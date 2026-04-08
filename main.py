import streamlit as st
import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['USE_TORCH'] = 'True'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
from auth.session_manager import SessionManager
from components.auth_pages import show_login_page
from components.sidebar import show_sidebar
from components.analysis_form import show_analysis_form
from components.footer import show_footer
from config.app_config import APP_NAME, APP_TAGLINE, APP_DESCRIPTION, APP_ICON
from services.ai_service import get_chat_response

# Must be the first Streamlit command
st.set_page_config(
    page_title="Vitality AI", page_icon="🧬", layout="wide"
)

# Initialize session state
SessionManager.init_session()

# Hide all Streamlit form-related elements
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif !important;
        }

        /* Background gradient for main app */
        .stApp {
            background: linear-gradient(135deg, #0D1B2A 0%, #1B2A3B 100%) !important;
            color: #FFFFFF !important;
        }

        /* Main fade-in animation */
        .main {
            animation: fadeIn 0.8s ease-out forwards;
        }
        @keyframes fadeIn {
            0% { opacity: 0; transform: translateY(15px); }
            100% { opacity: 1; transform: translateY(0); }
        }

        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #081119 !important;
            border-right: 1px solid rgba(0,180,216,0.1) !important;
        }

        /* Top logo area in sidebar */
        [data-testid="stSidebarNav"]::before {
            content: "🧬 VITALITY AI";
            display: block;
            padding: 2rem 1.5rem;
            font-size: 1.5rem;
            font-weight: 700;
            color: #00B4D8;
            text-shadow: 0 0 10px rgba(0, 180, 216, 0.3);
            letter-spacing: 1px;
        }

        /* Primary Action Buttons */
        button[kind="primary"], [data-testid="stFormSubmitButton"] > button {
            background: linear-gradient(135deg, #00B4D8, #023E8A) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 50px !important; /* Pill-shaped */
            padding: 0.6rem 1.5rem !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
        }
        button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 15px rgba(0,180,216,0.4) !important;
        }

        /* Secondary Item Buttons (Sidebar lists, Toggles) */
        button[kind="secondary"] {
            background: rgba(255,255,255,0.03) !important;
            color: rgba(255,255,255,0.85) !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            border-radius: 10px !important; /* Modern square with rounded corners */
            padding: 0.5rem 1rem !important;
            transition: all 0.2s ease !important;
            font-weight: 500 !important;
            display: flex;
            align-items: center;
        }
        button[kind="secondary"]:hover {
            background: rgba(0,180,216,0.1) !important;
            border-color: rgba(0,180,216,0.4) !important;
            color: #FFFFFF !important;
        }
        
        /* Force left align only for session list buttons (1st column) */
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:first-child button[kind="secondary"] {
            justify-content: flex-start !important;
        }
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:first-child button[kind="secondary"] p {
            text-align: left !important;
            width: 100%;
        }

        /* Ensure icon/dustbin buttons (Last column) absolutely center their inner DOM layers */
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:last-child button[kind="secondary"] {
            justify-content: center !important;
            padding: 0 !important;
        }
        
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:last-child button[kind="secondary"] > * {
            display: flex !important;
            justify-content: center !important;
            width: 100% !important;
        }

        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:last-child button[kind="secondary"] p {
            text-align: center !important;
            margin: 0 auto !important;
            display: flex !important;
            justify-content: center !important;
            width: 100% !important;
        }

        /* Cards (Metric blocks and general containers) */
        div[data-testid="stMetric"], .stExpander, div.css-1r6slb0, div.stChatFloatingInputContainer {
            background: rgba(255, 255, 255, 0.03) !important;
            border-radius: 12px !important;
            border: 1px solid rgba(0,180,216,0.1) !important;
            padding: 1.5rem !important;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1) !important;
            transition: transform 0.3s ease, box-shadow 0.3s ease !important;
            margin-bottom: 1rem !important;
        }

        div[data-testid="stMetric"]:hover, .stExpander:hover {
            transform: translateY(-3px) !important;
            box-shadow: 0 8px 25px rgba(0,180,216,0.15) !important;
        }

        /* Metric specific styling */
        [data-testid="stMetricValue"] {
            font-size: 2.2rem !important;
            font-weight: 700 !important;
            color: #FFFFFF !important;
        }
        [data-testid="stMetricDelta"] {
            color: #06D6A0 !important; /* Health green */
        }

        /* Tables/DataFrames */
        .stDataFrame {
            border-radius: 12px !important;
            overflow: hidden !important;
            border: 1px solid rgba(255,255,255,0.05) !important;
        }
        table {
            border-collapse: collapse !important;
            width: 100% !important;
            color: #FFFFFF !important;
        }
        th {
            background-color: rgba(0,180,216,0.15) !important;
            color: #00B4D8 !important;
            font-weight: 600 !important;
            padding: 14px 12px !important;
            text-align: left !important;
            border-bottom: 2px solid #00B4D8 !important;
        }
        tr:nth-child(even) {
            background-color: rgba(255,255,255,0.01) !important;
        }
        tr:nth-child(odd) {
            background-color: rgba(255,255,255,0.03) !important;
        }
        td {
            padding: 12px !important;
            border-bottom: 1px solid rgba(255,255,255,0.05) !important;
        }

        /* Input Fields */
        .stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div > div {
            background-color: rgba(255,255,255,0.03) !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            border-radius: 10px !important;
            color: #FFFFFF !important;
            padding: 0.5rem 1rem !important;
            transition: all 0.2s ease !important;
        }
        .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus, .stSelectbox > div > div > div:focus {
            border-color: #00B4D8 !important;
            box-shadow: 0 0 0 2px rgba(0,180,216,0.2) !important;
            background-color: rgba(255,255,255,0.06) !important;
        }

        /* Hide form submission helper text */
        div[data-testid="InputInstructions"] > span:nth-child(1) {
            visibility: hidden;
        }

        /* Alerts and Warnings (Pulse Animation) */
        .stAlert {
            border-radius: 10px !important;
            border-left: 4px solid !important;
            background-color: rgba(255,255,255,0.02) !important;
        }
        .stException, div[data-baseweb="toast"][style*="error"], div[data-testid="stAlert"]:has(> div[data-testid="stMarkdownContainer"] > p:contains("Error")) {
            animation: pulse 2s infinite !important;
            border-left-color: #FF4D4D !important;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(255, 77, 77, 0.4); }
            70% { box-shadow: 0 0 0 10px rgba(255, 77, 77, 0); }
            100% { box-shadow: 0 0 0 0 rgba(255, 77, 77, 0); }
        }

        /* Chat bubbles styling */
        .stChatMessage {
            background-color: rgba(255,255,255,0.02) !important;
            border-radius: 12px !important;
            padding: 1.5rem !important;
            border: 1px solid rgba(255,255,255,0.05) !important;
            margin-bottom: 1rem !important;
        }
        .stChatMessage[data-testid="stChatMessageUser"] {
            background-color: rgba(0,180,216,0.05) !important;
            border: 1px solid rgba(0,180,216,0.1) !important;
        }
        
        /* Section Dividers */
        hr {
            border-top: 1px solid rgba(0,180,216,0.2) !important;
            margin: 2.5rem 0 !important;
        }

        /* Watermark/Footer */
        .footer-watermark {
            position: fixed;
            bottom: 0;
            right: 0;
            padding: 12px 24px;
            font-size: 0.8rem;
            font-weight: 500;
            letter-spacing: 1px;
            color: rgba(255,255,255,0.3);
            pointer-events: none;
            z-index: 1000;
        }
    </style>
    <div class="footer-watermark">VITALITY AI • INTELLIGENT HEALTH COMPANION</div>
