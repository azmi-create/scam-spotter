import streamlit as st
from analyzer import analyze_message, analyze_image

# Page configuration
st.set_page_config(
    page_title="Scam Spotter",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Custom CSS for polished, modern look
st.markdown(
    """
    <style>
    /* Main container styling */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 780px;
    }
    
    /* Header typography */
    .app-title {
        font-size: 2.4rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.25rem;
        letter-spacing: -0.5px;
    }
    
    .app-tagline {
        font-size: 1.05rem;
        color: #64748b;
        text-align: center;
        margin-bottom: 2rem;
    }

    /* Verdict Banner Styles */
    .verdict-banner {
        border-radius: 12px;
        padding: 24px 20px;
        text-align: center;
        color: #ffffff;
        margin-top: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
    }
    
    .verdict-scam {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        border: 1px solid #b91c1c;
    }
    
    .verdict-risky {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        border: 1px solid #b45309;
    }
    
    .verdict-safe {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        border: 1px solid #047857;
    }
    
    .verdict-label {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: 700;
        opacity: 0.9;
        margin-bottom: 4px;
    }

    .verdict-heading {
        font-size: 2.2rem;
        font-weight: 900;
        margin: 0;
        line-height: 1.1;
    }
    
    /* Card sections */
    .section-card {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 1rem;
    }
    
    .card-title {
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    /* Footer */
    .app-footer {
        text-align: center;
        font-size: 0.85rem;
        color: #94a3b8;
        margin-top: 3rem;
        padding-top: 1.5rem;
        border-top: 1px solid rgba(128, 128, 128, 0.2);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Title and Tagline
st.markdown("<h1 class='app-title'>🛡️ Scam Spotter</h1>", unsafe_allow_html=True)
st.markdown(
    "<p class='app-tagline'>Detect fraudulent messages, phishing scams, and shady links in seconds.</p>",
    unsafe_allow_html=True,
)

# Preset examples for convenience
example_scam = "URGENT: Your Wells Fargo account has been locked due to suspicious activity. Verify your identity immediately at http://secure-wellsfargo-verify.biz/login or your account will be permanently closed."
example_safe = "Hi Mom! The flight just landed safely. Grabbing my luggage now and will call you once I'm in the Uber."
example_risky = "Hey! A mutual friend told me about your photography work. Check out this cool collaborative gig opportunity and text me back: http://tinyurl.com/photog-apply"

if "message_input" not in st.session_state:
    st.session_state["message_input"] = ""

def set_preset(text: str) -> None:
    st.session_state["message_input"] = text

with st.expander("💡 Or try an example message", expanded=False):
    col1, col2, col3 = st.columns(3)
    col1.button("🚨 Phishing Alert", use_container_width=True, on_click=set_preset, args=(example_scam,))
    col2.button("⚠️ Unsolicited Offer", use_container_width=True, on_click=set_preset, args=(example_risky,))
    col3.button("✅ Normal Text", use_container_width=True, on_click=set_preset, args=(example_safe,))

# Text Input Area
user_message = st.text_area(
    label="Paste suspicious message:",
    key="message_input",
    height=180,
    placeholder="Paste suspicious SMS, email, WhatsApp message, or direct message here...",
    help="Copy and paste any suspicious communication you received to analyze its legitimacy.",
)

# Screenshot Upload Option
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = ("png", "jpg", "jpeg")

uploaded_file = st.file_uploader(
    "Or upload a screenshot",
    type=["png", "jpg", "jpeg"],
    help="Upload an image or screenshot of a suspicious message (PNG, JPG, or JPEG up to 5 MB).",
)

file_is_valid = True
if uploaded_file is not None:
    file_ext = uploaded_file.name.split(".")[-1].lower() if "." in uploaded_file.name else ""
    if file_ext not in ALLOWED_EXTENSIONS:
        st.error(f"⚠️ Unsupported file type (.{file_ext}). Please upload a PNG, JPG, or JPEG screenshot.")
        file_is_valid = False
    elif uploaded_file.size > MAX_FILE_SIZE_BYTES:
        size_mb = uploaded_file.size / (1024 * 1024)
        st.error(f"⚠️ File size ({size_mb:.2f} MB) exceeds the {MAX_FILE_SIZE_MB} MB limit. Please upload a smaller image.")
        file_is_valid = False
    else:
        st.image(uploaded_file, caption="Screenshot preview", width=240)

# Analyze Button
analyze_clicked = st.button("🔍 Analyze", type="primary", use_container_width=True)

# Analysis execution
if analyze_clicked:
    result = None
    if uploaded_file is not None:
        if not file_is_valid:
            st.error("⚠️ Please resolve the file error above before analyzing.")
        else:
            with st.spinner("Analyzing screenshot with AI scam detector..."):
                mime_type = uploaded_file.type
                if not mime_type:
                    ext = uploaded_file.name.split(".")[-1].lower()
                    mime_type = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
                result = analyze_image(uploaded_file.getvalue(), mime_type=mime_type)
    elif user_message.strip():
        with st.spinner("Analyzing message with AI scam detector..."):
            result = analyze_message(user_message)
    else:
        st.warning("⚠️ Please paste a message or upload a screenshot to analyze.")

    # Show result UI
    if result is not None:
        if result.get("error") and not result.get("verdict"):
            st.error(f"Error: {result['error']}")
        else:
            verdict = result.get("verdict", "Risky")
            confidence = int(result.get("confidence", 0))
            red_flags = result.get("red_flags", [])
            explanation = result.get("explanation", "")
            what_to_do = result.get("what_to_do", [])

            # Banner style mapping
            banner_classes = {
                "Scam": "verdict-scam",
                "Risky": "verdict-risky",
                "Safe": "verdict-safe",
            }
            banner_icons = {
                "Scam": "🚨",
                "Risky": "⚠️",
                "Safe": "✅",
            }
            banner_class = banner_classes.get(verdict, "verdict-risky")
            banner_icon = banner_icons.get(verdict, "⚠️")

            # Big colored banner
            st.markdown(
                f"""
                <div class="verdict-banner {banner_class}">
                    <div class="verdict-label">Analysis Result</div>
                    <div class="verdict-heading">{banner_icon} VERDICT: {verdict.upper()}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Confidence Metric & Progress
            col_metric, col_bar = st.columns([1, 2])
            with col_metric:
                st.metric(
                    label="Confidence Score",
                    value=f"{confidence}%",
                    help="Model certainty in this assessment.",
                )
            with col_bar:
                st.write("**Confidence Level**")
                st.progress(confidence / 100.0)

            st.write("")

            # Red Flags Section
            st.subheader("🚩 Red Flags")
            if red_flags:
                for flag in red_flags:
                    st.markdown(f"- **{flag}**")
            else:
                st.info("No suspicious red flags were detected in this message.")

            # Explanation Section
            st.subheader("📝 Explanation")
            st.info(explanation)

            # What-to-do Section
            st.subheader("🛡️ What You Should Do")
            for idx, step in enumerate(what_to_do, 1):
                st.markdown(f"**{idx}.** {step}")

# Footer
st.markdown(
    "<div class='app-footer'>Informational only. Always verify with your bank or official source.</div>",
    unsafe_allow_html=True,
)
