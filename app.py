import streamlit as st
import pandas as pd
from PIL import Image
import time
from datetime import datetime
import base64  # Added for handling file previews

# Internal modules
from resume_text_utils import extract_text
from prompts import resume_match_prompt
from llm import analyze_resume
from storage import save_to_google_sheet
import json

# Page Config
st.set_page_config(
    page_title="Crave – AI Resume Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SESSION STATE INITIALIZATION ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = None

# --- AUTHENTICATION FUNCTIONS ---
def check_password():
    """Validates username and password against secrets.toml"""
    def password_entered():
        # FIX: Use .get() to avoid KeyError if Streamlit has already cleaned up the widget
        user = st.session_state.get("username_input", "")
        pwd = st.session_state.get("password_input", "")
        
        # Check if user exists and password matches
        if user in st.secrets["auth"] and st.secrets["auth"][user] == pwd:
            st.session_state["authenticated"] = True
            st.session_state["username"] = user
            # CRITICAL FIX: Do NOT manually delete session keys here. 
            # Let Streamlit handle widget cleanup naturally.
        else:
            st.session_state["authenticated"] = False
            st.error("😕 User not known or password incorrect")

    if not st.session_state["authenticated"]:
        st.markdown(
            """
            <style>
                .login-container {
                    display: flex; 
                    flex-direction: column; 
                    align-items: center; 
                    justify-content: center;
                    padding-top: 50px;
                }
            </style>
            """, unsafe_allow_html=True
        )
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            try:
                logo = Image.open("assets/crave_logo.png")
                st.image(logo, width=200)
            except FileNotFoundError:
                st.header("Crave Infotech")
                
            st.markdown("<h2 style='text-align: center;'>AI Resume Workspace</h2>", unsafe_allow_html=True)
            
            st.text_input("Username", key="username_input")
            st.text_input("Password", type="password", key="password_input", on_change=password_entered)
            st.button("Login", on_click=password_entered, type="primary", use_container_width=True)
            
            st.markdown("---")
            st.caption("🔒 Secure Access | Crave Infotech Internal Tool")
            return False
            
    return True

# --- MAIN APP LOGIC ---
def main():
    # Sidebar
    with st.sidebar:

            
        st.write(f"👤 **User:** {st.session_state['username']}")
        
        if st.button("Logout"):
            st.session_state["authenticated"] = False
            st.session_state["username"] = None
            # Only clear inputs on explicit LOGOUT
            if "username_input" in st.session_state:
                del st.session_state["username_input"]
            if "password_input" in st.session_state:
                del st.session_state["password_input"]
            st.rerun()
            
        st.divider()
        st.info("💡 **Tip:** Upload multiple resumes to compare them side-by-side.")

    # Header
    logo_col, title_col = st.columns([1, 4])
    
    with logo_col:
        try:
            logo = Image.open("assets/crave_logo.png")
            st.image(logo, width=200)
        except FileNotFoundError:
            st.header("Crave Infotech")
    with title_col:
        st.title("AI Resume Analyzer")
    st.divider()

    # Inputs
    col_upload, col_jd = st.columns([1, 1.5], gap="large")
    
    with col_upload:
        st.subheader("Upload Resumes")
        resume_files = st.file_uploader(
            "Drop PDF or DOCX files here",
            type=["pdf", "docx"],
            accept_multiple_files=True
        )

    with col_jd:
        st.subheader("Job Description")
        jd_text = st.text_area(
            "Paste the complete JD here...", 
            height=400, 
            placeholder="e.g. Senior Python Developer with AWS experience..."
        )

    # Action
    if st.button("🔍 Run Analysis", type="primary"):
        if not resume_files or not jd_text.strip():
            st.warning("⚠️ Please upload at least one resume and provide a Job Description.")
        else:
            perform_analysis(resume_files, jd_text)

def perform_analysis(resume_files, jd_text):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_files = len(resume_files)
    
    for idx, resume_file in enumerate(resume_files):
        status_text.text(f"Processing {resume_file.name}...")
        
        # 1. Extract Text
        resume_text = extract_text(resume_file)
        if not resume_text.strip():
            st.error(f"Could not extract text from {resume_file.name}")
            continue

        # 2. Prepare File for Preview (Read bytes & Encode)
        # We must seek(0) because extract_text read the file stream to the end
        resume_file.seek(0)
        file_bytes = resume_file.read()
        file_b64 = base64.b64encode(file_bytes).decode()
        
        # 3. LLM Analysis
        prompt = resume_match_prompt(resume_text, jd_text)
        try:
            raw_result = analyze_resume(prompt)
            # Cleanup json string if markdown code blocks exist
            if "```json" in raw_result:
                raw_result = raw_result.split("```json")[1].split("```")[0]
            elif "```" in raw_result:
                raw_result = raw_result.split("```")[1].split("```")[0]
                
            data = json.loads(raw_result)
        except Exception as e:
            st.error(f"Error parsing AI response for {resume_file.name}: {e}")
            continue

        # 4. Enhance Data
        data["resume_file"] = resume_file.name
        data["resume_text_preview"] = resume_text[:1000] + "..." # Fallback text
        data["file_data"] = file_b64 # Binary data for preview
        data["file_type"] = resume_file.type # Mime type
        data["analyzed_by"] = st.session_state["username"]
        data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 5. Save to Google Sheets
        try:
            save_to_google_sheet(data)
        except Exception as e:
            st.toast(f"⚠️ Failed to save {data['applicant_name']} to Sheets: {str(e)}", icon="☁️")

        results.append(data)
        progress_bar.progress((idx + 1) / total_files)

    status_text.empty()
    progress_bar.empty()

    if results:
        display_results(results)

def display_results(results):
    df = pd.DataFrame(results)
    
    # Sort by match percentage
    df = df.sort_values(by="match_percentage", ascending=False)
    
    st.success("✅ Analysis Complete!")

    # Summary Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Candidates Analyzed", len(df))
    c2.metric("Top Match Score", f"{df['match_percentage'].max()}%")
    c3.metric("Recommended Candidates", len(df[df['final_recommendation'] == 'Recommended']))

    # Main Table
    st.subheader("📊 Comparison Table")
    
    # Helper to clean lists for table
    def clean_list(x):
        return ", ".join(x) if isinstance(x, list) else x

    df_display = df.copy()
    df_display['strengths'] = df_display['strengths'].apply(clean_list)
    df_display['missing_skills'] = df_display['missing_skills'].apply(clean_list)
    
    st.dataframe(
        df_display[[
            "applicant_name",  
            "years_experience", "education_level", "strengths", "missing_skills","match_percentage", "final_recommendation"
        ]],
        use_container_width=True,
        column_config={
            "applicant_name": st.column_config.TextColumn("Candidate"),
            "match_percentage": st.column_config.ProgressColumn(
                "Match %", format="%d%%", min_value=0, max_value=100
            ),
            "years_experience": st.column_config.TextColumn("Experience"),
            "education_level": st.column_config.TextColumn("Education"),
            "strengths": st.column_config.TextColumn("Strengths"),
            "missing_skills": st.column_config.TextColumn("Missing Skills"),
            "final_recommendation": st.column_config.TextColumn("Verdict")
        }
    )

    # Detailed View
    st.subheader("📑 Detailed Breakdown")
    
    for _, row in df.iterrows():
        # Color coding for expander
        score = row['match_percentage']
        if score >= 85:
            color_emoji = "🟢"
        elif score >= 50:
            color_emoji = "🟡"
        else:
            color_emoji = "🔴"

        with st.expander(f"{color_emoji} {row['applicant_name']} ({row['match_percentage']}%) - {row['final_recommendation']}"):
            
            tab1, tab2 = st.tabs(["🧠 AI Analysis", "📄 Resume File"])
            
            with tab1:
                c_left, c_right = st.columns(2)
                
                with c_left:
                    st.markdown("#### Key Strengths")
                    for s in row['strengths']:
                        st.markdown(f"- ✅ {s}")
                        
                    st.markdown("#### ⚠️ Missing Skills")
                    if row['missing_skills']:
                        for m in row['missing_skills']:
                            st.markdown(f"- {m}")
                    else:
                        st.write("No major skills missing.")

                with c_right:
                    st.markdown("#### 🔍 Evaluation")
                    st.info(row['summary'])
                    
                    st.markdown("#### 🏗️ Skills Gap Analysis")
                    st.write(row['skills_gap'])
                    
                    st.markdown("#### 🎓 Qualifications")
                    st.write(f"**Experience:** {row.get('years_experience', 'N/A')}")
                    st.write(f"**Education:** {row.get('education_level', 'N/A')}")
            
            with tab2:
                file_type = row.get("file_type", "")
                file_b64 = row.get("file_data", "")
                
                if "pdf" in file_type:
                    # Embed PDF Viewer
                    pdf_display = f'<iframe src="data:application/pdf;base64,{file_b64}" width="100%" height="600px" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                else:
                    # Fallback for Word files (Browsers don't support native DOCX embedding)
                    st.warning("⚠️ Word documents cannot be previewed directly in the browser. Showing extracted text below.")
                    st.text_area("Extracted Content", row['resume_text_preview'], height=400, disabled=True)

# --- ENTRY POINT ---
if __name__ == "__main__":
    if check_password():
        main()