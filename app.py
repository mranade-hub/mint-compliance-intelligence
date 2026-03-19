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

# --- PAGE CONFIGURATION ---
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
    background-color: #121212;
    color: white;
}
/* Sections */
.section-header {
    border-bottom: 1px solid #333;
    padding-bottom: 10px;
    margin-top: 40px;
    margin-bottom: 20px;
    color: #F8F9FA;
    font-weight: 300;
}
/* Override main background for true dark mode */
.stApp {
    background-color: #0E1117;
    color: #C9D1D9;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# HELPERS & BUG FIXES
# =====================================================
def maturity_level(score):
    if score >= 85: return "Optimized"
    elif score >= 70: return "Managed"
    elif score >= 50: return "Developing"
    else: return "Emerging"

def clean_text(text): 
    # STRICT SANITIZER: Strips absolutely all non-ASCII characters to prevent PDF crashes
    if text is None: return ""
    return re.sub(r'[^\x00-\x7F]+', ' ', str(text)).strip()

def save_audit_history(company, results):
    os.makedirs("audit_history", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"audit_history/{company}_{timestamp}.json", "w") as f:
        json.dump(results, f)

def top_gaps(results):
    gaps = []
    for phase, info in results["phases"].items():
        for d in info["documents"]:
            if not d["pass"]: gaps.append((phase, d["document"], d["score"]))
    return sorted(gaps, key=lambda x: x[2])[:5]

def generate_pdf(company, results):
    pdf = FPDF()
    pdf.add_page()
    
    # --- HEADER BANNER ---
    pdf.set_fill_color(20, 25, 35)
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_y(15)
    pdf.set_font("Arial", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, clean_text("MINT COMPLIANCE EXECUTIVE BRIEF"), ln=True, align='C')
    
    # --- RESET COLORS & SPACING ---
    pdf.set_text_color(40, 40, 40)
    pdf.set_y(50)
    
    # --- KEY METRICS ---
    pdf.set_font("Arial", "B", 14)
    pdf.cell(100, 10, clean_text(f"Company: {company}"), ln=False)
    pdf.cell(90, 10, clean_text(f"Overall Score: {results['overall_score']}%"), ln=True, align='R')
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(100, 8, clean_text(f"Detected Phase: {results['detected_phase']}"), ln=False)
    pdf.cell(90, 8, clean_text(f"Maturity: {maturity_level(results['overall_score'])}"), ln=True, align='R')
    
    if results['overall_score'] < 70:
        pdf.set_text_color(220, 53, 69) 
    else:
        pdf.set_text_color(40, 167, 69)
    pdf.cell(190, 8, clean_text(f"Risk Classification: {results['risk_level']}"), ln=True, align='R')
    
    pdf.ln(10)
    
    # --- EXECUTIVE SUMMARY ---
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Executive Summary", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, clean_text(results["executive_summary"]))
    pdf.ln(10)
    
    # --- PRIORITY GAPS TABLE ---
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Critical Remediation Targets", ln=True)
    
    pdf.set_fill_color(230, 235, 245)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(40, 8, "Phase", border=1, fill=True)
    pdf.cell(120, 8, "Document", border=1, fill=True)
    pdf.cell(30, 8, "Score", border=1, fill=True, ln=True, align='C')
    
    pdf.set_font("Arial", "", 10)
    gaps = top_gaps(results)
    for g in gaps:
        pdf.cell(40, 8, clean_text(g[0])[:25], border=1)
        pdf.cell(120, 8, clean_text(g[1])[:60], border=1) 
        pdf.cell(30, 8, clean_text(f"{g[2]}%"), border=1, ln=True, align='C')

    file_path = f"{clean_text(company)}_Compliance_Report.pdf"
    pdf.output(file_path)
    return file_path

# =====================================================
# SIDEBAR: SETUP & INGESTION
# =====================================================
with st.sidebar:
    st.title("⚙️ Mission Setup")
    
    company = st.text_input("Target Company")
    project_type = st.selectbox(
        "Engagement Type",
        ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"]
    )
    
    st.divider()
    
    st.subheader("Data Source")
    data_source = st.radio("Extraction Method:", ["☁️ Secure Google Drive", "📁 Local Payload (ZIP)"])
    
    target_zip_for_audit = None
    drive_ready = False
    
    # LOCAL ZIP
    if data_source == "📁 Local Payload (ZIP)":
        uploaded_file = st.file_uploader("Upload ZIP", type="zip")
        if uploaded_file:
            target_zip_for_audit = uploaded_file
            
    # GOOGLE DRIVE
    elif data_source == "☁️ Secure Google Drive":
        if "matching_folders" not in st.session_state: st.session_state.matching_folders = []
        if "has_searched" not in st.session_state: st.session_state.has_searched = False

        search_term = st.text_input("Query Drive Directory")
        if st.button("Search", use_container_width=True):
            if search_term:
                try:
                    drive_service = get_drive_service()
                    if drive_service:
                        with st.spinner("Establishing secure connection..."):
                            results = search_folders_by_name(drive_service, search_term, MAIN_AUDIT_FOLDER_ID)
                            st.session_state.matching_folders = results
                            st.session_state.has_searched = True
                except Exception as e:
                    st.error(f"Connection failed: {e}")

        if st.session_state.has_searched and st.session_state.matching_folders:
            drive_service = get_drive_service()
            main_options = {f"{f['name']}": f for f in st.session_state.matching_folders}
            selected_main = st.selectbox("Select Root Directory:", options=list(main_options.keys()))
            selected_main_folder = main_options[selected_main]
            
            with st.spinner("Mapping subdirectories..."):
                subfolders = get_subfolders(drive_service, selected_main_folder['id'])
            
            target_options = {f"📦 ENTIRE '{selected_main_folder['name']}' Vault": selected_main_folder}
            for sf in subfolders: 
                target_options[f"📁 Node: {sf['name']}"] = sf
                
            selected_target = st.selectbox("Target Node:", options=list(target_options.keys()))
            target_folder = target_options[selected_target]

            if st.button("⬇️ Extract Files", type="primary", use_container_width=True):
                if not company:
                    st.error("Target Company name required.")
                else:
                    try:
                        target_dir = f"downloads/{company}"
                        if os.path.exists(target_dir): shutil.rmtree(target_dir)
                        os.makedirs(target_dir, exist_ok=True)
                        
                        with st.spinner("Extracting payload directly to engine..."):
                            download_folder_recursively(drive_service, target_folder['id'], target_dir)
                        
                        st.success("Extraction complete. Ready for analysis.")
                        drive_ready = True
                    except Exception as e:
                        st.error(f"Extraction failed: {e}")

    st.divider()
    
    # EXECUTION BUTTON
    if st.button("🚀 INITIATE AUDIT", type="primary", use_container_width=True):
        if not company:
            st.error("Provide a Target Company.")
        elif data_source == "📁 Local Payload (ZIP)" and not target_zip_for_audit:
            st.error("Upload a ZIP payload.")
        elif data_source == "☁️ Secure Google Drive" and not drive_ready and not os.path.exists(f"downloads/{company}"):
            st.error("Extract files from Drive first.")
        else:
            with st.spinner("MINT Intelligence Engine processing..."):
                if target_zip_for_audit:
                    extract_zip(target_zip_for_audit, company)
                    
                results = run_pipeline(company, project_type)
                save_audit_history(company, results)
                
                st.session_state.audit_results = results
                st.session_state.audit_company = company


# =====================================================
# MAIN DASHBOARD AREA
# =====================================================

if st.session_state.audit_results is None:
    st.title("MINT Command Center")
    st.info("👈 Configure mission parameters in the sidebar to initiate.")
else:
    results = st.session_state.audit_results
    comp = st.session_state.audit_company
    
    overall = results["overall_score"]
    maturity = maturity_level(overall)
    
    total_docs = sum(len(p["documents"]) for p in results["phases"].values())
    passed_docs = sum(1 for p in results["phases"].values() for d in p["documents"] if d["pass"])
    pass_rate = round(passed_docs/total_docs*100,1) if total_docs > 0 else 0

    st.markdown(f"<h1 style='color: white; margin-bottom: 0px;'>Intelligence Brief: {comp}</h1>", unsafe_allow_html=True)
    st.caption(f"DETECTED PHASE: {results['detected_phase'].upper()}")

    # --- ROW 1: EXECUTIVE GAUGES ---
    st.markdown('<h3 class="section-header">Executive Health Overview</h3>', unsafe_allow_html=True)
    col_g1, col_g2, col_g3 = st.columns(3)
    
    with col_g1:
        fig1 = go.Figure(go.Indicator(
            mode = "gauge+number", value = overall, title = {'text': "Overall Compliance", 'font': {'color': 'white'}},
            number = {'font': {'color': 'white'}},
            gauge = {
                'axis': {'range': [0, 100], 'tickcolor': "white"},
                'bar': {'color': "#00E676" if overall >= 70 else "#FF3D00"},
                'bgcolor': "#1E1E1E",
                'steps': [
                    {'range': [0, 50], 'color': "rgba(255, 61, 0, 0.2)"},
                    {'range': [50, 70], 'color': "rgba(255, 214, 0, 0.2)"},
                    {'range': [70, 100], 'color': "rgba(0, 230, 118, 0.2)"}
                ]
            }
        ))
        fig1.update_layout(height=250, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor='rgba(0,0,0,0)', font={'color': 'white'})
        st.plotly_chart(fig1, use_container_width=True)

    with col_g2:
        fig2 = go.Figure(go.Indicator(
            mode = "number", value = pass_rate, number = {'suffix': "%", 'font': {'color': 'white'}},
            title = {'text': "Document Pass Rate", 'font': {'color': 'white'}},
            domain = {'x': [0, 1], 'y': [0, 1]}
        ))
        fig2.update_layout(height=250, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig2, use_container_width=True)
        
    with col_g3:
        st.markdown(f"""
        <div style="background-color: #1A1A1A; padding: 30px; border-radius: 10px; border-left: 5px solid {'#FF3D00' if overall < 70 else '#00E676'}; height: 100%; text-align: center;">
            <h4 style="color: #888; margin-bottom: 5px; text-transform: uppercase;">Risk Level</h4>
            <h2 style="color: {'#FF3D00' if overall < 70 else '#00E676'}; margin-top: 0;">{results['risk_level']}</h2>
            <hr style="border-color: #333;">
            <h4 style="color: #888; margin-bottom: 5px; text-transform: uppercase;">Maturity</h4>
            <h3 style="color: white; margin-top: 0;">{maturity}</h3>
        </div>
        """, unsafe_allow_html=True)

    # --- ROW 2: RADAR & GAPS ---
    st.markdown('<h3 class="section-header">Vulnerability & Phase Balance</h3>', unsafe_allow_html=True)
    col_rad, col_gaps = st.columns([1, 1])

    with col_rad:
        phase_names, phase_scores = [], []
        for phase, info in results["phases"].items():
            phase_names.append(phase)
            phase_scores.append(info["score"])

        radar = go.Figure()
        radar.add_trace(go.Scatterpolar(
            r=phase_scores + [phase_scores[0]] if phase_scores else [],
            theta=phase_names + [phase_names[0]] if phase_names else [],
            fill='toself', line=dict(color='#00E676', width=2), fillcolor='rgba(0, 230, 118, 0.2)'
        ))
        radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], gridcolor='#333', linecolor='#333'),
                angularaxis=dict(gridcolor='#333', linecolor='#333'),
                bgcolor='#0E1117'
            ), 
            margin=dict(l=40, r=40, t=20, b=20),
            height=350,
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        st.plotly_chart(radar, use_container_width=True)

    with col_gaps:
        gaps = top_gaps(results)
        if not gaps:
            st.success("Operational integrity verified. No major gaps found. 🎉")
        else:
            st.error("🚨 PRIORITY REMEDIATION TARGETS")
            for phase, doc, score in gaps:
                with st.expander(f"{phase}: {doc} (Score: {score}%)"):
                    ai_comment = "No specific diagnostic."
                    for d in results["phases"][phase]["documents"]:
                        if d["document"] == doc:
                            ai_comment = d.get("comment", ai_comment)
                            break
                    st.write(f"**Diagnostic Notes:** {ai_comment}")

    # --- ROW 3: MASTER LEDGER ---
    st.markdown('<h3 class="section-header">Compliance Master Ledger</h3>', unsafe_allow_html=True)
    
    # Prepare neat dataframe for the visual table
    table_data = []
    for phase, info in results["phases"].items():
        for d in info["documents"]:
            table_data.append({
                "Phase": phase,
                "Document Requirement": d["document"],
                "Score": d["score"],
                "Status": "🟢 PASS" if d["pass"] else "🔴 FAIL"
            })
    
    df_ledger = pd.DataFrame(table_data)
    
    # Render highly professional interactive dataframe with progress bars
    st.dataframe(
        df_ledger,
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Health Score",
                help="AI assigned completeness score",
                format="%f%%",
                min_value=0,
                max_value=100,
            ),
            "Status": st.column_config.TextColumn("Status")
        },
        use_container_width=True,
        hide_index=True,
        height=350
    )

    # --- ROW 4: ARTIFACTS ---
    st.markdown('<h3 class="section-header">Export Artifacts</h3>', unsafe_allow_html=True)
    dl_col1, dl_col2 = st.columns(2)

    with dl_col1:
        pdf_path = generate_pdf(comp, results)
        with open(pdf_path, "rb") as f:
            st.download_button("📄 Download Professional Executive Brief", f, file_name=pdf_path, mime="application/pdf", use_container_width=True)

    with dl_col2:
        # Full CSV export data
        csv_data = []
        for phase, info in results["phases"].items():
            for d in info["documents"]:
                csv_data.append({"Phase": phase, "Document": d["document"], "Status": "Pass" if d["pass"] else "Fail", "Score": d["score"], "AI Notes": d.get("comment", "")})
        csv_bytes = pd.DataFrame(csv_data).to_csv(index=False).encode('utf-8')
        st.download_button("📊 Download Complete Ledger (CSV)", data=csv_bytes, file_name=f"{clean_text(comp)}_Audit_Ledger.csv", mime="text/csv", use_container_width=True)