""",
    unsafe_allow_html=True,
)


def show_welcome_screen():
    st.markdown(
        f"""
        <div style='text-align: center; display: flex; flex-direction: column; align-items: center; justify-content: center; padding-top: 5rem; padding-bottom: 2rem;'>
            <h1 style='font-size: 4rem; font-weight: 800; color: white; margin-bottom: 0.5rem; letter-spacing: -0.03em; display: flex; align-items: center; justify-content: center; gap: 16px;'>
                <span style='text-shadow: 0 0 30px rgba(0,180,216,0.5); font-size: 4rem;'>🧬</span> Vitality AI
            </h1>
            <h2 style='font-size: 1.6rem; color: rgba(255,255,255,0.9); font-weight: 500; margin-bottom: 2.5rem; letter-spacing: -0.01em;'>Your intelligent health companion</h2>
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); padding: 1rem 2.5rem; border-radius: 50px; display: inline-block; margin-bottom: 2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                <p style='font-size: 1.05rem; color: rgba(255,255,255,0.6); margin: 0; font-weight: 500; letter-spacing: 0.5px;'>
                    Discover a Healthier You with AI <span style="color: #00B4D8; margin: 0 10px;">•</span> Start by creating a session
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        if st.button(
            "➕ Create New Analysis Session", use_container_width=True, type="primary"
        ):
            success, session = SessionManager.create_chat_session()
            if success:
                st.session_state.current_session = session
                st.rerun()
            else:
                st.error("Failed to create session")


