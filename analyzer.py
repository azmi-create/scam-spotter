"""
analyzer.py - Scam detection logic using Google GenAI SDK.
"""

import json
import os
from typing import Any, Dict, List, Literal, Optional, Union
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel, Field, ValidationError

# Load environment variables from .env file
load_dotenv()

SYSTEM_PROMPT = """You are an elite cybersecurity and fraud-detection expert specializing in consumer protection.
Your task is to analyze the provided message or screenshot for indicators of scams, phishing, social engineering, financial fraud, impersonation, or dangerous links.

Evaluation Guidelines:
- "Scam": High probability of fraud, phishing, impersonation (e.g., fake bank alerts, crypto scams, package delivery scams with malicious links, prize hoaxes).
- "Risky": Suspicious or unsolicited elements, pressure tactics, vague offers, or requests for contact where caution is warranted but malicious intent is not 100% proven.
- "Safe": Legitimate, routine, or benign communications with no deceptive or fraudulent characteristics.

Required Output Rules:
1. verdict: Must be exactly one of "Scam", "Risky", or "Safe".
2. confidence: Integer between 0 and 100 representing certainty.
3. red_flags: List of up to 3 concise bullet points identifying specific suspicious indicators. If completely Safe, return an empty list or safety notes.
4. explanation: Exactly two simple, clear sentences explaining the reasoning for the verdict to a general user.
5. what_to_do: List of 2 to 3 short, actionable, concrete instructions for the user to stay safe."""


class ScamAnalysisSchema(BaseModel):
    verdict: Literal["Scam", "Risky", "Safe"]
    confidence: int = Field(..., ge=0, le=100, description="Confidence score from 0 to 100")
    red_flags: List[str] = Field(..., description="List of up to 3 short strings")
    explanation: str = Field(..., description="Exactly two simple sentences explaining the verdict")
    what_to_do: List[str] = Field(..., description="List of 2-3 short action steps")


