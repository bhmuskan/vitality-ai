import streamlit as st
from auth.session_manager import SessionManager
from config.app_config import APP_ICON, APP_NAME, APP_TAGLINE, APP_DESCRIPTION
from utils.validators import validate_signup_fields
import time
import re

def show_login_page():
    # IMPORTANT: Initialize form_type immediately, no code before this!
    if 'form_type' not in st.session_state:
        st.session_state['form_type'] = 'login'  # Use dict-style access to be safer
    
    # From now on, form_type is guaranteed to exist
    current_form = st.session_state['form_type']  # Use dict-style access for consistency

    # Minimal specific CSS for auth page
    st.markdown("""
        <style>
        /* Hide navbar on auth screen */
        header { visibility: hidden !important; }
        
        /* Premium Auth Card Styling */
        [data-testid="stForm"] {
            max-width: 420px !important;
            margin: 0 auto !important;
            padding: 2rem !important;
            border-radius: 16px !important;
            border: 1px solid rgba(0, 180, 216, 0.15) !important;
            background: linear-gradient(180deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%) !important;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3) !important;
        }

        /* Center all buttons under Auth pages */
        .stButton {
            display: flex;
            justify-content: center;
        }
        .stButton > button {
            width: 100% !important;
            max-width: 420px !important;
        }
        
        /* Make Hr lines more subtle */
        hr { margin: 1.5rem auto !important; max-width: 420px !important; border-top: 1px solid rgba(255,255,255,0.1) !important;}
        
        /* Remove default Streamlit padding */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 1rem !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
<div style="text-align:center; margin-bottom: 1rem;">
  <div style="font-size: 2.5rem; margin-bottom: 0px; text-shadow: 0 0 20px rgba(0,180,216,0.3);">🧬</div>
  <div style="font-size: 2rem; font-weight: 700; color: white; letter-spacing: -0.02em;">VITALITY AI</div>
  <div style="font-size: 0.8rem; color: #00B4D8; font-weight: 600; margin-top: 4px; text-transform: uppercase; letter-spacing: 1.5px;">Your Intelligent Health Companion</div>
  <p style="color: rgba(255,255,255,0.5); font-size: 0.85rem; max-width: 420px; margin: 0.5rem auto 0 auto; line-height: 1.3;">
    Authenticate to access intelligent patient insights, secure chat sessions, and advanced health data analytics.
  </p>
</div>
""", unsafe_allow_html=True)

    # Use the stored current_form value
    if current_form == 'login':
        show_login_form()
    else:
        show_signup_form()
    
    # Toggle button at bottom
    st.markdown("---")
    toggle_text = "Don't have an account? Sign up" if current_form == 'login' else "Already have an account? Login"
    if st.button(toggle_text, use_container_width=True, type="secondary"):
        # Toggle form type (use dict access for safety)
        st.session_state['form_type'] = 'signup' if current_form == 'login' else 'login'
        st.rerun()

def show_login_form():
    with st.form("login_form"):
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.form_submit_button("Login", use_container_width=True, type="primary"):
            if email and password:
                success, result = SessionManager.login(email, password)
                if success:
                    # Show success message with spinner
                    with st.spinner("Logging in..."):
                        success_placeholder = st.empty()
                        success_placeholder.success("Login successful! Redirecting...")
                        time.sleep(1)  # Brief pause to show message
                        st.rerun()
                else:
                    st.error(f"Login failed: {result}")
            else:
                st.error("Please enter both email and password")

def show_signup_form():
    with st.form("signup_form"):
        new_name = st.text_input("Full Name", key="signup_name")
        new_email = st.text_input("Email", key="signup_email")
        new_password = st.text_input("Password", type="password", key="signup_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="signup_password2")
        
        st.markdown("""
            Password requirements:
            - At least 8 characters
            - One uppercase letter
            - One lowercase letter
            - One number
        """)
        
        if st.form_submit_button("Sign Up", use_container_width=True, type="primary"):
            validation_result = validate_signup_fields(
                new_name, new_email, new_password, confirm_password
            )
            
            if not validation_result[0]:
                st.error(validation_result[1])
                return
            
            # Show loading spinner during signup
            with st.spinner("Creating your account..."):
                success, response = st.session_state.auth_service.sign_up(
                    new_email, new_password, new_name
                )
                
                if success:
                    st.session_state.authenticated = True
                    st.session_state.user = response
                    st.success("Account created successfully! Redirecting...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Sign up failed: {response}")
