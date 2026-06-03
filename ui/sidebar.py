import os
import shutil
import zipfile
import datetime
import streamlit as st

from config import MAIN_AUDIT_FOLDER_ID
from drive_utils import get_drive_service, search_folders_by_name, get_subfolders, download_folder_recursively
from logger_utils import append_log
from pipeline import run_pipeline
from services.sheets_db import load_company_history, save_to_google_sheets
from services.history_manager import save_audit_history, get_last_audit_rfc3339, merge_incremental_results

def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="padding: 24px 0 20px 0; border-bottom: 1px solid rgba(99,179,237,0.1); margin-bottom: 24px;">
            <div class="sidebar-logo">◈ Adherence Intelligence Platform</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="mint-section-label">Engagement Setup</div>', unsafe_allow_html=True)
        company = st.text_input("Company Name", placeholder="e.g. Acme Corporation", label_visibility="collapsed")
        st.markdown('<div style="font-size:0.72rem; color:#475569; margin-bottom:6px; letter-spacing:0.05em; text-transform:uppercase;">Company Name</div>', unsafe_allow_html=True)

        project_category = st.selectbox(
            "Project Category",
            ["MINT", "Solution Partner - T&T", "Track and Trace"],
            label_visibility="visible"
        )

        project_type = st.selectbox(
            "Engagement Type",
            ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"],
            label_visibility="visible"
        )

        forced_phase = st.selectbox(
            "Force Project Phase",
            ["Auto-Detect", "Engage", "Design", "Build", "Execute", "Test", "Deploy", "Service", "Hypercare & Project Closure"],
            help="If Auto-Detect fails, select the current phase to prevent the bot from penalizing future documents."
        )

        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
        st.markdown('<div class="mint-section-label">Data Source</div>', unsafe_allow_html=True)

        data_source = st.radio(
            "Data Source",
            ["Google Drive", "Local ZIP Upload", "Load Previous Audit"],
            label_visibility="collapsed"
        )

        target_zip_for_audit = None
        drive_ready = False
        target_folder_name = "Unknown"
        is_incremental = False

        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

        # ── Load Previous Audit ──
        if data_source == "Load Previous Audit":
            if not company:
                st.markdown('<div style="font-size:0.8rem; color:#64748B; padding:10px 0;">Enter a company name to load history.</div>', unsafe_allow_html=True)
            else:
                history = load_company_history(company)
                if not history:
                    st.markdown('<div style="font-size:0.8rem; color:#64748B; padding:10px 0;">No previous audits found for this entity.</div>', unsafe_allow_html=True)
                else:
                    options = {
                        f"{h.get('audit_timestamp', 'Unknown')}  -  {h.get('overall_score', 0)}% adherence": h
                        for h in history
                    }
                    selected_key = st.selectbox("Select Audit Record", list(options.keys()))
                    if st.button("Load Audit", type="primary", width="stretch"):
                        st.session_state.audit_results = options[selected_key]
                        st.session_state.audit_company = company
                        st.rerun()

        # ── ZIP Upload ──
        elif data_source == "Local ZIP Upload":
            uploaded_file = st.file_uploader("Upload ZIP Archive", type="zip")
            is_incremental = st.checkbox("Incremental Audit (Only fetch new/modified files)", value=True)

            if uploaded_file:
                target_zip_for_audit = uploaded_file
                target_folder_name = uploaded_file.name
                st.markdown(f'<div style="font-size:0.78rem; color:#4ADE80; padding:6px 0;">✓ {uploaded_file.name}</div>', unsafe_allow_html=True)

        # ── Google Drive ──
        elif data_source == "Google Drive":
            search_term = st.text_input("Search Drive", placeholder="Enter company folder name")

            if st.button("Search Drive", width="stretch"):
                if search_term:
                    try:
                        drive_service = get_drive_service()
                        if drive_service:
                            with st.spinner("Searching..."):
                                st.session_state.matching_folders = search_folders_by_name(
                                    drive_service, search_term, MAIN_AUDIT_FOLDER_ID
                                )
                                st.session_state.has_searched = True
                    except Exception as e:
                        st.error(f"Drive connection failed: {e}")

            if st.session_state.has_searched and st.session_state.matching_folders:
                drive_service = get_drive_service()
                main_options = {f["name"]: f for f in st.session_state.matching_folders}
                
                if main_options:
                    selected_main_folder = main_options[st.selectbox("Root Folder", list(main_options.keys()))]

                    with st.spinner("Loading subfolders..."):
                        subfolders = get_subfolders(drive_service, selected_main_folder["id"])

                    target_options = {"Entire Vault": selected_main_folder}
                    for sf in subfolders:
                        target_options[sf["name"]] = sf

                    target_folder = target_options[st.selectbox("Target Folder", list(target_options.keys()))]
                    target_folder_name = target_folder["name"]

                    is_incremental = st.checkbox("Incremental Audit (Only fetch new/modified files)", value=True)

                    if st.button("Extract Files", width="stretch"):
                        if company:
                            try:
                                target_dir = f"downloads/{company}"
                                if os.path.exists(target_dir):
                                    shutil.rmtree(target_dir)
                                os.makedirs(target_dir, exist_ok=True)

                                with st.spinner("Downloading from Drive..."):
                                    target_date = None
                                    if is_incremental:
                                        target_date = get_last_audit_rfc3339(company)
                                        if target_date:
                                            st.toast(f"Fetching files modified after: {target_date}")
                                        else:
                                            st.toast("No previous audit found. Running full fetch.")

                                    download_folder_recursively(drive_service, target_folder["id"], target_dir, modified_after=target_date)

                                if os.path.exists("temp_downloads"):
                                    shutil.rmtree("temp_downloads")
                                st.success("Extraction complete.")
                                drive_ready = True
                            except Exception as e:
                                st.error(f"Extraction failed: {e}")
            elif st.session_state.has_searched:
                st.warning("No folders found. Refine your search term.")

        # ── Initiate Audit Button ──
        if data_source != "Load Previous Audit":
            st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
            st.markdown('<hr style="border-color:rgba(99,179,237,0.08);">', unsafe_allow_html=True)

            if st.button("Run Adherence Audit", type="primary", width="stretch"):
                if not company:
                    st.error("Company name is required.")
                elif data_source == "Local ZIP Upload" and not target_zip_for_audit:
                    st.error("Please upload a ZIP archive.")
                elif data_source == "Google Drive" and not drive_ready and not os.path.exists(f"downloads/{company}"):
                    st.error("Please extract files from Drive first.")
                else:
                    with st.status("Running adherence audit...", expanded=True) as status_box:
                        progress_bar = st.progress(0, text="Initializing...")

                        def file_logger(msg):
                            append_log(company, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

                        def ui_progress(current, total, message="Processing"):
                            pct = int((current / total) * 100) if total > 0 else 0
                            progress_bar.progress(
                                current / total if total > 0 else 0,
                                text=f"{message}  ({pct}%)"
                            )

                        if target_zip_for_audit:
                            file_logger("[SYSTEM] Inspecting uploaded archive for incremental changes...")
                            target_dir = f"downloads/{company}"
                            if os.path.exists(target_dir):
                                shutil.rmtree(target_dir)
                            os.makedirs(target_dir, exist_ok=True)
                            
                            target_zip_for_audit.seek(0)
                            with zipfile.ZipFile(target_zip_for_audit, "r") as zip_ref:
                                target_date_str = None
                                target_date_utc = None
                                if is_incremental:
                                    target_date_str = get_last_audit_rfc3339(company)
                                    if target_date_str:
                                        target_date_utc = datetime.datetime.strptime(target_date_str, "%Y-%m-%dT%H:%M:%S.000Z")
                                        target_date_utc = target_date_utc.replace(tzinfo=datetime.timezone.utc)

                                extracted_count = 0
                                for zip_info in zip_ref.infolist():
                                    if zip_info.is_dir():
                                        continue

                                    should_extract = True
                                    if target_date_utc:
                                        file_dt_naive = datetime.datetime(*zip_info.date_time)
                                        file_dt_local = file_dt_naive.astimezone()
                                        file_dt_utc = file_dt_local.astimezone(datetime.timezone.utc)

                                        if file_dt_utc <= target_date_utc:
                                            should_extract = False

                                    if should_extract:
                                        zip_ref.extract(zip_info, target_dir)
                                        extracted_count += 1

                                file_logger(f"[SYSTEM] Extracted {extracted_count} modified files from archive.")

                        pass_phase = None if forced_phase == "Auto-Detect" else forced_phase
                        
                        raw_results = run_pipeline(
                            company,
                            project_category,
                            project_type,
                            log_callback=file_logger,
                            progress_callback=ui_progress,
                            forced_phase=pass_phase,
                            folder_name=target_folder_name
                        )

                        if data_source in ["Google Drive", "Local ZIP Upload"] and is_incremental and get_last_audit_rfc3339(company):
                            file_logger("[SYSTEM] Merging incremental results with master history...")
                            previous_history = load_company_history(company)[0]
                            final_results = merge_incremental_results(previous_history, raw_results)
                        else:
                            final_results = raw_results

                        save_audit_history(company, final_results)
                        file_logger("[SYSTEM] Appending record to Google Sheets Ledger...")
                        save_to_google_sheets(company, final_results)
                        status_box.update(label="Audit complete.", state="complete", expanded=False)

                    st.session_state.audit_results = final_results
                    st.session_state.audit_company = company
                    st.rerun()

        # ── Reset ──
        if st.session_state.audit_results is not None:
            st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
            if st.button("Clear Dashboard", width="stretch"):
                st.session_state.audit_results = None
                st.session_state.audit_company = None
                st.rerun()