def get_genai_client() -> Optional[genai.Client]:
    """Initialize and return the GenAI client using the configured API key."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def _execute_analysis(contents: Union[str, List[Any]]) -> Dict[str, Any]:
    """
    Internal helper to invoke Gemini with structured JSON mode and handle errors.
    Reused by both analyze_message and analyze_image.
    """
    # 1. Check API key configuration
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {
            "verdict": "Risky",
            "confidence": 0,
            "red_flags": ["Missing Gemini API Key"],
            "explanation": "The Gemini API key is missing from your environment. Please configure GEMINI_API_KEY in your .env file to enable analysis.",
            "what_to_do": [
                "Create a .env file in the project root based on .env.example.",
                "Set GEMINI_API_KEY=your_key_here with a valid Google Gemini API key.",
                "Restart the application and try again."
            ],
            "error": "Missing API key: GEMINI_API_KEY is not set."
        }

    # 2. Model selection
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # 3. Call Gemini
    try:
        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=ScamAnalysisSchema,
            temperature=0.1,
        )

        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )
    except APIError as api_err:
        return {
            "verdict": "Risky",
            "confidence": 0,
            "red_flags": ["API communication failure"],
            "explanation": f"Google Gemini API error occurred while processing the request: {api_err.message or str(api_err)}",
            "what_to_do": [
                "Verify your GEMINI_API_KEY permissions and quota in Google AI Studio.",
                "Check that the model specified in GEMINI_MODEL is accessible with your key.",
                "Try again in a few moments."
            ],
            "error": f"Gemini API Error: {api_err.message or str(api_err)}"
        }
    except Exception as e:
        return {
            "verdict": "Risky",
            "confidence": 0,
            "red_flags": ["Network or service error"],
            "explanation": f"Unable to reach the scam analysis service. Details: {str(e)}",
            "what_to_do": [
                "Check your internet connection.",
                "Ensure GEMINI_API_KEY and GEMINI_MODEL in .env are valid.",
                "Retry after a short moment."
            ],
            "error": f"Service Error: {str(e)}"
        }

    # 4. Parse and validate JSON response
    response_text = response.text if response and hasattr(response, "text") else ""
    if not response_text:
        return {
            "verdict": "Risky",
            "confidence": 0,
            "red_flags": ["Empty response from model"],
            "explanation": "The AI model returned an empty response. This can occasionally happen due to safety filtering or temporary timeouts.",
            "what_to_do": [
                "Check whether the submitted message contains blocked content.",
                "Try re-analyzing the message or testing with a shorter snippet."
            ],
            "error": "Empty response received from Gemini."
        }

    try:
        raw_json = json.loads(response_text)
    except json.JSONDecodeError as json_err:
        return {
            "verdict": "Risky",
            "confidence": 0,
            "red_flags": ["Malformed JSON from AI model"],
            "explanation": "The AI model response was not valid JSON. Please try analyzing again.",
            "what_to_do": [
                "Retry the analysis.",
                "If the issue persists, test with a different model in GEMINI_MODEL."
            ],
            "error": f"Invalid JSON response: {str(json_err)}"
        }

    # 5. Format and bound output fields
    try:
        validated = ScamAnalysisSchema.model_validate(raw_json)
        result_dict = validated.model_dump()
        result_dict["red_flags"] = result_dict["red_flags"][:3]
        result_dict["what_to_do"] = result_dict["what_to_do"][:3]
        return result_dict
    except ValidationError:
        verdict = raw_json.get("verdict", "Risky")
        if verdict not in ("Scam", "Risky", "Safe"):
            verdict = "Risky"

        try:
            confidence = int(raw_json.get("confidence", 50))
            confidence = max(0, min(100, confidence))
        except (ValueError, TypeError):
            confidence = 50

        red_flags = raw_json.get("red_flags", [])
        if not isinstance(red_flags, list):
            red_flags = [str(red_flags)]
        red_flags = [str(rf) for rf in red_flags[:3]]

        explanation = str(raw_json.get("explanation", "Analysis completed with partial formatting."))
        what_to_do = raw_json.get("what_to_do", [])
        if not isinstance(what_to_do, list):
            what_to_do = [str(what_to_do)]
        what_to_do = [str(step) for step in what_to_do[:3]]
        if not what_to_do:
            what_to_do = ["Verify sender through an independent official channel.", "Do not click unverified links."]

        return {
            "verdict": verdict,
            "confidence": confidence,
            "red_flags": red_flags,
            "explanation": explanation,
            "what_to_do": what_to_do
        }


def analyze_message(text: str) -> Dict[str, Any]:
    """
    Sends the suspicious message to Gemini with a scam-detection system prompt.
    Returns a dictionary matching the specified JSON schema:
      - verdict: "Scam" | "Risky" | "Safe"
      - confidence: int (0-100)
      - red_flags: list[str] (up to 3 items)
      - explanation: str (2 simple sentences)
      - what_to_do: list[str] (2-3 short action steps)

    Gracefully handles empty input, missing configuration, API errors, and invalid JSON.
    """
    if not text or not text.strip():
        return {
            "verdict": "Risky",
            "confidence": 0,
            "red_flags": ["No message text was provided"],
            "explanation": "No message was provided to analyze. Please enter or paste the message text into the box above.",
            "what_to_do": [
                "Paste the suspicious email, SMS, or direct message into the text area.",
                "Click the Analyze button to receive an assessment."
            ],
            "error": "Empty input: Please paste a message to analyze."
        }

    user_content = f"Please analyze this message for scam indicators:\n\n\"\"\"\n{text.strip()}\n\"\"\""
    return _execute_analysis(user_content)


def analyze_image(image_bytes: bytes, mime_type: str = "image/png") -> Dict[str, Any]:
    """
    Sends a screenshot image to Gemini with scam-detection prompt and JSON schema.
    Uses types.Part.from_bytes to attach the image.
    Prompt note: 'First read all text visible in the screenshot (including sender name,
    phone number, and links), then analyze it for scam indicators.'

    Returns a dictionary with the same verdict, confidence, red_flags, explanation, and what_to_do.
    Gracefully handles empty input, unsupported format, API errors, and invalid JSON.
    """
    if not image_bytes:
        return {
            "verdict": "Risky",
            "confidence": 0,
            "red_flags": ["No image data provided"],
            "explanation": "No screenshot was provided to analyze. Please upload a valid PNG or JPEG image file.",
            "what_to_do": [
                "Upload a clear screenshot of the suspicious message or website.",
                "Click Analyze to evaluate it."
            ],
            "error": "Empty image: Please provide a valid screenshot to analyze."
        }

    # Normalize mime type
    normalized_mime = mime_type.lower().strip()
    if normalized_mime in ("image/jpg", "jpg"):
        normalized_mime = "image/jpeg"
    elif normalized_mime == "png":
        normalized_mime = "image/png"

    try:
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=normalized_mime)
    except Exception as part_err:
        return {
            "verdict": "Risky",
            "confidence": 0,
            "red_flags": ["Invalid image format"],
            "explanation": f"Unable to process the image data: {str(part_err)}",
            "what_to_do": [
                "Ensure the file is a standard PNG or JPEG image.",
                "Try taking another screenshot and re-uploading."
            ],
            "error": f"Invalid image format: {str(part_err)}"
        }

    prompt_note = (
        "First read all text visible in the screenshot (including sender name, phone number, and links), "
        "then analyze it for scam indicators."
    )

    contents = [image_part, prompt_note]
    return _execute_analysis(contents)
