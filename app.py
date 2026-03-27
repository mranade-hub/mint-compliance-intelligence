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
from drive_utils import get_drive_service, search_folders_by_name, get_subfolders, download_folder_recursively
from logger_utils import append_log

st.set_page_config(layout="wide", page_title="MINT Command Center", initial_sidebar_state="expanded")

MAIN_AUDIT_FOLDER_ID = "0BxOKDhjJWW08dk5lTXQ1M09XaVk" 
BENCHMARK_SCORE = 68

if "audit_results" not in st.session_state: st.session_state.audit_results = None
if "audit_company" not in st.session_state: st.session_state.audit_company = None

st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #121212; color: white; }
.section-header { border-bottom: 1px solid #333; padding-bottom: 10px; margin-top: 40px; margin-bottom: 20px; color: #F8F9FA; font-weight: 300; }
.stApp { background-color: #0E1117; color: #C9D1D9; }
</style>
""", unsafe_allow_html=True)

def maturity_level(score):
    if score >= 85: return "Optimized"
    elif score >= 70: return "Managed"
    elif score >= 50: return "Developing"
    else: return "Emerging"

def clean_text(text): 
    if text is None: return ""
    return re.sub(r'[^\x00-\x7F]+', ' ', str(text)).strip()

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
    return sorted(history, key=lambda x: x["timestamp"], reverse=True)

def top_gaps(results):
    gaps = []
    for phase, info in results["phases"].items():
        for d in info["documents"]:
            if not d["pass"] or d.get("wrong_folder"): 
                gaps.append((phase, d["document"], d["score"], d.get("wrong_folder", False), d.get("actual_folder", "N/A")))
    return sorted(gaps, key=lambda x: x[2])[:5]

class ExecutivePDF(FPDF):
    def __init__(self, company):
        super().__init__()
        self.company = clean_text(company)
        self.timestamp = datetime.datetime.now().strftime("%B %d, %Y - %H:%M")

    def header(self):
        self.set_fill_color(15, 23, 42) 
        self.rect(0, 0, 210, 40, 'F')
        if os.path.exists("logo.png"):
            try: self.image("logo.png", x=10, y=8, w=25)
            except: pass 
        self.set_y(15)
        self.set_font("Arial", "B", 18)
        self.set_text_color(248, 250, 252) 
        self.cell(0, 10, "COMPLIANCE EXECUTIVE BRIEF", ln=True, align='C')
        self.set_y(45)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(148, 163, 184) 
        self.cell(0, 10, f"Generated for {self.company} on {self.timestamp} | Page {self.page_no()}", align='C')

def generate_pdf(company, results):
    pdf = ExecutivePDF(company)
    pdf.add_page()
    
    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(100, 10, f"Target Entity: {pdf.company}", ln=False)
    pdf.cell(90, 10, f"Overall Score: {results['overall_score']}%", ln=True, align='R')
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(100, 8, f"Detected Phase: {clean_text(results['detected_phase'])}", ln=False)
    pdf.cell(90, 8, f"Maturity: {maturity_level(results['overall_score'])}", ln=True, align='R')
    
    pdf.set_text_color(220, 38, 38) if results['overall_score'] < 70 else pdf.set_text_color(22, 163, 74) 
    pdf.cell(190, 8, f"Risk Classification: {clean_text(results['risk_level'])}", ln=True, align='R')
    
    pdf.ln(8)
    pdf.set_draw_color(226, 232, 240)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)
    
    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Diagnostic Summary", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.set_text_color(71, 85, 105) 
    pdf.multi_cell(0, 6, clean_text(results["executive_summary"]))
    pdf.ln(10)
    
    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Phase Performance", ln=True)
    
    pdf.set_fill_color(241, 245, 249) 
    pdf.set_font("Arial", "B", 10)
    pdf.cell(140, 8, "Project Phase", border=1, fill=True)
    pdf.cell(50, 8, "Compliance Score", border=1, fill=True, ln=True, align='C')
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(71, 85, 105)
    for phase, info in results["phases"].items():
        pdf.cell(140, 8, clean_text(phase), border=1)
        pdf.cell(50, 8, f"{info['score']}%", border=1, ln=True, align='C')
    
    pdf.ln(10)

    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Priority Remediation Targets", ln=True)
    
    pdf.set_fill_color(254, 226, 226) 
    pdf.set_text_color(153, 27, 27) 
    pdf.set_font("Arial", "B", 10)
    pdf.cell(40, 8, "Phase", border=1, fill=True)
    pdf.cell(120, 8, "Document Requirement", border=1, fill=True)
    pdf.cell(30, 8, "Score", border=1, fill=True, ln=True, align='C')
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(71, 85, 105)
    gaps = top_gaps(results)
    if not gaps:
        pdf.cell(190, 8, "No critical gaps identified.", border=1, ln=True, align='C')
    else:
        for g in gaps:
            pdf.cell(40, 8, clean_text(g[0])[:25], border=1)
            pdf.cell(120, 8, clean_text(g[1])[:60], border=1) 
            pdf.cell(30, 8, f"{g[2]}%", border=1, ln=True, align='C')

    file_path = f"{clean_text(company)}_Compliance_Report.pdf"
    pdf.output(file_path)
    return file_path


with st.sidebar:
    st.image("logo.png", width=140)
    st.title("MINT Setup")
    
    company = st.text_input("Target Company")
    project_type = st.selectbox("Engagement Type", ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"])
    st.divider()
    
    st.subheader("Data Extraction")
    data_source = st.radio("Method:", ["☁️ Google Drive", "📁 Local ZIP Upload", "🗄️ Load Previous Audit"])
    
    target_zip_for_audit, drive_ready = None, False
    
    if data_source == "🗄️ Load Previous Audit":
        if not company: st.info("Enter a Target Company to load history.")
        else:
            history = load_company_history(company)
            if not history: st.warning("No previous audits found.")
            else:
                options = {f"Audit: {h['timestamp']} (Score: {h['overall_score']}%)": h for h in history}
                if st.button("🔄 LOAD DASHBOARD", type="primary", use_container_width=True):
                    st.session_state.audit_results = options[st.selectbox("Select Audit:", list(options.keys()))]
                    st.session_state.audit_company = company
                    st.rerun()

    elif data_source == "📁 Local ZIP Upload":
        uploaded_file = st.file_uploader("Upload Payload", type="zip")
        if uploaded_file: target_zip_for_audit = uploaded_file
            
    elif data_source == "☁️ Google Drive":
        if "matching_folders" not in st.session_state: st.session_state.matching_folders = []
        if "has_searched" not in st.session_state: st.session_state.has_searched = False

        search_term = st.text_input("Query Drive")
        if st.button("Search", use_container_width=True):
            if search_term:
                try:
                    drive_service = get_drive_service()
                    if drive_service:
                        with st.spinner("Connecting..."):
                            st.session_state.matching_folders = search_folders_by_name(drive_service, search_term, MAIN_AUDIT_FOLDER_ID)
                            st.session_state.has_searched = True
                except Exception as e: st.error(f"Failed: {e}")

        if st.session_state.has_searched and st.session_state.matching_folders:
            drive_service = get_drive_service()
            main_options = {f"{f['name']}": f for f in st.session_state.matching_folders}
            selected_main_folder = main_options[st.selectbox("Root:", list(main_options.keys()))]
            
            with st.spinner("Mapping..."):
                subfolders = get_subfolders(drive_service, selected_main_folder['id'])
            
            target_options = {f"📦 ENTIRE Vault": selected_main_folder}
            for sf in subfolders: target_options[f"📁 {sf['name']}"] = sf
                
            target_folder = target_options[st.selectbox("Target:", list(target_options.keys()))]

            if st.button("⬇️ Extract Files", use_container_width=True):
                if company:
                    try:
                        target_dir = f"downloads/{company}"
                        if os.path.exists(target_dir): shutil.rmtree(target_dir)
                        os.makedirs(target_dir, exist_ok=True)
                        with st.spinner("Extracting..."):
                            download_folder_recursively(drive_service, target_folder['id'], target_dir)
                        st.success("Ready.")
                        drive_ready = True
                    except Exception as e: st.error(f"Failed: {e}")

    if data_source != "🗄️ Load Previous Audit":
        st.divider()
        if st.button("🚀 INITIATE AUDIT", type="primary", use_container_width=True):
            if not company: st.error("Target Company required.")
            elif data_source == "📁 Local ZIP Upload" and not target_zip_for_audit: st.error("Upload ZIP.")
            elif data_source == "☁️ Google Drive" and not drive_ready and not os.path.exists(f"downloads/{company}"): st.error("Extract files first.")
            else:
                with st.status("🚀 Intelligence Engine Active...", expanded=True) as status_box:
                    progress_bar = st.progress(0, text="Initializing...")
                    
                    def file_logger(msg):
                        append_log(company, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")
                        
                    def ui_progress(current, total, message="Processing"):
                        progress_bar.progress(current / total if total > 0 else 0, text=f"**{message}** ({int((current/total)*100 if total>0 else 0)}%)")

                    if target_zip_for_audit:
                        file_logger("[SYSTEM] Unzipping payload...")
                        extract_zip(target_zip_for_audit, company)
                        
                    results = run_pipeline(company, project_type, log_callback=file_logger, progress_callback=ui_progress)
                    save_audit_history(company, results)
                    status_box.update(label="✅ Complete!", state="complete", expanded=False)
                    
                st.session_state.audit_results = results
                st.session_state.audit_company = company
                st.rerun() 


if st.session_state.audit_results is None:
    st.title("MINT Intelligence Dashboard")
    st.info("👈 Please configure mission parameters in the sidebar to initiate analysis.")
else:
    results = st.session_state.audit_results
    comp = st.session_state.audit_company
    
    overall = results["overall_score"]
    maturity = maturity_level(overall)
    
    total_docs = sum(len(p["documents"]) for p in results["phases"].values())
    passed_docs = sum(1 for p in results["phases"].values() for d in p["documents"] if d["pass"])
    pass_rate = round(passed_docs/total_docs*100,1) if total_docs > 0 else 0

    st.title(f"Intelligence Brief: {comp}")
    st.caption(f"DETECTED PROJECT PHASE: **{results['detected_phase'].upper()}**")

    st.divider()
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric(label="Overall Compliance", value=f"{overall}%", delta=f"{overall - BENCHMARK_SCORE}% vs Benchmark")
    col_m2.metric(label="Document Pass Rate", value=f"{pass_rate}%")
    col_m3.metric(label="Maturity Level", value=maturity)
    col_m4.metric(label="Risk Assessment", value=results['risk_level'], delta="Critical Attention" if overall < 70 else "Healthy", delta_color="inverse")
    st.divider()

    col_left, col_right = st.columns(2)
    with col_left:
        with st.container(border=True):
            st.subheader("Performance Balance")
            phase_names, phase_scores = [], []
            for phase, info in results["phases"].items():
                phase_names.append(phase)
                phase_scores.append(info["score"])

            radar = go.Figure()
            radar.add_trace(go.Scatterpolar(
                r=phase_scores + [phase_scores[0]] if phase_scores else [],
                theta=phase_names + [phase_names[0]] if phase_names else [],
                fill='toself', line=dict(color='#3b82f6', width=2), fillcolor='rgba(59, 130, 246, 0.2)'
            ))
            radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), margin=dict(l=40, r=40, t=20, b=20), height=320)
            st.plotly_chart(radar, use_container_width=True)

    with col_right:
        with st.container(border=True):
            st.subheader("Priority Remediation Targets")
            gaps = top_gaps(results)
            if not gaps:
                st.success("Operational integrity verified. No critical gaps found. 🎉")
            else:
                for phase, doc, score, wrong_folder, actual_folder in gaps:
                    icon = "📁" if wrong_folder else "⚠️"
                    with st.expander(f"{icon} {doc} (Score: {score}%)"):
                        st.write(f"**Target Phase:** {phase}")
                        if wrong_folder:
                            st.error(f"Found in wrong location: `{actual_folder}`")
                        ai_comment = "No specific diagnostic."
                        for d in results["phases"][phase]["documents"]:
                            if d["document"] == doc:
                                ai_comment = d.get("comment", ai_comment)
                                break
                        st.caption(f"**AI Notes:** {ai_comment}")

    with st.container(border=True):
        st.subheader("Compliance Master Ledger")
        
        table_data = []
        for phase, info in results["phases"].items():
            for d in info["documents"]:
                if not d.get("actual_folder") or d.get("actual_folder") == "N/A": loc_status = "⚠️ Missing"
                elif d.get("wrong_folder"): loc_status = f"🚫 Wrong Folder ({d.get('actual_folder')})"
                else: loc_status = "✅ Correct"

                table_data.append({
                    "Phase": phase,
                    "Document Requirement": d["document"],
                    "Score": d["score"],
                    "Status": "✅ Pass" if d["pass"] else "❌ Fail",
                    "Location": loc_status
                })
        
        df_ledger = pd.DataFrame(table_data)
        st.dataframe(
            df_ledger,
            column_config={"Score": st.column_config.ProgressColumn("Health Score", format="%f%%", min_value=0, max_value=100)},
            use_container_width=True, hide_index=True, height=300
        )

    st.subheader("Export Artifacts")
    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        pdf_path = generate_pdf(comp, results)
        with open(pdf_path, "rb") as f:
            st.download_button("📄 Download Executive PDF", f, file_name=pdf_path, mime="application/pdf", use_container_width=True, type="primary")

    with dl_col2:
        csv_bytes = df_ledger.to_csv(index=False).encode('utf-8')
        st.download_button("📊 Download Ledger CSV", data=csv_bytes, file_name=f"{clean_text(comp)}_Audit_Ledger.csv", mime="text/csv", use_container_width=True)