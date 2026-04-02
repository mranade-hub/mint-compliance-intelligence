import streamlit as st
import os
import io
import shutil
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

# --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# 0. PAGE CONFIGURATION (Must be the first Streamlit command)
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
st.set_page_config(
    page_title="Audit Folder Downloader",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# 1. CONFIGURATION
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(SCRIPT_DIR, "credentials.json")
TOKEN_PATH = os.path.join(SCRIPT_DIR, "token.json")
TEMP_DOWNLOAD_DIR = os.path.join(SCRIPT_DIR, "temp_downloads") 

# 🔴 REPLACE THIS WITH YOUR MAIN AUDIT FOLDER ID
MAIN_AUDIT_FOLDER_ID = "0BxOKDhjJWW08dk5lTXQ1M09XaVk" 

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

GOOGLE_MIME_TYPES = {
    'application/vnd.google-apps.document': ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx'),
    'application/vnd.google-apps.spreadsheet': ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx'),
    'application/vnd.google-apps.presentation': ('application/vnd.openxmlformats-officedocument.presentationml.presentation', '.pptx')
}

# --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# 2. GOOGLE AUTH & DRIVE LOGIC
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
@st.cache_resource
def authenticate():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                st.sidebar.error(f"Error refreshing token: {e}")
                return None
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                st.sidebar.error(f"Error: '{CREDENTIALS_PATH}' not found.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
    return creds

@st.cache_resource
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

# --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# 3. STREAMLIT UI SETUP
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

# Sidebar for metadata / instructions
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/1/12/Google_Drive_icon_%282020%29.svg", width=60)
    st.title("Audit Exporter")
    st.markdown("---")
    st.markdown("""
    **How to use:**
    1. Enter a company name.
    2. Select the correct main folder.
    3. Choose a specific subfolder (or download all).
    4. Export as a ZIP file.
    """)
    st.markdown("---")
    st.caption("Google Drive API Authenticated 🟢")

# Main Page Header
st.header("🗂️ Audit Folder Downloader")
st.markdown("Search and extract company audit folders directly from Google Drive.")
st.divider()

# Initialize session states
if "matching_folders" not in st.session_state:
    st.session_state.matching_folders = []
if "has_searched" not in st.session_state:
    st.session_state.has_searched = False
if "selected_main_folder_id" not in st.session_state:
    st.session_state.selected_main_folder_id = None

# --- STEP 1: SEARCH CARD ---
with st.container(border=True):
    st.subheader("🔍 Step 1: Search Directory")
    
    # Use columns to put the search bar and button on the same line
    col1, col2 = st.columns([4, 1])
    
    with col1:
        search_term = st.text_input(
            "Company Name", 
            placeholder="e.g., Acme Corp...", 
            label_visibility="collapsed"
        )
    with col2:
        search_button = st.button("Search", use_container_width=True, type="primary")

    if search_button:
        if not search_term:
            st.warning("⚠️ Please enter a search term.")
        elif MAIN_AUDIT_FOLDER_ID == "YOUR_MAIN_AUDIT_FOLDER_ID_HERE":
            st.error("⚠️ Please update `MAIN_AUDIT_FOLDER_ID` in the code!")
        else:
            try:
                drive_service = get_drive_service()
                if drive_service:
                    with st.spinner(f"Querying Drive for '{search_term}'..."):
                        results = search_folders_by_name(drive_service, search_term, MAIN_AUDIT_FOLDER_ID)
                        
                        st.session_state.matching_folders = results
                        st.session_state.has_searched = True
                        
                        # Reset downstream UI states
                        st.session_state.selected_main_folder_id = None
                        if "zip_file_path" in st.session_state:
                            del st.session_state["zip_file_path"]
                            
                        if results:
                            st.toast(f"Found {len(results)} matches!", icon="✅")
                        
            except Exception as e:
                st.error(f"Search failed: {e}")

# --- STEP 2: SELECT TARGET CARD ---
if st.session_state.has_searched:
    with st.container(border=True):
        st.subheader("📂 Step 2: Select Target")
        
        if not st.session_state.matching_folders:
            st.info("No folders found matching that search term. Try a different spelling.")
        else:
            drive_service = get_drive_service()
            
            # 2A: Main Folder Selection
            main_folder_options = {f"{f['name']} (ID: {f['id']})": f for f in st.session_state.matching_folders}
            selected_main_option = st.selectbox(
                "Select Main Company Folder:", 
                options=list(main_folder_options.keys())
            )
            selected_main_folder = main_folder_options[selected_main_option]
            
            # Check if main folder selection changed to reset zip file
            if st.session_state.selected_main_folder_id != selected_main_folder['id']:
                st.session_state.selected_main_folder_id = selected_main_folder['id']
                if "zip_file_path" in st.session_state:
                    del st.session_state["zip_file_path"]

            st.markdown("---")
            
            # 2B: Subfolder Selection
            with st.spinner("Fetching contents..."):
                subfolders = get_subfolders(drive_service, selected_main_folder['id'])
            
            target_options = {f"📦 Download ENTIRE '{selected_main_folder['name']}' Folder": selected_main_folder}
            for sf in subfolders:
                target_options[f"📁 Subfolder: {sf['name']}"] = sf
                
            selected_target_option = st.selectbox(
                "Select specific contents to download:",
                options=list(target_options.keys())
            )
            target_folder_to_download = target_options[selected_target_option]
            
            st.write("") # Add a little spacing
            
            # 2C: Trigger Download Process
            if st.button("☁️ Generate ZIP File", use_container_width=True):
                try:
                    # Clean up local temp directory first
                    if os.path.exists(TEMP_DOWNLOAD_DIR):
                        shutil.rmtree(TEMP_DOWNLOAD_DIR)
                    
                    base_folder_path = os.path.join(TEMP_DOWNLOAD_DIR, target_folder_to_download['name'])
                    
                    # Setup progress bar
                    progress_text = "Downloading files from Google Drive..."
                    my_bar = st.progress(0, text=progress_text)
                    
                    # Start Download
                    with st.spinner(f"Pulling data for '{target_folder_to_download['name']}'..."):
                        # (A real progress bar for recursion is complex, so we just show an indeterminate spinner here alongside the progress bar visual)
                        my_bar.progress(30, text="Traversing folders and downloading files...")
                        download_folder_recursively(drive_service, target_folder_to_download['id'], base_folder_path)
                    
                    my_bar.progress(80, text="Compressing into a ZIP file...")
                    
                    # Zip it up
                    zip_path = os.path.join(SCRIPT_DIR, target_folder_to_download['name'])
                    shutil.make_archive(zip_path, 'zip', TEMP_DOWNLOAD_DIR)
                    
                    st.session_state.zip_file_path = f"{zip_path}.zip"
                    st.session_state.zip_file_name = f"{target_folder_to_download['name']}.zip"
                    
                    # Clean up unzipped files immediately
                    if os.path.exists(TEMP_DOWNLOAD_DIR):
                        shutil.rmtree(TEMP_DOWNLOAD_DIR)
                    
                    my_bar.progress(100, text="Complete!")
                    st.success("🎉 Folder processed and ready for download!")
                    
                except Exception as e:
                    st.error(f"Download process failed: {e}")

# --- STEP 3: DOWNLOAD CARD ---
if "zip_file_path" in st.session_state and os.path.exists(st.session_state.zip_file_path):
    with st.container(border=True):
        st.subheader("✅ Step 3: Save File")
        
        # Displaying file info
        file_size_bytes = os.path.getsize(st.session_state.zip_file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        col_info, col_btn = st.columns([3, 1])
        with col_info:
            st.markdown(f"**File Name:** `{st.session_state.zip_file_name}`")
            st.markdown(f"**Size:** `{file_size_mb:.2f} MB`")
            
        with col_btn:
            with open(st.session_state.zip_file_path, "rb") as fp:
                st.download_button(
                    label="⬇️ Download ZIP",
                    data=fp,
                    file_name=st.session_state.zip_file_name,
                    mime="application/zip",
                    type="primary",
                    use_container_width=True
                )