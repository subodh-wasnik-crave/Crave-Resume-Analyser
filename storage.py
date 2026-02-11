import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

def get_gspread_client():
    """Authenticates with Google Sheets using secrets."""
    try:
        # Load service account info from secrets
        service_account_info = st.secrets["connections"]["gsheets"]
        
        # Define scopes
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Create credentials from the dictionary in secrets
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            dict(service_account_info), 
            scopes
        )
        
        client = gspread.authorize(creds)
        return client
        
    except Exception as e:
        # If credentials aren't set up, log specific error
        print(f"Google Sheets Auth Error: {e}")
        return None

def save_to_google_sheet(data):
    """Appends analysis data to the configured Google Sheet."""
    
    # 1. Check if configured
    if "connections" not in st.secrets or "gsheets" not in st.secrets["connections"]:
        print("Google Sheets secrets not found. Skipping cloud save.")
        return

    client = get_gspread_client()
    if not client:
        return

    try:
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet_url"]
        sheet = client.open_by_url(sheet_url).sheet1
        
        # Prepare row data (Flatten list fields)
        row = [
            data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            data.get("analyzed_by", "Unknown"),
            data.get("applicant_name", "Unknown"),
            data.get("resume_file", ""),
            data.get("match_percentage", 0),
            data.get("final_recommendation", ""),
            ", ".join(data.get("strengths", [])),
            ", ".join(data.get("missing_skills", [])),
            data.get("summary", ""),
            data.get("years_experience", ""),
            data.get("education_level", "")
        ]
        
        # Append to sheet
        sheet.append_row(row)
        
    except Exception as e:
        raise Exception(f"Failed to write to Google Sheet: {str(e)}")