def show_chat_history():
    success, messages = st.session_state.auth_service.get_session_messages(
        st.session_state.current_session["id"]
    )

    if success and messages:
        # Separate the initial analysis (first assistant message) from follow-ups
        initial_analysis = None
        follow_up_messages = []
        
        # We need to filter out system messages and find the first assistant response
        for msg in messages:
            if msg.get("role") == "system":
                continue
            
            # The first assistant message is our primary analysis report
            if msg["role"] == "assistant" and not initial_analysis:
                initial_analysis = msg["content"]
            else:
                follow_up_messages.append(msg)
        
        # 1. Display the Clinical Analysis in a prominent, premium card
        if initial_analysis:
            st.markdown("""
                <div style='background: rgba(0, 180, 216, 0.05); border-left: 4px solid #00B4D8; padding: 2rem; border-radius: 12px; margin-bottom: 2rem;'>
                    <h3 style='margin-top: 0; color: #00B4D8; font-size: 1.2rem; text-transform: uppercase; letter-spacing: 1px;'>📋 Comprehensive Clinical Analysis</h3>
                    <div style='color: #E0E0E0; font-size: 1.05rem; line-height: 1.6;'>
            """, unsafe_allow_html=True)
            st.markdown(initial_analysis)
            st.markdown("</div></div>", unsafe_allow_html=True)

        # 2. Display follow-up chat history
        if follow_up_messages:
            st.markdown("<h4 style='color: #FFFFFF; opacity: 0.6; margin-bottom: 1.5rem;'>💬 Follow-up Consultation</h4>", unsafe_allow_html=True)
            for msg in follow_up_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    
        return messages
    return []


def handle_chat_input(messages):
    if prompt := st.chat_input("Ask a follow-up question regarding your analysis..."):
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)

        # Save user message
        st.session_state.auth_service.save_chat_message(
            st.session_state.current_session["id"], prompt, role="user"
        )

        # Get context (report text)
        context_text = st.session_state.get("current_report_text", "")
        if not context_text and messages:
            for msg in messages:
                if msg.get("role") == "system" and "__REPORT_TEXT__" in msg.get("content", ""):
                    content = msg.get("content", "")
                    start_idx = content.find("__REPORT_TEXT__\n") + len("__REPORT_TEXT__\n")
                    end_idx = content.find("\n__END_REPORT_TEXT__")
                    if start_idx > 0 and end_idx > start_idx:
                        context_text = content[start_idx:end_idx]
                        st.session_state.current_report_text = context_text
                        break

        with st.chat_message("assistant"):
            with st.spinner("Analyzing context..."):
                response = get_chat_response(prompt, context_text, messages)
                st.markdown(response)

            # Save AI response
            st.session_state.auth_service.save_chat_message(
                st.session_state.current_session["id"], response, role="assistant"
            )
            # Rerun to update the session state correctly
            st.rerun()


def show_user_greeting():
    if st.session_state.user:
        # Get name from user data, fallback to email if name is empty
        display_name = st.session_state.user.get("name") or st.session_state.user.get(
            "email", ""
        )
        st.markdown(
            f"""
            <div style='display: flex; justify-content: space-between; align-items: center; padding: 1.25rem 2rem; background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(0, 180, 216, 0.15); border-radius: 16px; margin-bottom: 2.5rem; box-shadow: 0 8px 32px rgba(0,0,0,0.15); backdrop-filter: blur(12px);'>
                <div style='display: flex; align-items: center; gap: 1.2rem;'>
                    <div style='font-size: 2.2rem; text-shadow: 0 0 20px rgba(0,180,216,0.4);'>🧬</div>
                    <div>
                        <h2 style='margin: 0; color: #FFFFFF; font-weight: 700; letter-spacing: -0.02em; font-size: 1.4rem;'>VITALITY AI</h2>
                        <div style='color: #00B4D8; font-size: 0.8rem; font-weight: 600; margin-top: 4px; text-transform: uppercase; letter-spacing: 1.5px;'>
                            Intelligent Health Companion
                        </div>
                    </div>
                </div>
                <div style='text-align: right; color: rgba(255,255,255,0.9); font-size: 0.9em; font-weight: 500; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.05); padding: 0.5rem 1.2rem; border-radius: 50px; display: flex; align-items: center; gap: 8px;'>
                    <span style='font-size: 1.2em;'>👋</span> <span>Hi, <span style="font-weight: 600; color: white;">{display_name}</span></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main():
    SessionManager.init_session()

    if not SessionManager.is_authenticated():
        show_login_page()
        show_footer()
        return

    # Show user greeting at the top
    show_user_greeting()

    # Show sidebar
    show_sidebar()

    # Main session content
    if st.session_state.get("current_session"):
        session_title = st.session_state.current_session['title']
        st.markdown(f"<h1 style='font-size: 2.2rem; color: white; margin-bottom: 2rem;'>📊 {session_title}</h1>", unsafe_allow_html=True)
        
        # Load messages
        messages = show_chat_history()

        # If analysis is present, we show follow-up tools
        if messages:
            # We put the form in an expander if we already have results
            with st.expander("🔄 Update Patient Data or Re-Analyze Report", expanded=False):
                show_analysis_form()
            
            # Follow-up chat input
            handle_chat_input(messages)
        else:
            # No analysis yet, show the capture form
            show_analysis_form()
    else:
        show_welcome_screen()


if __name__ == "__main__":
    main()
