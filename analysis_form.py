import streamlit as st
from config.prompts import SPECIALIST_PROMPTS
from utils.pdf_extractor import extract_text_from_pdf
from config.sample_data import SAMPLE_REPORT
from config.app_config import MAX_UPLOAD_SIZE_MB
import json
import os
from groq import Groq


def show_analysis_form():
    # Initialize session state for patient info
    if "patient_name" not in st.session_state:
        st.session_state.patient_name = ""
    if "patient_age" not in st.session_state:
        st.session_state.patient_age = 0
    if "patient_gender" not in st.session_state:
        st.session_state.patient_gender = ""

    # Initialize report source in session state for new sessions
    if (
        "current_session" in st.session_state
        and "report_source" not in st.session_state
    ):
        st.session_state.report_source = "Upload PDF"

    report_source = st.radio(
        "Choose report source",
        ["Upload PDF", "Use Sample PDF"],
        index=0 if st.session_state.get("report_source") == "Upload PDF" else 1,
        horizontal=True,
        key="report_source",
    )

    pdf_contents = get_report_contents(report_source)

    if pdf_contents:  # Only show form if we have report content
        render_patient_form(pdf_contents)


def get_report_contents(report_source):
    if report_source == "Upload PDF":
        uploaded_file = st.file_uploader(
            f"Upload blood report PDF (Max {MAX_UPLOAD_SIZE_MB}MB)",
            type=["pdf"],
            help=f"Maximum file size: {MAX_UPLOAD_SIZE_MB}MB. Only PDF files containing medical reports are supported",
        )
        if uploaded_file:
            # Check file size before processing
            file_size_mb = uploaded_file.size / (1024 * 1024)  # Convert to MB
            if file_size_mb > MAX_UPLOAD_SIZE_MB:
                st.error(
                    f"File size ({file_size_mb:.1f}MB) exceeds the {MAX_UPLOAD_SIZE_MB}MB limit."
                )
                return None

            if uploaded_file.type != "application/pdf":
                st.error("Please upload a valid PDF file.")
                return None

            pdf_contents = extract_text_from_pdf(uploaded_file)
            if isinstance(pdf_contents, str) and (
                pdf_contents.startswith(
                    ("File size exceeds", "Invalid file type", "Error validating")
                )
                or pdf_contents.startswith("The uploaded file")
                or "error" in pdf_contents.lower()
            ):
                st.error(pdf_contents)
                return None
            
            # Auto-Extraction from PDF text
            file_hash = f"{uploaded_file.name}_{uploaded_file.size}"
            if st.session_state.get("last_processed_pdf") != file_hash:
                with st.spinner("🔍 Auto-detecting patient information..."):
                    try:
                        # Safe Groq API Key access with fallback
                        import os
                        try:
                            groq_api_key = st.secrets["GROQ_API_KEY"]
                        except Exception:
                            groq_api_key = os.getenv("GROQ_API_KEY", "")

                        if groq_api_key:
                            client = Groq(api_key=groq_api_key)
                            extract_prompt = f"Extract the following fields from this medical document. Return ONLY a valid JSON object with keys: \"name\", \"age\", \"gender\". If a field is not found, return null for that field.\n\nDocument Text:\n{pdf_contents[:4000]}"
                            
                            response = client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=[{"role": "user", "content": extract_prompt}],
                                response_format={"type": "json_object"},
                                temperature=0,
                            )
                            
                            extracted_info = json.loads(response.choices[0].message.content)
                            
                            # Pre-fill session state
                            if extracted_info.get("name"): 
                                st.session_state.patient_name = extracted_info["name"]
                            if extracted_info.get("age"):
                                try:
                                    st.session_state.patient_age = int(extracted_info["age"])
                                except:
                                    pass
                            if extracted_info.get("gender"):
                                g = str(extracted_info["gender"]).capitalize()
                                if g in ["Male", "Female", "Other"]:
                                    st.session_state.patient_gender = g
                        
                            st.session_state.last_processed_pdf = file_hash
                            st.toast("✅ Patient info auto-detected from PDF", icon="✨")
                    except Exception as e:
                        # Silent failure for extraction convenience
                        pass

            with st.expander("View Extracted Report"):
                st.text(pdf_contents)
            return pdf_contents
    else:
        with st.expander("View Sample Report"):
            st.text(SAMPLE_REPORT)
        return SAMPLE_REPORT
    return None


def render_patient_form(pdf_contents):
    with st.form("analysis_form"):
        # Auto-populated fields
        patient_name = st.text_input("Patient Name", value=st.session_state.get("patient_name", ""))
        
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Age", min_value=0, max_value=120, value=int(st.session_state.get("patient_age", 0)))
        with col2:
            gender_options = ["", "Male", "Female", "Other"]
            current_gender = st.session_state.get("patient_gender", "")
            # Ensure the gender actually exists in our options
            if current_gender not in gender_options:
                current_gender = ""
            gender = st.selectbox("Gender", gender_options, 
                                index=gender_options.index(current_gender))

        if st.form_submit_button("Analyze Report"):
            # Update session state with final values before analysis
            st.session_state.patient_name = patient_name
            st.session_state.patient_age = age
            st.session_state.patient_gender = gender
            handle_form_submission(patient_name, age, gender, pdf_contents)


def handle_form_submission(patient_name, age, gender, pdf_contents):
    # Validation: age can be 0, but name and gender must be non-empty
    if not patient_name or not gender or age is None:
        st.error("Please fill in all fields (Name, Age, and Gender)")
        return

    # Check rate limit first, outside of spinner
    from services.ai_service import generate_analysis

    can_analyze, error_msg = generate_analysis(None, None, check_only=True)
    if not can_analyze:
        st.error(error_msg)
        st.stop()
        return

    with st.spinner("Analyzing report..."):
        # Save report content for follow-up chat (session state for immediate use)
        st.session_state.current_report_text = pdf_contents

        # Save user message and proceed with analysis
        st.session_state.auth_service.save_chat_message(
            st.session_state.current_session["id"],
            f"Analyzing report for patient: {patient_name}",
        )

        # Generate analysis
        result = generate_analysis(
            {
                "patient_name": patient_name,
                "age": age,
                "gender": gender,
                "report": pdf_contents,
            },
            SPECIALIST_PROMPTS["comprehensive_analyst"],
        )

        if result["success"]:
            # Store report text as a system message for persistence
            # This allows us to retrieve it later even after page refresh
            report_metadata = f"__REPORT_TEXT__\n{pdf_contents}\n__END_REPORT_TEXT__"
            st.session_state.auth_service.save_chat_message(
                st.session_state.current_session["id"], report_metadata, role="system"
            )

            # Add model used information if available
            content = result["content"]
            if "model_used" in result:
                model_info = f"\n\n*Analysis generated using {result['model_used']}*"
                content += model_info

            st.session_state.auth_service.save_chat_message(
                st.session_state.current_session["id"], content, role="assistant"
            )
            st.rerun()
        else:
            st.error(result["error"])
            st.stop()
