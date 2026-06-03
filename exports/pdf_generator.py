import os
import datetime
from fpdf import FPDF
from utils.helpers import clean_text, top_gaps, maturity_level

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
    cat_name = results.get("project_category", "Adherence")
    pdf = ExecutivePDF(company, cat_name)
    
    # 1. COVER PAGE
    pdf.add_page()
    pdf.set_fill_color(8, 12, 20)
    pdf.rect(0, 0, 210, 297, 'F') 
    
    current_y = 80
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    my_logo_path = os.path.join(base_dir, "logo.png")
    
    if os.path.exists(my_logo_path):
        try:
            pdf.image(my_logo_path, x=85, y=35, w=40)
            current_y = 95 
        except Exception:
            pass 

    pdf.set_y(current_y)
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(59, 130, 246)
    pdf.cell(0, 10, f"{cat_name.upper()}", align='C', ln=True)
    
    pdf.set_font("Arial", "B", 26)
    pdf.set_text_color(241, 245, 249)
    pdf.cell(0, 14, "Executive Adherence Report", align='C', ln=True)
    
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
    
    # 2. MAIN CONTENT PAGE
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

    # 3. PRIORITY GAP REGISTER
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

    # 4. MASTER LEDGER
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

    # 5. SIGNATURE CAPTURES
    def _get_sig_paths(doc_dict):
        paths = doc_dict.get("signature_image_paths", [])
        if paths: return paths if isinstance(paths, list) else [paths]
        legacy = doc_dict.get("signature_image_path")
        if legacy: return [legacy] if isinstance(legacy, str) else []
        return []

    has_signatures = any(
        _get_sig_paths(d)
        for _, info in results.get("phases", {}).items()
        for d in info.get("documents", [])
    )

    if has_signatures:
        first_doc = True
        for phase, info in results.get("phases", {}).items():
            for d in info.get("documents", []):
                sig_paths = _get_sig_paths(d)
                valid_paths = [p for p in sig_paths if p and os.path.exists(p)]

                if not valid_paths:
                    continue

                pdf.add_page() 

                if first_doc:
                    pdf.set_text_color(15, 23, 42)
                    pdf.set_font("Arial", "B", 14)
                    pdf.cell(0, 8, "Signature Verification Captures", ln=True)
                    pdf.ln(4)
                    first_doc = False

                pdf.set_font("Arial", "B", 10)
                pdf.set_text_color(37, 99, 235)
                doc_label = f"Document: {clean_text(d.get('document', 'Unknown'))}  |  Phase: {phase}"
                pdf.multi_cell(0, 6, doc_label, align='L')

                pdf.set_draw_color(37, 99, 235)
                pdf.set_line_width(0.4)
                pdf.line(15, pdf.get_y() + 1, 195, pdf.get_y() + 1)
                pdf.ln(4)

                for img_idx, sig_path in enumerate(valid_paths):
                    if img_idx > 0:
                        pdf.add_page()
                        pdf.set_font("Arial", "I", 8)
                        pdf.set_text_color(100, 116, 139)
                        pdf.cell(0, 5, f"Signature Page {img_idx + 1} of {len(valid_paths)}", ln=True)
                        pdf.ln(2)

                    try:
                        pdf.image(sig_path, x=25, w=160)
                        pdf.ln(6)
                    except Exception as e:
                        pdf.set_font("Arial", "", 9)
                        pdf.set_text_color(239, 68, 68)
                        pdf.cell(0, 6, f"[Image load error: {clean_text(str(e))}]", ln=True)


    os.makedirs("results", exist_ok=True)
    file_path = f"results/{clean_text(company)}_{clean_text(cat_name).replace(' ', '_')}_Adherence_Report.pdf"
    pdf.output(file_path)
    return file_path