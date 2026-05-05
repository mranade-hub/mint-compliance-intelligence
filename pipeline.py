import os
import json
import re
import shutil

# Safely import PyMuPDF for signature image extraction
try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

from wolfgang_client import WolfgangClient
from auditor import ai_deep_audit_batch
from compliance_matrix import COMPLIANCE_MATRIX

PHASE_ORDER = list(COMPLIANCE_MATRIX.keys())

def normalize_str(s):
    if not s: return ""
    return re.sub(r'[^a-z0-9]', '', str(s).lower())

def extract_signature_image(pdf_path, doc_name):
    """Helper function to find and extract the signature page as an image."""
    if not HAS_FITZ: 
        return None
        
    try:
        doc = fitz.open(pdf_path)
        sig_page_num = -1
        
        # Look for signature keywords in the last 5 pages
        search_range = range(max(0, len(doc) - 5), len(doc))
        for i in search_range:
            text = doc[i].get_text().lower()
            if any(kw in text for kw in ["signature", "signed", "approved by", "approval", "date:"]):
                sig_page_num = i
                break
                
        # Fallback to the very last page if no keywords are found
        if sig_page_num == -1:
            sig_page_num = len(doc) - 1 
            
        page = doc[sig_page_num]
        
        # Render the page to a high-res image
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        os.makedirs("temp_signatures", exist_ok=True)
        
        clean_name = re.sub(r'[^a-zA-Z0-9]', '_', doc_name)
        out_path = f"temp_signatures/{clean_name}_sig.png"
        pix.save(out_path)
        
        doc.close()
        return out_path
    except Exception as e:
        print(f"Error extracting signature for {doc_name}: {e}")
        return None


