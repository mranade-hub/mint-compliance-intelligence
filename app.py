import sys
import os
import json
import datetime
import asyncio
import re
import shutil

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF

from utils import extract_zip
from pipeline import run_pipeline

# Import Drive functions
from drive_utils import (
    get_drive_service, 
    search_folders_by_name, 
    get_subfolders, 
    download_folder_recursively
)

st.set_page_config(layout="wide", page_title="MINT Compliance Intelligence")

# =====================================================
# CONFIGURATION
# =====================================================
# 🔴 REPLACE THIS WITH YOUR MAIN AUDIT FOLDER ID
MAIN_AUDIT_FOLDER_ID = "0BxOKDhjJWW08dk5lTXQ1M09XaVk" 
TEMP_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_downloads") 

# =====================================================
# ENTERPRISE STYLING
# =====================================================
st.markdown("""
<style>
.block-container { padding-top: 2rem; padding-bottom: 2rem; }
.kpi-card { background-color: #F8F9FA; padding: 20px; border-radius: 12px; text-align: center; }
.kpi-title { font-size: 14px; color: #6c757d; }
.kpi-value { font-size: 28px; font-weight: 600; }
.exec-banner { background-color: #EDF2F7; padding: 25px; border-radius: 14px; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# HELPERS
# =====================================================
def maturity_level(score):
    if score >= 85: return "Optimized"
    elif score >= 70: return "Managed"
    elif score >= 50: return "Developing"
    else: return "Emerging"

def clean_text(text): return re.sub(r'[^\x00-\x7F]+', '', str(text))

def save_audit_history(company, results):
    os.makedirs("audit_history", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"audit_history/{company}_{timestamp}.json", "w") as f:
        json.dump(results, f)

def load_company_history(company):
    if not os.path.exists("audit_history"): return []
    history = []
    for file in os.listdir("audit_history"):
        if file.startswith(company):
            with open(os.path.join("audit_history", file)) as f:
                data = json.load(f)
                data["timestamp"] = file.split("_")[1]
                history.append(data)
    return sorted(history, key=lambda x: x["timestamp"])

def generate_pdf(company, results):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "MINT Compliance Executive Report", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Company: {company}", ln=True)
    pdf.cell(0, 8, f"Overall Score: {results['overall_score']}%", ln=True)
    pdf.cell(0, 8, f"Maturity: {maturity_level(results['overall_score'])}", ln=True)
    pdf.ln(5)
    pdf.multi_cell(0, 6, clean_text(results["executive_summary"]))
    file_path = f"{company}_Compliance_Report.pdf"
    pdf.output(file_path)
    return file_path

def top_gaps(results):
    gaps = []
    for phase, info in results["phases"].items():
        for d in info["documents"]:
            if not d["pass"]: gaps.append((phase, d["document"], d["score"]))
    return sorted(gaps, key=lambda x: x[2])[:5]

# =====================================================
# UI START: UNIFIED FLOW
# =====================================================
st.title("MINT Compliance Intelligence Platform")

# --- STEP 1: PROJECT DETAILS ---
st.markdown("### 1. Project Details")
col_a, col_b = st.columns(2)
with col_a:
    company = st.text_input("Company Name")
with col_b:
    project_type = st.selectbox(
        "Project Type",
        ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"]
    )

st.divider()

# --- STEP 2: GET DATA ---
st.markdown("### 2. Provide Project Data")
data_source = st.radio("Select Data Source:", ["☁️ Fetch from Google Drive", "📁 Upload Local ZIP File"], horizontal=True)

target_zip_for_audit = None

if data_source == "📁 Upload Local ZIP File":
    uploaded_file = st.file_uploader("Upload Project ZIP", type="zip")
    if uploaded_file:
        target_zip_for_audit = uploaded_file

elif data_source == "☁️ Fetch from Google Drive":
    if "matching_folders" not in st.session_state: st.session_state.matching_folders = []
    if "has_searched" not in st.session_state: st.session_state.has_searched = False

    col_search, col_btn = st.columns([4, 1])
    with col_search:
        search_term = st.text_input("Search Drive", placeholder="e.g., Acme Corp...", label_visibility="collapsed")
    with col_btn:
        if st.button("Search", use_container_width=True):
            if not search_term:
                st.warning("⚠️ Enter a search term.")
            else:
                try:
                    drive_service = get_drive_service()
                    if drive_service:
                        with st.spinner("Querying Google Drive..."):
                            results = search_folders_by_name(drive_service, search_term, MAIN_AUDIT_FOLDER_ID)
                            st.session_state.matching_folders = results
                            st.session_state.has_searched = True
                            if results: st.toast(f"Found {len(results)} matches!", icon="✅")
                except Exception as e:
                    st.error(f"Search failed: {e}")

    if st.session_state.has_searched:
        if not st.session_state.matching_folders:
            st.info("No folders found. Try a different spelling.")
        else:
            drive_service = get_drive_service()
            
            main_options = {f"{f['name']} (ID: {f['id']})": f for f in st.session_state.matching_folders}
            selected_main = st.selectbox("Select Main Folder:", options=list(main_options.keys()))
            selected_main_folder = main_options[selected_main]
            
            with st.spinner("Fetching subfolders..."):
                subfolders = get_subfolders(drive_service, selected_main_folder['id'])
            
            target_options = {f"📦 ENTIRE '{selected_main_folder['name']}' Folder": selected_main_folder}
            for sf in subfolders: target_options[f"📁 Subfolder: {sf['name']}"] = sf
                
            selected_target = st.selectbox("Select contents to download:", options=list(target_options.keys()))
            target_folder = target_options[selected_target]
            
            if st.button("⬇️ Download & Prepare for Audit", type="secondary"):
                try:
                    if os.path.exists(TEMP_DOWNLOAD_DIR): shutil.rmtree(TEMP_DOWNLOAD_DIR)
                    base_path = os.path.join(TEMP_DOWNLOAD_DIR, target_folder['name'])
                    
                    my_bar = st.progress(0, text="Downloading files from Google Drive...")
                    
                    with st.spinner(f"Pulling data for '{target_folder['name']}'..."):
                        my_bar.progress(30, text="Traversing folders and downloading...")
                        download_folder_recursively(drive_service, target_folder['id'], base_path)
                    
                    my_bar.progress(80, text="Compressing into a ZIP file...")
                    
                    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
                    zip_path = os.path.join(SCRIPT_DIR, target_folder['name'])
                    shutil.make_archive(zip_path, 'zip', TEMP_DOWNLOAD_DIR)
                    
                    st.session_state.drive_zip_path = f"{zip_path}.zip"
                    
                    if os.path.exists(TEMP_DOWNLOAD_DIR): shutil.rmtree(TEMP_DOWNLOAD_DIR)
                    
                    my_bar.progress(100, text="Complete!")
                    st.success("🎉 Download complete!")
                    
                except Exception as e:
                    st.error(f"Download failed: {e}")

    # If the user successfully downloaded a zip, set it as the target
    if "drive_zip_path" in st.session_state and os.path.exists(st.session_state.drive_zip_path):
        st.info(f"✅ Loaded Drive File: `{os.path.basename(st.session_state.drive_zip_path)}`")
        target_zip_for_audit = st.session_state.drive_zip_path

st.divider()

# --- STEP 3: RUN AUDIT ---
st.markdown("### 3. Execution")
if st.button("🚀 Run Compliance Audit", type="primary", use_container_width=True):
    if not company:
        st.error("⚠️ Please provide a Company Name in Step 1.")
        st.stop()
    if not target_zip_for_audit:
        st.error("⚠️ Please either upload a ZIP or download a folder from Drive in Step 2.")
        st.stop()

    with st.spinner("Running Compliance Intelligence Engine... This may take a few minutes."):
        # target_zip_for_audit is either the st.file_uploader object OR the local file path string
        extract_zip(target_zip_for_audit, company)
        results = run_pipeline(company, project_type)

    save_audit_history(company, results)

    # -----------------------------------------------------
    # RENDER RESULTS (Same as your original code)
    # -----------------------------------------------------
    overall = results["overall_score"]
    maturity = maturity_level(overall)
    benchmark = 68  

    st.markdown("## Executive Intelligence Summary")
    st.markdown(f"""
    <div class="exec-banner">
        <b>Overall Compliance:</b> {overall}% ({maturity})<br>
        <b>Benchmark:</b> {benchmark}%<br>
        <b>Variance:</b> {overall - benchmark:+}%<br><br>
        {results['executive_summary']}
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 Executive View", "⚠ Risk & Gaps", "📂 Phase Analytics", "📈 Trends", "📄 Reports"]
    )

    with tab1:
        total_docs = sum(len(p["documents"]) for p in results["phases"].values())
        passed_docs = sum(1 for p in results["phases"].values() for d in p["documents"] if d["pass"])

        col1, col2, col3 = st.columns(3)
        col1.markdown(f'<div class="kpi-card"><div class="kpi-title">Overall Score</div><div class="kpi-value">{overall}%</div></div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="kpi-card"><div class="kpi-title">Maturity Level</div><div class="kpi-value">{maturity}</div></div>', unsafe_allow_html=True)
        col3.markdown(f'<div class="kpi-card"><div class="kpi-title">Pass Rate</div><div class="kpi-value">{round(passed_docs/total_docs*100,1) if total_docs > 0 else 0}%</div></div>', unsafe_allow_html=True)

        phase_names, phase_scores = [], []
        for phase, info in results["phases"].items():
            phase_names.append(phase)
            phase_scores.append(info["score"])

        radar = go.Figure()
        radar.add_trace(go.Scatterpolar(
            r=phase_scores + [phase_scores[0]] if phase_scores else [],
            theta=phase_names + [phase_names[0]] if phase_names else [],
            fill='toself', line=dict(color='#264653', width=3), fillcolor='rgba(38, 70, 83, 0.3)'
        ))
        radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), template="plotly_white", showlegend=False)
        st.plotly_chart(radar, use_container_width=True)

    with tab2:
        st.subheader("Priority Remediation Targets")
        gaps = top_gaps(results)
        for g in gaps: st.error(f"{g[0]} → {g[1]} ({g[2]}%)")

    with tab3:
        heat_data = [{"Phase": phase, "Document": d["document"], "Score": d["score"]} for phase, info in results["phases"].items() for d in info["documents"]]
        if heat_data:
            heat_df = pd.DataFrame(heat_data)
            pivot = heat_df.pivot(index="Document", columns="Phase", values="Score")
            heatmap = px.imshow(pivot, color_continuous_scale="RdYlGn", aspect="auto", template="plotly_white")
            st.plotly_chart(heatmap, use_container_width=True)

    with tab4:
        history = load_company_history(company)
        if len(history) > 1:
            trend_df = pd.DataFrame([{"Timestamp": h["timestamp"], "Score": h["overall_score"]} for h in history])
            trend_chart = px.line(trend_df, x="Timestamp", y="Score", markers=True, template="plotly_white")
            st.plotly_chart(trend_chart, use_container_width=True)
        else:
            st.info("Run another audit later to unlock trend analytics.")

    with tab5:
        pdf_path = generate_pdf(company, results)
        with open(pdf_path, "rb") as f:
            st.download_button("Download Executive PDF Report", f, file_name=pdf_path, mime="application/pdf")