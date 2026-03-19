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

st.set_page_config(layout="wide", page_title="MINT Command Center", initial_sidebar_state="expanded")

# =====================================================
# CONFIGURATION & SESSION STATE
# =====================================================
MAIN_AUDIT_FOLDER_ID = "0BxOKDhjJWW08dk5lTXQ1M09XaVk" 

if "audit_results" not in st.session_state:
    st.session_state.audit_results = None
if "audit_company" not in st.session_state:
    st.session_state.audit_company = None

# =====================================================
# HIGH-CONTRAST "CONTROL ROOM" STYLING
# =====================================================
st.markdown("""
<style>
/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: #1E1E2F;
    color: white;
}
/* KPI Cards */
.kpi-container {
    display: flex;
    gap: 20px;
    margin-bottom: 30px;
}
.kpi-card-dark {
    background-color: #2D2D44;
    border-left: 5px solid #00FFC4;
    padding: 20px;
    border-radius: 8px;
    flex: 1;
    color: white;
    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
}
.kpi-title-dark {
    font-size: 14px;
    color: #A0A0B5;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.kpi-value-dark {
    font-size: 36px;
    font-weight: 700;
    margin-top: 10px;
    color: #FFFFFF;
}
/* Sections */
.section-header {
    border-bottom: 2px solid #E2E8F0;
    padding-bottom: 10px;
    margin-top: 40px;
    margin-bottom: 20px;
    color: #1E293B;
}
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

def clean_text(text): 
    return re.sub(r'[^\x00-\x7F]+', '', str(text))

def save_audit_history(company, results):
    os.makedirs("audit_history", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"audit_history/{company}_{timestamp}.json", "w") as f:
        json.dump(results, f)

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
# SIDEBAR: SETUP & INGESTION
# =====================================================
with st.sidebar:
    st.title("⚙️ Setup")
    
    company = st.text_input("Company Name")
    project_type = st.selectbox(
        "Project Type",
        ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"]
    )
    
    st.divider()
    
    st.subheader("Data Source")
    data_source = st.radio("Fetch method:", ["☁️ Google Drive", "📁 Local ZIP File"])
    
    target_zip_for_audit = None
    drive_ready = False
    
    # LOCAL ZIP
    if data_source == "📁 Local ZIP File":
        uploaded_file = st.file_uploader("Upload ZIP", type="zip")
        if uploaded_file:
            target_zip_for_audit = uploaded_file
            
    # GOOGLE DRIVE
    elif data_source == "☁️ Google Drive":
        if "matching_folders" not in st.session_state: st.session_state.matching_folders = []
        if "has_searched" not in st.session_state: st.session_state.has_searched = False

        search_term = st.text_input("Search Drive Folders")
        if st.button("Search", use_container_width=True):
            if search_term:
                try:
                    drive_service = get_drive_service()
                    if drive_service:
                        with st.spinner("Querying Drive..."):
                            results = search_folders_by_name(drive_service, search_term, MAIN_AUDIT_FOLDER_ID)
                            st.session_state.matching_folders = results
                            st.session_state.has_searched = True
                except Exception as e:
                    st.error(f"Search failed: {e}")

        if st.session_state.has_searched and st.session_state.matching_folders:
            drive_service = get_drive_service()
            main_options = {f"{f['name']}": f for f in st.session_state.matching_folders}
            selected_main = st.selectbox("Select Main Folder:", options=list(main_options.keys()))
            selected_main_folder = main_options[selected_main]
            
            # --- RESTORED SUBFOLDER LOGIC ---
            with st.spinner("Fetching subfolders..."):
                subfolders = get_subfolders(drive_service, selected_main_folder['id'])
            
            target_options = {f"📦 ENTIRE '{selected_main_folder['name']}' Folder": selected_main_folder}
            for sf in subfolders: 
                target_options[f"📁 Subfolder: {sf['name']}"] = sf
                
            selected_target = st.selectbox("Select contents to download:", options=list(target_options.keys()))
            target_folder = target_options[selected_target]
            # --------------------------------

            if st.button("⬇️ Download Files", type="primary", use_container_width=True):
                if not company:
                    st.error("Enter Company Name first!")
                else:
                    try:
                        # SUPER SPEED UP: Download directly into the pipeline's expected folder.
                        target_dir = f"downloads/{company}"
                        if os.path.exists(target_dir): shutil.rmtree(target_dir)
                        os.makedirs(target_dir, exist_ok=True)
                        
                        with st.spinner("Downloading directly to pipeline..."):
                            # Using target_folder ID so it respects subfolder choice
                            download_folder_recursively(drive_service, target_folder['id'], target_dir)
                        
                        st.success("Files ready!")
                        drive_ready = True
                    except Exception as e:
                        st.error(f"Download failed: {e}")

    st.divider()
    
    # EXECUTION BUTTON
    if st.button("🚀 RUN AUDIT", type="primary", use_container_width=True):
        if not company:
            st.error("Provide a Company Name.")
        elif data_source == "📁 Local ZIP File" and not target_zip_for_audit:
            st.error("Upload a ZIP file.")
        elif data_source == "☁️ Google Drive" and not drive_ready and not os.path.exists(f"downloads/{company}"):
            st.error("Download files from Drive first.")
        else:
            with st.spinner("Running MINT Compliance Engine..."):
                # Only extract if we are using a local ZIP. Drive files are already in place!
                if target_zip_for_audit:
                    extract_zip(target_zip_for_audit, company)
                    
                results = run_pipeline(company, project_type)
                save_audit_history(company, results)
                
                # Save to session state to prevent refresh bugs
                st.session_state.audit_results = results
                st.session_state.audit_company = company


# =====================================================
# MAIN DASHBOARD AREA (TOP-DOWN NARRATIVE)
# =====================================================

if st.session_state.audit_results is None:
    st.title("MINT Command Center")
    st.info("👈 Use the setup menu on the left to configure and run an audit.")
else:
    results = st.session_state.audit_results
    comp = st.session_state.audit_company
    
    overall = results["overall_score"]
    maturity = maturity_level(overall)
    
    total_docs = sum(len(p["documents"]) for p in results["phases"].values())
    passed_docs = sum(1 for p in results["phases"].values() for d in p["documents"] if d["pass"])
    pass_rate = round(passed_docs/total_docs*100,1) if total_docs > 0 else 0

    st.title(f"Intelligence Brief: {comp}")
    st.caption(f"Risk Level: {results['risk_level']} | Detected Phase: {results['detected_phase']}")

    # --- ROW 1: KPI CARDS ---
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card-dark">
            <div class="kpi-title-dark">Overall Compliance</div>
            <div class="kpi-value-dark">{overall}%</div>
        </div>
        <div class="kpi-card-dark" style="border-left-color: #FF007F;">
            <div class="kpi-title-dark">Maturity Status</div>
            <div class="kpi-value-dark">{maturity}</div>
        </div>
        <div class="kpi-card-dark" style="border-left-color: #0088FF;">
            <div class="kpi-title-dark">Pass Rate</div>
            <div class="kpi-value-dark">{pass_rate}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- ROW 2: RADAR & GAPS ---
    st.markdown('<h3 class="section-header">Performance & Vulnerabilities</h3>', unsafe_allow_html=True)
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        phase_names, phase_scores = [], []
        for phase, info in results["phases"].items():
            phase_names.append(phase)
            phase_scores.append(info["score"])

        radar = go.Figure()
        radar.add_trace(go.Scatterpolar(
            r=phase_scores + [phase_scores[0]] if phase_scores else [],
            theta=phase_names + [phase_names[0]] if phase_names else [],
            fill='toself', line=dict(color='#00FFC4', width=3), fillcolor='rgba(0, 255, 196, 0.1)'
        ))
        radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])), 
            margin=dict(l=40, r=40, t=20, b=20),
            height=350
        )
        st.plotly_chart(radar, use_container_width=True)

    with col2:
        st.markdown("#### Priority Remediation Targets")
        gaps = top_gaps(results)
        if not gaps:
            st.success("No major compliance gaps found! 🎉")
        else:
            for phase, doc, score in gaps:
                ai_comment = "No specific comment provided."
                for d in results["phases"][phase]["documents"]:
                    if d["document"] == doc:
                        ai_comment = d.get("comment", ai_comment)
                        break

                with st.expander(f"🚨 {doc} ({score}%)"):
                    st.write(f"**Phase:** {phase}")
                    st.write(f"**AI Diagnostics:** {ai_comment}")

    # --- ROW 3: HEATMAP ---
    st.markdown('<h3 class="section-header">Phase Analytics Heatmap</h3>', unsafe_allow_html=True)
    heat_data = [{"Phase": phase, "Document": d["document"], "Score": d["score"]} for phase, info in results["phases"].items() for d in info["documents"]]
    if heat_data:
        heat_df = pd.DataFrame(heat_data)
        pivot = heat_df.pivot(index="Document", columns="Phase", values="Score")
        heatmap = px.imshow(pivot, color_continuous_scale="RdYlGn", aspect="auto")
        heatmap.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(heatmap, use_container_width=True)

    # --- ROW 4: ARTIFACTS ---
    st.markdown('<h3 class="section-header">Export Artifacts</h3>', unsafe_allow_html=True)
    dl_col1, dl_col2 = st.columns(2)

    with dl_col1:
        pdf_path = generate_pdf(comp, results)
        with open(pdf_path, "rb") as f:
            st.download_button("📄 Download Executive PDF", f, file_name=pdf_path, mime="application/pdf", use_container_width=True)

    with dl_col2:
        csv_data = []
        for phase, info in results["phases"].items():
            for d in info["documents"]:
                csv_data.append({"Phase": phase, "Document": d["document"], "Status": "Pass" if d["pass"] else "Fail", "Score": d["score"], "AI Comment": d.get("comment", "")})
        
        csv_df = pd.DataFrame(csv_data)
        csv_bytes = csv_df.to_csv(index=False).encode('utf-8')
        st.download_button("📊 Download Audit CSV", data=csv_bytes, file_name=f"{comp}_Audit.csv", mime="text/csv", use_container_width=True)