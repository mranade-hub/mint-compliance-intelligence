import sys
import os
import json
import datetime
import asyncio
import re
import shutil
import zipfile

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from fpdf import FPDF

from pipeline import run_pipeline
from drive_utils import get_drive_service, search_folders_by_name, get_subfolders, download_folder_recursively
from logger_utils import append_log

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="MINT - Compliance Intelligence",
    page_icon="◈",
    initial_sidebar_state="expanded"
)

MAIN_AUDIT_FOLDER_ID = "0BxOKDhjJWW08dk5lTXQ1M09XaVk"

# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────
for key, default in [
    ("audit_results", None),
    ("audit_company", None),
    ("matching_folders", []),
    ("has_searched", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─────────────────────────────────────────────
#  GLOBAL CSS
# ─────────────────────────────────────────────
st.markdown('<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">', unsafe_allow_html=True)

custom_css = """
/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp {
    background-color: #080C14 !important;
    color: #CBD5E1 !important;
    font-family: 'Sora', sans-serif !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0C1221 0%, #080C14 100%) !important;
    border-right: 1px solid rgba(99,179,237,0.08) !important;
}
[data-testid="stSidebar"] * { font-family: 'Sora', sans-serif !important; }
[data-testid="stSidebar"] .stTextInput > div > div > input,
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stFileUploader > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(99,179,237,0.15) !important;
    border-radius: 6px !important;
    color: #E2E8F0 !important;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stRadio label {
    color: #94A3B8 !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] .stRadio > div { gap: 6px !important; }
[data-testid="stSidebar"] .stRadio > div > label {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(99,179,237,0.1) !important;
    border-radius: 6px !important;
    padding: 8px 12px !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
    font-size: 0.85rem !important;
    color: #CBD5E1 !important;
    transition: all 0.2s ease !important;
}
[data-testid="stSidebar"] .stRadio > div > label:hover {
    border-color: rgba(99,179,237,0.35) !important;
    background: rgba(99,179,237,0.06) !important;
}

/* ── Primary Button ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1D4ED8 0%, #2563EB 100%) !important;
    border: none !important;
    border-radius: 6px !important;
    color: #fff !important;
    font-family: 'Sora', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    padding: 10px 20px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 0 20px rgba(37,99,235,0.25) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 0 30px rgba(37,99,235,0.45) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(99,179,237,0.2) !important;
    border-radius: 6px !important;
    color: #94A3B8 !important;
    font-family: 'Sora', sans-serif !important;
    font-size: 0.82rem !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: rgba(99,179,237,0.45) !important;
    color: #E2E8F0 !important;
}

/* ── Download Button ── */
[data-testid="stDownloadButton"] > button {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(99,179,237,0.2) !important;
    border-radius: 6px !important;
    color: #94A3B8 !important;
    font-family: 'Sora', sans-serif !important;
    font-size: 0.82rem !important;
    width: 100% !important;
    transition: all 0.2s ease !important;
}
[data-testid="stDownloadButton"] > button:hover {
    border-color: rgba(99,179,237,0.45) !important;
    color: #E2E8F0 !important;
    background: rgba(99,179,237,0.06) !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.025) !important;
    border: 1px solid rgba(99,179,237,0.1) !important;
    border-radius: 10px !important;
    padding: 20px 24px !important;
}
[data-testid="stMetricLabel"] {
    color: #64748B !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}
[data-testid="stMetricValue"] {
    color: #F1F5F9 !important;
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    font-family: 'Sora', sans-serif !important;
}
[data-testid="stMetricDelta"] { font-size: 0.78rem !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(99,179,237,0.1) !important;
    border-radius: 8px !important;
    margin-bottom: 6px !important;
}
[data-testid="stExpander"] summary {
    color: #CBD5E1 !important;
    font-size: 0.85rem !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(99,179,237,0.1) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}

/* ── Divider ── */
hr { border-color: rgba(99,179,237,0.08) !important; }

/* ── Progress bar ── */
[data-testid="stProgress"] > div > div {
    background: linear-gradient(90deg, #1D4ED8, #38BDF8) !important;
}

/* ── Status box ── */
[data-testid="stStatus"] {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(99,179,237,0.12) !important;
    border-radius: 10px !important;
}

/* ── Plotly chart background ── */
.js-plotly-plot, .plotly { background: transparent !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(99,179,237,0.2); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(99,179,237,0.4); }

/* ── Custom card classes ── */
.mint-card {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(99,179,237,0.1);
    border-radius: 12px;
    padding: 28px 32px;
    margin-bottom: 16px;
}
.mint-section-label {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #3B82F6;
    margin-bottom: 8px;
}
.mint-section-title {
    font-size: 1.15rem;
    font-weight: 600;
    color: #F1F5F9;
    margin-bottom: 0;
}
.mint-hero-score {
    font-size: 4rem;
    font-weight: 700;
    color: #F1F5F9;
    line-height: 1;
    font-family: 'Sora', sans-serif;
}
.mint-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.badge-pass   { background: rgba(34,197,94,0.12);  color: #4ADE80; border: 1px solid rgba(34,197,94,0.25); }
.badge-fail   { background: rgba(239,68,68,0.12);  color: #F87171; border: 1px solid rgba(239,68,68,0.25); }
.badge-warn   { background: rgba(234,179,8,0.12);  color: #FACC15; border: 1px solid rgba(234,179,8,0.25); }
.badge-miss   { background: rgba(100,116,139,0.15); color: #94A3B8; border: 1px solid rgba(100,116,139,0.25); }

.phase-node {
    text-align: center;
    padding: 14px 10px;
    border-radius: 10px;
    border: 1px solid rgba(99,179,237,0.15);
    background: rgba(255,255,255,0.025);
    position: relative;
}
.phase-node-label {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #64748B;
    margin-bottom: 6px;
}
.phase-node-score {
    font-size: 1.4rem;
    font-weight: 700;
    font-family: 'Sora', sans-serif;
}
.phase-active { border-color: rgba(59,130,246,0.45) !important; background: rgba(59,130,246,0.06) !important; }

.gap-item {
    padding: 14px 18px;
    border-radius: 8px;
    border-left: 3px solid;
    background: rgba(255,255,255,0.02);
    margin-bottom: 8px;
}
.gap-critical { border-left-color: #EF4444; }
.gap-warning  { border-left-color: #F59E0B; }

.sidebar-logo {
    font-size: 1.3rem;
    font-weight: 700;
    color: #F1F5F9;
    letter-spacing: -0.02em;
    font-family: 'Sora', sans-serif;
}
.sidebar-logo span { color: #3B82F6; }

.export-card {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(99,179,237,0.1);
    border-radius: 10px;
    padding: 20px 24px;
}
.export-card-title {
    font-size: 0.82rem;
    font-weight: 600;
    color: #F1F5F9;
    margin-bottom: 4px;
}
.export-card-desc {
    font-size: 0.75rem;
    color: #64748B;
    margin-bottom: 14px;
}
"""

st.markdown(f'<style>{custom_css}</style>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def maturity_level(score):
    if score >= 85:   return "Optimized"
    elif score >= 70: return "Managed"
    elif score >= 50: return "Developing"
    else:             return "Emerging"

def risk_color(score):
    if score >= 85:   return "#4ADE80"
    elif score >= 70: return "#FACC15"
    elif score >= 50: return "#FB923C"
    else:             return "#F87171"

def score_color(score):
    if score >= 85:   return "#4ADE80"
    elif score >= 70: return "#A3E635"
    elif score >= 50: return "#FB923C"
    else:             return "#F87171"

def clean_text(text):
    if text is None: return ""
    return re.sub(r'[^\x00-\x7F]+', ' ', str(text)).strip()

def save_audit_history(company, results):
    os.makedirs("audit_history", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results["audit_timestamp"] = timestamp
    with open(f"audit_history/{company}_{timestamp}.json", "w") as f:
        json.dump(results, f)

def load_company_history(company):
    if not os.path.exists("audit_history"): return []
    history = []
    for file in os.listdir("audit_history"):
        if file.startswith(company) and file.endswith(".json"):
            try:
                with open(os.path.join("audit_history", file)) as f:
                    data = json.load(f)
                if "audit_timestamp" not in data:
                    data["audit_timestamp"] = file.replace(f"{company}_", "").replace(".json", "")
                history.append(data)
            except Exception:
                continue
    return sorted(history, key=lambda x: x.get("audit_timestamp", ""), reverse=True)

def top_gaps(results):
    gaps = []
    for phase, info in results.get("phases", {}).items():
        for d in info.get("documents", []):
            if not d.get("pass") and "N/A" not in d.get("comment", ""):
                gaps.append((phase, d["document"], d.get("score", 0), False, d.get("actual_folder", "N/A")))
            elif d.get("wrong_folder"):
                gaps.append((phase, d["document"], d.get("score", 0), True, d.get("actual_folder", "N/A")))
    return sorted(gaps, key=lambda x: x[2])[:6]


# ─────────────────────────────────────────────
#  PDF GENERATION
# ─────────────────────────────────────────────
class ExecutivePDF(FPDF):
    def __init__(self, company, category_name="MINT"):
        super().__init__()
        self.company = clean_text(company)
        self.category_name = category_name
        self.timestamp = datetime.datetime.now().strftime("%B %d, %Y - %H:%M")
        self.set_margins(15, 15, 15)
        self.is_cover = True  

    def header(self):
        if self.is_cover: return
        
        self.set_fill_color(8, 12, 20)
        self.rect(0, 0, 210, 35, 'F')
        self.set_draw_color(37, 99, 235)
        self.set_line_width(1)
        self.line(0, 35, 210, 35)
        
        self.set_y(12)
        self.set_font("Arial", "B", 16)
        self.set_text_color(241, 245, 249)
        self.cell(0, 8, "COMPLIANCE INTELLIGENCE BRIEF", ln=True, align='L')
        self.set_font("Arial", "", 9)
        self.set_text_color(148, 163, 184)
        self.cell(0, 5, f"Automated {self.category_name} Adherence Report for {self.company}", ln=True, align='L')
        self.set_y(42)

    def footer(self):
        if self.is_cover: return
        
        self.set_y(-20)
        self.set_font("Arial", "I", 8)
        self.set_text_color(148, 163, 184)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.2)
        self.line(15, self.get_y() - 2, 195, self.get_y() - 2)
        self.cell(0, 8, f"Confidential  |  {self.timestamp}  |  Page {self.page_no()}", align='C')

def draw_kpi_card(pdf, x, y, w, h, label, value, val_color=(15, 23, 42)):
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(x, y, w, h, 'DF')
    
    pdf.set_xy(x, y + 4)
    pdf.set_font("Arial", "B", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(w, 4, label, align='C')
    
    pdf.set_xy(x, y + 10)
    pdf.set_font("Arial", "B", 15)
    pdf.set_text_color(*val_color)
    pdf.cell(w, 8, value, align='C')

def draw_table_row(pdf, data, widths, line_height=6, fill_color=None, text_colors=None, is_header=False):
    max_lines = 1
    for i, text in enumerate(data):
        eff_width = widths[i] - 4
        words = clean_text(str(text)).split()
        line_count, curr_w = 1, 0
        for w in words:
            w_len = pdf.get_string_width(w + " ")
            if curr_w + w_len > eff_width:
                line_count += 1
                curr_w = w_len
            else:
                curr_w += w_len
        if line_count > max_lines: max_lines = line_count
            
    row_h = (max_lines * line_height) + 4
    if pdf.get_y() + row_h > 275: pdf.add_page()
        
    x, y = pdf.get_x(), pdf.get_y()
    pdf.set_draw_color(226, 232, 240)
    pdf.set_line_width(0.2)
    
    for i in range(len(data)):
        if fill_color:
            pdf.set_fill_color(*fill_color)
            pdf.rect(x, y, widths[i], row_h, 'DF')
        else:
            pdf.rect(x, y, widths[i], row_h, 'D')
        x += widths[i]
        
    x = 15
    for i, text in enumerate(data):
        if is_header:
            pdf.set_text_color(15, 23, 42)
            pdf.set_font("Arial", "B", 9)
        elif text_colors and i in text_colors:
            pdf.set_text_color(*text_colors[i])
            pdf.set_font("Arial", "B", 9)
        else:
            pdf.set_text_color(71, 85, 105)
            pdf.set_font("Arial", "", 9)
            
        pdf.set_xy(x + 2, y + 2)
        pdf.multi_cell(widths[i] - 4, line_height, clean_text(str(text)), border=0, align='L')
        x += widths[i]
        
    pdf.set_xy(15, y + row_h)

def generate_pdf(company, results):
    cat_name = results.get("project_category", "MINT")
    pdf = ExecutivePDF(company, cat_name)
    
    # --- 1. COVER PAGE ---
    pdf.add_page()
    pdf.set_fill_color(8, 12, 20)
    pdf.rect(0, 0, 210, 297, 'F') 
    
    current_y = 80
    my_logo_path = "logo.png" 
    
    if os.path.exists(my_logo_path):
        try:
            pdf.image(my_logo_path, x=85, y=35, w=40)
            current_y = 95 
        except Exception:
            pass 

    pdf.set_y(current_y)
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(59, 130, 246)
    pdf.cell(0, 10, "M I N T", align='C', ln=True)
    
    pdf.set_font("Arial", "B", 26)
    pdf.set_text_color(241, 245, 249)
    pdf.cell(0, 14, f"Executive Adherence Report ({cat_name})", align='C', ln=True)
    
    pdf.set_fill_color(37, 99, 235)
    pdf.rect(85, pdf.get_y() + 4, 40, 2, 'F') 
    
    pdf.set_y(pdf.get_y() + 18)
    pdf.set_font("Arial", "", 11)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 6, "PREPARED FOR:", align='C', ln=True)
    
    pdf.set_font("Arial", "B", 24)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 12, f"{pdf.company}", align='C', ln=True)
    
    pdf.set_y(260)
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 5, f"Generated: {pdf.timestamp}", align='C', ln=True)
    pdf.cell(0, 5, "CONFIDENTIAL", align='C', ln=True)
    
    # --- 2. MAIN CONTENT PAGE ---
    pdf.is_cover = False
    pdf.add_page()

    total_docs = sum(len(p.get("documents", [])) for p in results.get("phases", {}).values())
    passed_docs = sum(1 for p in results.get("phases", {}).values() for d in p.get("documents", []) if d.get("pass"))
    pass_rate = f"{round(passed_docs / total_docs * 100, 1)}%" if total_docs > 0 else "0%"
    overall = results.get("overall_score", 0)
    
    rc = (239, 68, 68) if overall < 70 else (34, 197, 94)
    
    card_y = pdf.get_y()
    draw_kpi_card(pdf, 15, card_y, 42, 22, "ADHERENCE", f"{overall}%", val_color=rc)
    draw_kpi_card(pdf, 61, card_y, 42, 22, "PASS RATE", pass_rate)
    draw_kpi_card(pdf, 107, card_y, 42, 22, "MATURITY", maturity_level(overall))
    draw_kpi_card(pdf, 153, card_y, 42, 22, "RISK LEVEL", clean_text(results.get("risk_level", "Unknown")), val_color=rc)
    
    pdf.set_y(card_y + 30)

    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Executive Summary", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(71, 85, 105)
    pdf.multi_cell(0, 6, clean_text(results.get("executive_summary", "No summary provided.")))
    pdf.ln(6)

    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Phase Performance Pipeline", ln=True)
    pdf.ln(2)
    
    y_start = pdf.get_y()
    for phase, info in results.get("phases", {}).items():
        score = info.get("score", 0)
        
        pdf.set_text_color(71, 85, 105)
        pdf.set_xy(15, y_start)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(45, 5, clean_text(phase))
        
        pdf.set_fill_color(226, 232, 240)
        pdf.rect(65, y_start + 1.5, 100, 3, 'F')
        
        if   score >= 85: pdf.set_fill_color(34, 197, 94)
        elif score >= 70: pdf.set_fill_color(163, 230, 53)
        elif score >= 50: pdf.set_fill_color(249, 115, 22)
        else:             pdf.set_fill_color(239, 68, 68)
        
        if score > 0:
            pdf.rect(65, y_start + 1.5, max(1, score), 3, 'F')
            
        pdf.set_text_color(15, 23, 42)
        pdf.set_font("Arial", "B", 8)
        pdf.set_xy(170, y_start)
        pdf.cell(20, 5, f"{score}%")
        
        y_start += 7
    pdf.set_y(y_start + 8)

    # --- 3. PRIORITY GAP REGISTER ---
    gaps = top_gaps(results)
    if gaps:
        pdf.set_text_color(15, 23, 42)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Priority Action Register (Top Gaps)", ln=True)
        pdf.ln(2)
        
        for phase, doc, score, wrong_folder, actual_folder in gaps:
            gap_y = pdf.get_y()
            if gap_y > 260:
                pdf.add_page()
                gap_y = pdf.get_y()
                
            pdf.set_fill_color(250, 250, 250)
            pdf.rect(15, gap_y, 180, 16, 'F')
            
            if wrong_folder: pdf.set_fill_color(245, 158, 11) 
            else:            pdf.set_fill_color(239, 68, 68)  
            pdf.rect(15, gap_y, 2, 16, 'F')
            
            pdf.set_xy(20, gap_y + 2)
            pdf.set_font("Arial", "B", 9)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(140, 5, clean_text(doc))
            
            pdf.set_xy(160, gap_y + 2)
            pdf.set_font("Arial", "B", 8)
            tag_text = "MISPLACED" if wrong_folder else "MISSING"
            pdf.cell(30, 5, tag_text, align='R')
            
            pdf.set_xy(20, gap_y + 8)
            pdf.set_font("Arial", "", 8)
            pdf.set_text_color(100, 116, 139)
            subtext = f"Phase: {phase}  |  Current Score: {score}%"
            if wrong_folder: subtext += f"  |  Found in: {actual_folder}"
            pdf.cell(140, 5, clean_text(subtext))
            
            pdf.set_y(gap_y + 19)

    # --- 4. MASTER LEDGER ---
    pdf.add_page()
    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Adherence Master Ledger", ln=True)
    pdf.ln(2)
    
    col_widths = [25, 60, 25, 70]
    draw_table_row(pdf, ["Phase", "Document", "Status", "AI Diagnostics"], 
                   col_widths, fill_color=(241, 245, 249), is_header=True)
    
    row_idx = 0
    for phase, info in results.get("phases", {}).items():
        for d in info.get("documents", []):
            if "N/A:" in d.get("comment", ""):
                loc_status, status_color = "PASS (Optional)", (100, 116, 139)
            elif not d.get("actual_folder") or d.get("actual_folder") == "N/A":
                loc_status, status_color = "Missing", (239, 68, 68)
            elif d.get("wrong_folder"):
                loc_status, status_color = f"{'PASS' if d['pass'] else 'FAIL'} - Misplaced", (245, 158, 11)
            else:
                loc_status = "PASS" if d["pass"] else "FAIL"
                status_color = (34, 197, 94) if d["pass"] else (239, 68, 68)

            bg_color = (255, 255, 255) if row_idx % 2 == 0 else (248, 250, 252)
            text_colors = {2: status_color} 
            
            draw_table_row(pdf, [phase, d["document"], loc_status, d.get("comment", "No diagnostic.")], 
                           col_widths, fill_color=bg_color, text_colors=text_colors)
            row_idx += 1

    # --- 5. SIGNATURE CAPTURES ---
    has_signatures = any(d.get("signature_image_path") for phase, info in results.get("phases", {}).items() for d in info.get("documents", []))
    
    if has_signatures:
        pdf.add_page()
        pdf.set_text_color(15, 23, 42)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, "Signature Verification Captures", ln=True)
        pdf.ln(4)
        
        for phase, info in results.get("phases", {}).items():
            for d in info.get("documents", []):
                sig_path = d.get("signature_image_path")
                if sig_path and os.path.exists(sig_path):
                    if pdf.get_y() > 220:
                        pdf.add_page()
                        
                    pdf.set_font("Arial", "B", 10)
                    pdf.set_text_color(71, 85, 105)
                    pdf.cell(0, 6, f"Document: {clean_text(d.get('document', 'Unknown'))} ({phase} Phase)", ln=True)
                    
                    try:
                        pdf.image(sig_path, x=15, w=180)
                        pdf.ln(8) 
                    except Exception as e:
                        pdf.set_text_color(239, 68, 68)
                        pdf.cell(0, 6, f"[Error loading signature image for {clean_text(d.get('document', 'Unknown'))}]", ln=True)

    os.makedirs("results", exist_ok=True)
    file_path = f"results/{clean_text(company)}_{clean_text(cat_name).replace(' ', '_')}_Adherence_Report.pdf"
    pdf.output(file_path)
    return file_path


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 24px 0 20px 0; border-bottom: 1px solid rgba(99,179,237,0.1); margin-bottom: 24px;">
        <div class="sidebar-logo">MINT</div>
        <div style="font-size:0.72rem; color:#475569; margin-top:4px; letter-spacing:0.06em; text-transform:uppercase;">
            Compliance Intelligence Platform
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="mint-section-label">Engagement Setup</div>', unsafe_allow_html=True)
    company = st.text_input("Company Name", placeholder="e.g. Acme Corporation", label_visibility="collapsed")
    st.markdown('<div style="font-size:0.72rem; color:#475569; margin-bottom:6px; letter-spacing:0.05em; text-transform:uppercase;">Company Name</div>', unsafe_allow_html=True)

    # --- NEW DROPDOWN FOR PROJECT CATEGORY ---
    project_category = st.selectbox(
        "Project Category",
        ["MINT", "Solution Partner", "Track and Trace"],
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
                if st.button("Load Audit", type="primary", use_container_width=True):
                    st.session_state.audit_results = options[selected_key]
                    st.session_state.audit_company = company
                    st.rerun()

    # ── ZIP Upload ──
    elif data_source == "Local ZIP Upload":
        uploaded_file = st.file_uploader("Upload ZIP Archive", type="zip")
        if uploaded_file:
            target_zip_for_audit = uploaded_file
            target_folder_name = uploaded_file.name
            st.markdown(f'<div style="font-size:0.78rem; color:#4ADE80; padding:6px 0;">✓ {uploaded_file.name}</div>', unsafe_allow_html=True)

    # ── Google Drive ──
    elif data_source == "Google Drive":
        search_term = st.text_input("Search Drive", placeholder="Enter company folder name")

        if st.button("Search Drive", use_container_width=True):
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

                if st.button("Extract Files", use_container_width=True):
                    if company:
                        try:
                            target_dir = f"downloads/{company}"
                            if os.path.exists(target_dir):
                                shutil.rmtree(target_dir)
                            os.makedirs(target_dir, exist_ok=True)
                            with st.spinner("Downloading from Drive..."):
                                download_folder_recursively(drive_service, target_folder["id"], target_dir)
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

        if st.button("Run Compliance Audit", type="primary", use_container_width=True):
            if not company:
                st.error("Company name is required.")
            elif data_source == "Local ZIP Upload" and not target_zip_for_audit:
                st.error("Please upload a ZIP archive.")
            elif data_source == "Google Drive" and not drive_ready and not os.path.exists(f"downloads/{company}"):
                st.error("Please extract files from Drive first.")
            else:
                with st.status("Running compliance audit...", expanded=True) as status_box:
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
                        file_logger("[SYSTEM] Extracting uploaded archive...")
                        target_dir = f"downloads/{company}"
                        if os.path.exists(target_dir):
                            shutil.rmtree(target_dir)
                        os.makedirs(target_dir, exist_ok=True)
                        
                        target_zip_for_audit.seek(0)
                        with zipfile.ZipFile(target_zip_for_audit, "r") as zip_ref:
                            zip_ref.extractall(target_dir)

                    pass_phase = None if forced_phase == "Auto-Detect" else forced_phase
                    
                    results = run_pipeline(
                        company,
                        project_category,
                        project_type,
                        log_callback=file_logger,
                        progress_callback=ui_progress,
                        forced_phase=pass_phase,
                        folder_name=target_folder_name
                    )
                    save_audit_history(company, results)
                    status_box.update(label="Audit complete.", state="complete", expanded=False)

                st.session_state.audit_results = results
                st.session_state.audit_company = company
                st.rerun()

    # ── Reset ──
    if st.session_state.audit_results is not None:
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
        if st.button("Clear Dashboard", use_container_width=True):
            st.session_state.audit_results = None
            st.session_state.audit_company = None
            st.rerun()


# ─────────────────────────────────────────────
#  MAIN AREA — LANDING STATE
# ─────────────────────────────────────────────
if st.session_state.audit_results is None:
    st.markdown("""
    <div style="
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 100px 40px;
        text-align: center;
    ">
        <div style="
            font-size: 3.8rem;
            font-weight: 700;
            color: #F1F5F9;
            font-family: 'Sora', sans-serif;
            letter-spacing: -0.03em;
            line-height: 1.1;
            margin-bottom: 16px;
        ">
            Compliance Intelligence<br>
            <span style="color: #3B82F6;">Dashboard</span>
        </div>
        <div style="
            font-size: 1rem;
            color: #475569;
            max-width: 500px;
            line-height: 1.7;
            margin-bottom: 40px;
        ">
            Configure your engagement in the sidebar, select a data source,
            and initiate the audit to generate a full adherence report.
        </div>
        <div style="
            display: flex;
            gap: 24px;
            flex-wrap: wrap;
            justify-content: center;
        ">
            <div style="
                background: rgba(255,255,255,0.025);
                border: 1px solid rgba(99,179,237,0.1);
                border-radius: 10px;
                padding: 20px 28px;
                width: 180px;
            ">
                <div style="font-size:1.6rem; margin-bottom:8px;">◈</div>
                <div style="font-size:0.8rem; font-weight:600; color:#94A3B8;">Phase Detection</div>
            </div>
            <div style="
                background: rgba(255,255,255,0.025);
                border: 1px solid rgba(99,179,237,0.1);
                border-radius: 10px;
                padding: 20px 28px;
                width: 180px;
            ">
                <div style="font-size:1.6rem; margin-bottom:8px;">⬡</div>
                <div style="font-size:0.8rem; font-weight:600; color:#94A3B8;">AI Document Audit</div>
            </div>
            <div style="
                background: rgba(255,255,255,0.025);
                border: 1px solid rgba(99,179,237,0.1);
                border-radius: 10px;
                padding: 20px 28px;
                width: 180px;
            ">
                <div style="font-size:1.6rem; margin-bottom:8px;">▦</div>
                <div style="font-size:0.8rem; font-weight:600; color:#94A3B8;">Risk Classification</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  MAIN AREA — DASHBOARD STATE
# ─────────────────────────────────────────────
else:
    results = st.session_state.audit_results
    comp    = st.session_state.audit_company
    overall = results.get("overall_score", 0)
    maturity = maturity_level(overall)
    cat_name = results.get("project_category", "MINT")

    total_docs  = sum(len(p.get("documents", [])) for p in results.get("phases", {}).values())
    passed_docs = sum(1 for p in results.get("phases", {}).values() for d in p.get("documents", []) if d.get("pass"))
    pass_rate   = round(passed_docs / total_docs * 100, 1) if total_docs > 0 else 0

    current_ts   = results.get("audit_timestamp", "")
    history      = load_company_history(comp)
    older_audits = [h for h in history if h.get("audit_timestamp", "") < current_ts]
    
    if older_audits:
        benchmark_score = older_audits[0].get("overall_score", 0)
        delta_val       = f"{round(overall - benchmark_score, 1):+.1f}% vs last audit"
    else:
        benchmark_score = None
        delta_val       = "First audit"

    # ── Page Header ──
    st.markdown(f"""
    <div style="
        padding: 32px 0 24px 0;
        border-bottom: 1px solid rgba(99,179,237,0.08);
        margin-bottom: 32px;
    ">
        <div style="font-size:0.72rem; font-weight:600; letter-spacing:0.15em; color:#3B82F6; text-transform:uppercase; margin-bottom:6px;">
            Compliance Intelligence Report ({cat_name})
        </div>
        <div style="
            font-size: 2rem;
            font-weight: 700;
            color: #F1F5F9;
            font-family: 'Sora', sans-serif;
            letter-spacing: -0.02em;
        ">
            {comp}
        </div>
        <div style="font-size:0.82rem; color:#475569; margin-top:4px;">
            Detected Phase: <span style="color:#94A3B8; font-weight:500;">{results.get('detected_phase', 'N/A')}</span>
            &nbsp;&nbsp;·&nbsp;&nbsp;
            Project Type: <span style="color:#94A3B8; font-weight:500;">{results.get('project_type', 'N/A')}</span>
            &nbsp;&nbsp;·&nbsp;&nbsp;
            Generated: <span style="color:#94A3B8; font-weight:500;">{datetime.datetime.now().strftime("%B %d, %Y  %H:%M")}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI Row ──
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Overall Adherence", f"{overall}%", delta=delta_val)
    with col2:
        st.metric("Document Pass Rate", f"{pass_rate}%", delta=f"{passed_docs}/{total_docs} documents")
    with col3:
        st.metric("Maturity Level", maturity)
    with col4:
        st.metric(
            "Risk Classification",
            results.get("risk_level", "Unknown"),
            delta="Needs attention" if overall < 70 else "Within tolerance",
            delta_color="inverse"
        )

    st.markdown('<div style="height:32px;"></div>', unsafe_allow_html=True)

    # ── Phase Pipeline ──
    st.markdown('<div class="mint-section-label">Phase Progression</div>', unsafe_allow_html=True)
    st.markdown('<div class="mint-section-title" style="margin-bottom:16px;">Lifecycle Adherence Pipeline</div>', unsafe_allow_html=True)

    phase_list  = list(results.get("phases", {}).items())
    if phase_list:
        phase_cols  = st.columns(len(phase_list))
        detected_ph = results.get("detected_phase", "")

        for i, (phase, info) in enumerate(phase_list):
            score  = info.get("score", 0)
            clr    = score_color(score)
            active = "phase-active" if phase == detected_ph else ""
            with phase_cols[i]:
                st.markdown(f"""
                <div class="phase-node {active}">
                    <div class="phase-node-label">{phase}</div>
                    <div class="phase-node-score" style="color:{clr};">{score}%</div>
                    <div style="font-size:0.68rem; color:#475569; margin-top:4px;">
                        {sum(1 for d in info.get('documents', []) if d.get('pass'))}/{len(info.get('documents', []))} docs
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown('<div style="height:32px;"></div>', unsafe_allow_html=True)

    # ── Charts Row ──
    chart_col, gap_col = st.columns([1, 1], gap="large")

    with chart_col:
        st.markdown('<div class="mint-section-label">Performance Analysis</div>', unsafe_allow_html=True)
        st.markdown('<div class="mint-section-title" style="margin-bottom:16px;">Phase Score Distribution</div>', unsafe_allow_html=True)

        phase_names  = list(results.get("phases", {}).keys())
        phase_scores = [results["phases"][p].get("score", 0) for p in phase_names]

        # Bar chart
        if phase_names:
            bar_colors = [score_color(s) for s in phase_scores]
            fig_bar = go.Figure(go.Bar(
                x=phase_names,
                y=phase_scores,
                marker=dict(
                    color=bar_colors,
                    opacity=0.85,
                    line=dict(width=0)
                ),
                text=[f"{s}%" for s in phase_scores],
                textposition="outside",
                textfont=dict(color="#94A3B8", size=11, family="Sora"),
            ))
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Sora", color="#64748B", size=11),
                margin=dict(l=0, r=0, t=10, b=0),
                height=260,
                yaxis=dict(
                    range=[0, 115],
                    showgrid=True,
                    gridcolor="rgba(99,179,237,0.06)",
                    zeroline=False,
                    tickfont=dict(color="#475569"),
                    ticksuffix="%",
                ),
                xaxis=dict(
                    showgrid=False,
                    tickfont=dict(color="#64748B"),
                ),
                showlegend=False,
            )
            st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    with gap_col:
        st.markdown('<div class="mint-section-label">Action Required</div>', unsafe_allow_html=True)
        st.markdown('<div class="mint-section-title" style="margin-bottom:16px;">Priority Gap Register</div>', unsafe_allow_html=True)

        gaps = top_gaps(results)
        if not gaps:
            st.markdown("""
            <div style="
                padding: 32px;
                text-align: center;
                background: rgba(34,197,94,0.04);
                border: 1px solid rgba(34,197,94,0.15);
                border-radius: 10px;
            ">
                <div style="font-size:1.4rem; margin-bottom:8px;">✓</div>
                <div style="font-size:0.88rem; color:#4ADE80; font-weight:600;">All documents verified</div>
                <div style="font-size:0.78rem; color:#475569; margin-top:4px;">No compliance gaps detected.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for phase, doc, score, wrong_folder, actual_folder in gaps:
                severity_class = "gap-warning" if wrong_folder else "gap-critical"
                badge_class    = "badge-warn"   if wrong_folder else "badge-fail"
                badge_text     = "MISPLACED"    if wrong_folder else "MISSING"
                ai_comment     = "No diagnostic available."
                
                for d in results["phases"][phase]["documents"]:
                    if d["document"] == doc:
                        ai_comment = d.get("comment", ai_comment)
                        break
                
                clean_phase = str(phase).strip()
                clean_comment = str(ai_comment).replace('\n', ' ').strip()
                truncated = (clean_comment[:90] + "…") if len(clean_comment) > 90 else clean_comment
                
                found_html = f'&nbsp;·&nbsp; Found in: <span style="color:#FACC15;">{actual_folder}</span>' if wrong_folder else ''
                
                html_str = f"""
                <div class="gap-item {severity_class}">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:4px;">
                        <div style="font-size:0.82rem; font-weight:600; color:#E2E8F0; flex:1; padding-right:8px;">{doc}</div>
                        <span class="mint-badge {badge_class}">{badge_text}</span>
                    </div>
                    <div style="font-size:0.72rem; color:#475569; margin-bottom:4px;">{clean_phase}{found_html}&nbsp;·&nbsp; Score: <span style="color:#94A3B8;">{score}%</span></div>
                    <div style="font-size:0.75rem; color:#64748B; line-height:1.5;">{truncated}</div>
                </div>
                """
                st.markdown(html_str, unsafe_allow_html=True)

    st.markdown('<div style="height:32px;"></div>', unsafe_allow_html=True)

    # ── Master Ledger ──
    st.markdown('<div class="mint-section-label">Document Register</div>', unsafe_allow_html=True)
    st.markdown('<div class="mint-section-title" style="margin-bottom:16px;">Adherence Master Ledger</div>', unsafe_allow_html=True)

    table_data = []
    for phase, info in results.get("phases", {}).items():
        for d in info.get("documents", []):
            if "N/A:" in d.get("comment", ""):
                loc_status, status_color = "PASS (Optional)", (100, 116, 139)
            elif not d.get("actual_folder") or d.get("actual_folder") == "N/A":
                loc_status, status_color = "Missing", (239, 68, 68)
            elif d.get("wrong_folder"):
                loc_status, status_color = f"{'PASS' if d['pass'] else 'FAIL'} - Misplaced", (245, 158, 11)
            else:
                loc_status = "PASS" if d["pass"] else "FAIL"
                status_color = (34, 197, 94) if d["pass"] else (239, 68, 68)

            table_data.append({
                "Phase":        phase,
                "Document":     d.get("document", "Unknown"),
                "Score":        d.get("score", 0),
                "Status":       "Pass" if d.get("pass") else "Fail",
                "Location":     loc_status,
                "Diagnostics":  d.get("comment", ""),
            })

    df_ledger = pd.DataFrame(table_data)
    if not df_ledger.empty:
        st.dataframe(
            df_ledger,
            column_config={
                "Score": st.column_config.ProgressColumn(
                    "Health Score", format="%d%%", min_value=0, max_value=100
                ),
                "Status": st.column_config.TextColumn("Status"),
            },
            use_container_width=True,
            hide_index=True,
            height=380,
        )

    st.markdown('<div style="height:32px;"></div>', unsafe_allow_html=True)

    # ── Export Section ──
    st.markdown('<div class="mint-section-label">Report Exports</div>', unsafe_allow_html=True)
    st.markdown('<div class="mint-section-title" style="margin-bottom:16px;">Download Artifacts</div>', unsafe_allow_html=True)

    ex_col1, ex_col2 = st.columns(2, gap="large")

    with ex_col1:
        st.markdown("""
        <div class="export-card">
            <div class="export-card-title">Executive PDF Report</div>
            <div class="export-card-desc">Full adherence brief with phase scores, ledger, and AI diagnostics. Formatted for board-level review.</div>
        </div>
        """, unsafe_allow_html=True)
        pdf_path = generate_pdf(comp, results)
        
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
            
        st.download_button(
            "Download PDF Report",
            data=pdf_bytes,
            file_name=f"{clean_text(comp)}_{clean_text(cat_name).replace(' ', '_')}_Adherence_Report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    with ex_col2:
        st.markdown("""
        <div class="export-card">
            <div class="export-card-title">Ledger CSV Export</div>
            <div class="export-card-desc">Machine-readable compliance ledger for integration with your data warehouse or project tracking systems.</div>
        </div>
        """, unsafe_allow_html=True)
        if not df_ledger.empty:
            csv_bytes = df_ledger.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download Ledger CSV",
                data=csv_bytes,
                file_name=f"{clean_text(comp)}_Adherence_Ledger.csv",
                mime="text/csv",
                use_container_width=True,
            )

    st.markdown('<div style="height:48px;"></div>', unsafe_allow_html=True)