def run_pipeline(company, project_type, log_callback=None, progress_callback=None, forced_phase=None, folder_name="Unknown"):
    base = f"downloads/{company}"
    
    if log_callback: log_callback("[SYSTEM] Booting Wolfgang Client & authenticating session...")
    if progress_callback: progress_callback(0, 1, "Initializing Wolfgang AI Connection...")
    
    wolfgang = WolfgangClient()

    try:
        all_files = []
        for root, _, files in os.walk(base):
            for f in files:
                all_files.append(os.path.join(root, f))

        all_files = list(set(all_files))
        if log_callback: log_callback(f"[SYSTEM] Found {len(all_files)} total files. Beginning deep audit...")

        ai_results = ai_deep_audit_batch(
            "Full Project", all_files, wolfgang,
            log_callback=log_callback, progress_callback=progress_callback
        )

        if log_callback: log_callback("[SYSTEM] Deep audit complete. Calculating final maturity scores...")
        if progress_callback: progress_callback(1, 1, "Generating Executive Report...")

        from collections import defaultdict
        compliance_map = defaultdict(list)
        
        if isinstance(ai_results, list):
            for item in ai_results:
                c_type = item.get("compliance_type")
                if c_type: 
                    compliance_map[normalize_str(c_type)].append(item)

        final = {}
        
        # --- UPDATE 1: FORCE PHASE FILTERING ---
        working_phases = PHASE_ORDER
        if forced_phase and forced_phase in PHASE_ORDER:
            allowed_index = PHASE_ORDER.index(forced_phase)
            working_phases = PHASE_ORDER[:allowed_index + 1]
            if log_callback: log_callback(f"[SYSTEM] Forcing audit scope to stop at phase: {forced_phase}")

        for phase in working_phases:
            phase_docs_dict = COMPLIANCE_MATRIX.get(phase, {})
            phase_results = []

            for doc, allowed_types in phase_docs_dict.items():
                
                # --- UPDATE 2: MINT SS EXCEPTION FOR IRD ---
                if "MINT SS" in folder_name.upper() and normalize_str(doc) == normalize_str("IRD"):
                    if log_callback: log_callback(f"[SYSTEM] MINT SS Project detected. Bypassing IRD requirement.")
                    continue
                    
                if project_type not in allowed_types:
                    continue

                qualities = compliance_map.get(normalize_str(doc), [])

                if not qualities:
                    phase_results.append({
                        "document": doc, "quality": {}, "score": 0, "pass": False,
                        "wrong_folder": False, "actual_folder": "N/A", "expected_phase": phase,
                        "comment": "Missing: No document submitted for this requirement.",
                        "signature_image_path": None
                    })
                    continue

                best_score, best_quality = -1, None
                for q in qualities:
                    score = 0
                    if q.get("appears_filled"): score += 30
                    if q.get("contains_project_content"): score += 30
                    if not q.get("appears_template_only"): score += 20
                    if q.get("document_type_correct"): score += 20
                    if score > best_score:
                        best_score, best_quality = score, q

                if best_quality is None: best_quality, best_score = {}, 0

                file_path = best_quality.get("file_path", "")
                wrong_folder = False
                actual_folder = "N/A"
                
                if file_path:
                    actual_folder = os.path.basename(os.path.dirname(file_path))
                    if actual_folder.lower() == company.lower():
                        actual_folder = "Root Directory"
                        
                    phase_keyword = phase.split()[0].lower() 
                    if phase_keyword not in file_path.lower():
                        wrong_folder = True

                comment = best_quality.get("short_summary", "")
                signature_image_path = None
                
                # --- UPDATE 3: SIGNATURE EXTRACTION FOR CORE DOCS ---
                sig_required_docs = ["designdocfullyexecuted", "hld", "configspec", "ird"]
                if normalize_str(doc) in sig_required_docs:
                    if best_score < 70:
                        comment = "⚠️ Document incomplete (Signatures likely missing). " + comment
                    elif file_path and file_path.lower().endswith(".pdf"):
                        signature_image_path = extract_signature_image(file_path, doc)
                        if not signature_image_path and not HAS_FITZ:
                            comment += " [System Note: PyMuPDF not installed, couldn't extract signature image]."
                
                if wrong_folder:
                    comment = f"⚠️ Wrong Folder ({actual_folder}). " + comment
                elif not comment:
                    comment = "Complete and adherent." if best_score >= 70 else "Incomplete or template-based."

                phase_results.append({
                    "document": doc, "quality": best_quality, "score": max(0, best_score),
                    "pass": best_score >= 70, "wrong_folder": wrong_folder,
                    "actual_folder": actual_folder, "expected_phase": phase, "comment": comment,
                    "signature_image_path": signature_image_path
                })

            avg_score = round(sum(d["score"] for d in phase_results) / len(phase_results), 2) if phase_results else 0
            final[phase] = {"documents": phase_results, "score": avg_score}

        # --- SMART PHASE DETECTION & SCORING LOGIC ---
        if forced_phase and forced_phase in PHASE_ORDER:
            detected_phase = forced_phase
        else:
            detected_phase = working_phases[0]
            for phase in working_phases:
                has_real_docs = any(d["score"] >= 50 for d in final[phase]["documents"])
                if has_real_docs: 
                    detected_phase = phase

        detected_index = PHASE_ORDER.index(detected_phase)
        active_phases = PHASE_ORDER[:detected_index + 1]
        
        # Calculate overall score ONLY based on active/forced phases
        valid_phase_scores = [final[p]["score"] for p in active_phases if p in final]
        overall_score = round(sum(valid_phase_scores) / len(valid_phase_scores), 2) if valid_phase_scores else 0

        risk = "🟢 Low Risk" if overall_score >= 85 else "🟡 Moderate Risk" if overall_score >= 70 else "🟠 High Risk" if overall_score >= 50 else "🔴 Critical Risk"
        
        # Updated Terminology
        executive_summary = f"Project assessed at {detected_phase} phase with {overall_score}% adherence. Classified as {risk}."

        return {
            "overall_score": overall_score, "detected_phase": detected_phase,
            "risk_level": risk, "executive_summary": executive_summary, "phases": final
        }

    finally:
        wolfgang.close()