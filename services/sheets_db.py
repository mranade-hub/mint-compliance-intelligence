import os
import json
import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from config import SPREADSHEET_ID

def save_to_google_sheets(company, results):
    """Appends the audit record as a new row in a Google Sheet."""
    try:
        RANGE_NAME = "Sheet1!A:F"

        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json')
        else:
            print("[ERROR] token.json not found. Run Drive extraction first to generate it.")
            return

        service = build('sheets', 'v4', credentials=creds)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        category = str(results.get("project_category", "Unknown"))
        score = float(results.get("overall_score", 0.0))
        risk = str(results.get("risk_level", "Unknown"))
        raw_json = json.dumps(results)

        values = [[timestamp, company, category, score, risk, raw_json]]
        body = {'values': values}

        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID, 
            range=RANGE_NAME,
            valueInputOption="USER_ENTERED", 
            body=body
        ).execute()
        
        print(f"[SUCCESS] Inserted into Google Sheets Database.")
        
    except Exception as e:
        print(f"[ERROR] Google Sheets Exception: {e}")

def load_company_history(company):
    """Fetches previous audit history directly from the Google Sheets database."""
    history = []
    try:
        RANGE_NAME = "Sheet1!A:F" 

        if not os.path.exists('token.json'):
            print("[WARNING] token.json not found. Cannot fetch history from Sheets.")
            return history

        creds = Credentials.from_authorized_user_file('token.json')
        service = build('sheets', 'v4', credentials=creds)

        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME
        ).execute()
        
        rows = result.get('values', [])
        
        for row in rows:
            if len(row) >= 6 and row[1].strip().lower() == company.strip().lower():
                try:
                    data = json.loads(row[5])
                    
                    if "audit_timestamp" not in data:
                        try:
                            dt = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                            data["audit_timestamp"] = dt.strftime("%Y%m%d_%H%M%S")
                        except ValueError:
                            data["audit_timestamp"] = row[0]
                            
                    history.append(data)
                except json.JSONDecodeError:
                    print(f"[WARNING] Could not parse the raw JSON data for a row belonging to {company}.")
                    continue
                    
    except Exception as e:
        print(f"[ERROR] Failed to fetch history from Google Sheets: {e}")

    return sorted(history, key=lambda x: x.get("audit_timestamp", ""), reverse=True)