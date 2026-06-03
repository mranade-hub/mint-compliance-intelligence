import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
MAIN_AUDIT_FOLDER_ID = os.environ.get("MAIN_AUDIT_FOLDER_ID")