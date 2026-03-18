import os
import io
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(SCRIPT_DIR, "credentials.json")
TOKEN_PATH = os.path.join(SCRIPT_DIR, "token.json")

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

GOOGLE_MIME_TYPES = {
    'application/vnd.google-apps.document': ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx'),
    'application/vnd.google-apps.spreadsheet': ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx'),
    'application/vnd.google-apps.presentation': ('application/vnd.openxmlformats-officedocument.presentationml.presentation', '.pptx')
}

def authenticate():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                return None
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                print(f"Error: '{CREDENTIALS_PATH}' not found.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
    return creds

def get_drive_service():
    creds = authenticate()
    if creds:
        return build("drive", "v3", credentials=creds)
    return None

def search_folders_by_name(service, search_term, parent_id):
    safe_term = search_term.replace("'", "\\'")
    query = (
        f"name contains '{safe_term}' and "
        f"'{parent_id}' in parents and "
        f"mimeType = 'application/vnd.google-apps.folder' and "
        f"trashed = false"
    )
    response = service.files().list(
        q=query, spaces='drive', fields='files(id, name)',
        supportsAllDrives=True, includeItemsFromAllDrives=True, orderBy="name" 
    ).execute()
    return response.get('files', [])

def get_subfolders(service, parent_id):
    query = (
        f"'{parent_id}' in parents and "
        f"mimeType = 'application/vnd.google-apps.folder' and "
        f"trashed = false"
    )
    response = service.files().list(
        q=query, spaces='drive', fields='files(id, name)',
        supportsAllDrives=True, includeItemsFromAllDrives=True, orderBy="name"
    ).execute()
    return response.get('files', [])

def download_file(service, file_id, file_name, mime_type, save_path):
    try:
        if mime_type in GOOGLE_MIME_TYPES:
            export_mime, ext = GOOGLE_MIME_TYPES[mime_type]
            file_name += ext
            request = service.files().export_media(fileId=file_id, mimeType=export_mime)
        elif 'application/vnd.google-apps' in mime_type:
            return  
        else:
            request = service.files().get_media(fileId=file_id)

        file_path = os.path.join(save_path, file_name)
        fh = io.FileIO(file_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
    except Exception as e:
        print(f"Failed to download {file_name}: {e}")

def download_folder_recursively(service, folder_id, current_local_path):
    if not os.path.exists(current_local_path):
        os.makedirs(current_local_path)
        
    page_token = None
    while True:
        q = f"'{folder_id}' in parents and trashed = false"
        response = service.files().list(
            q=q, pageSize=200, fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token, supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute()
        
        items = response.get("files", [])
        for item in items:
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                new_folder_path = os.path.join(current_local_path, item['name'])
                download_folder_recursively(service, item['id'], new_folder_path)
            else:
                download_file(service, item['id'], item['name'], item['mimeType'], current_local_path)
                
        page_token = response.get("nextPageToken", None)
        if page_token is None:
            break