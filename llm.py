import streamlit as st
from openai import AzureOpenAI
import json

def get_azure_client():
    # Fetch credentials from .streamlit/secrets.toml
    try:
        return AzureOpenAI(
            api_key=st.secrets["azure"]["OPENAI_API_KEY"],
            api_version=st.secrets["azure"]["OPENAI_API_VERSION"],
            azure_endpoint=st.secrets["azure"]["OPENAI_ENDPOINT"],
        )
    except KeyError:
        st.error("❌ Azure credentials missing in secrets.toml")
        st.stop()

def analyze_resume(prompt: str) -> str:
    client = get_azure_client()
    deployment = st.secrets["azure"]["OPENAI_CHAT_DEPLOYMENT"]

    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise AI Recruiter. Output JSON only."
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,  # Lower temperature for consistent JSON
            max_tokens=1500,
            response_format={"type": "json_object"} # Ensures JSON output if model supports it
        )
        return response.choices[0].message.content
        
    except Exception as e:
        return json.dumps({
            "applicant_name": "Error",
            "match_percentage": 0,
            "final_recommendation": "Rejected",
            "summary": f"API Error: {str(e)}",
            "strengths": [],
            "missing_skills": [],
            "skills_gap": "Analysis failed due to technical error."
        })