import os
import json
import re
import shutil

# Safely import PyMuPDF for signature image extraction and template heuristic reading
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

def detect_template_heuristics(pdf_path, company_name):
    """Returns True if the document heavily looks like a blank, unpopulated template."""
    if not HAS_FITZ or not pdf_path.lower().endswith(".pdf"):
        return False
    
    try:
        doc = fitz.open(pdf_path)
        text = ""
        # Check up to the first 10 pages for speed
        for i in range(min(10, len(doc))):
            text += doc[i].get_text().lower() + " "
        doc.close()
        
        comp_normalized = company_name.lower().split()[0]
        has_company = comp_normalized in text
        
        placeholders = len(re.findall(r'\[.*?\]|<.*?>|insert \w+ here', text))
        
        template_phrases = ["company name", "customer name", "partner name", "yyyymmdd"]
        has_template_phrase = any(p in text for p in template_phrases)

        if not has_company and (placeholders > 4 or has_template_phrase):
            return True
            
        return False
    except Exception:
        return False

# ─────────────────────────────────────────────
#  FIX 1 + FIX 6: extract ALL signature pages,
#  save to a persistent path (not temp_signatures)
# ─────────────────────────────────────────────
def extract_signature_images(pdf_path, doc_name, company="shared"):
    """
    Scans every page of the PDF. Returns a list of PNG paths — one full-page
    screenshot per page that contains signature-related content.

    Changes from the old single-path version:
      - Returns a LIST instead of a single path string.
      - Captures ALL pages above the score threshold, not just the best one.
      - Saves to audit_history/signatures/<company>/ so images survive across sessions.
      - Falls back to the last page if no keyword match is found.
    """
    if not HAS_FITZ or not pdf_path.lower().endswith(".pdf"):
        return []

    try:
        doc = fitz.open(pdf_path)

        # Weighted keyword scoring — same logic as before
        sig_keywords = {
            "electronically signed by:": 20,
            "docusign": 10,
            "digitally signed": 10,
            "signature:": 5,
            "approved by": 5,
            "sign here": 5,
            "signed by": 4,
            "date:": 1,
            "title:": 1,
        }

        # FIX 6: persistent folder so loaded-from-JSON audits still find the images
        sig_dir = os.path.join("audit_history", "signatures", re.sub(r'[^a-zA-Z0-9_-]', '_', company))
        os.makedirs(sig_dir, exist_ok=True)

        clean_name = re.sub(r'[^a-zA-Z0-9]', '_', doc_name)
        SCORE_THRESHOLD = 4  # Capture any page scoring above this

        captured_paths = []
        page_scores = []

        for i in range(len(doc)):
            text = doc[i].get_text().lower()
            score = sum(
                weight * text.count(kw)
                for kw, weight in sig_keywords.items()
                if kw in text
            )
            page_scores.append((i, score))

        # FIX 1: capture every qualifying page, not just the best one
        qualifying_pages = [
            (idx, sc) for idx, sc in page_scores if sc >= SCORE_THRESHOLD
        ]

        for idx, _ in qualifying_pages:
            page = doc[idx]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            out_path = os.path.join(sig_dir, f"{clean_name}_page{idx + 1}.png")
            pix.save(out_path)
            captured_paths.append(out_path)

        # Fallback: if no keyword match found, grab the very last page
        if not captured_paths:
            last_idx = len(doc) - 1

            # Also check last 3 pages for graphical elements (embedded signature images)
            fallback_idx = last_idx
            for i in range(max(0, last_idx - 2), last_idx + 1):
                images = doc[i].get_images()
                for img in images:
                    if img[2] > 50 and img[3] > 20:   # width > 50px, height > 20px
                        fallback_idx = i
                        break

            page = doc[fallback_idx]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            out_path = os.path.join(sig_dir, f"{clean_name}_last_page.png")
            pix.save(out_path)
            captured_paths.append(out_path)

        doc.close()
        return captured_paths

    except Exception as e:
        print(f"[SIGNATURE] Error extracting pages for '{doc_name}': {e}")
        return []


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

        if log_callback: log_callback("[SYSTEM] Deep audit complete. Initializing Backend Verification Checklist...")
        if progress_callback: progress_callback(1, 1, "Reconciling Checklist & Generating Report...")

        from collections import defaultdict
        compliance_map = defaultdict(list)
        
        if isinstance(ai_results, list):
            for item in ai_results:
                c_type = item.get("compliance_type")
                if c_type: 
                    compliance_map[normalize_str(c_type)].append(item)

        final = {}
        
        working_phases = PHASE_ORDER
        if forced_phase and forced_phase in PHASE_ORDER:
            allowed_index = PHASE_ORDER.index(forced_phase)
            working_phases = PHASE_ORDER[:allowed_index + 1]
            if log_callback: log_callback(f"[SYSTEM] Forcing audit scope to stop at phase: {forced_phase}")

        checklist_logs = []
        missing_critical_docs = []

        # ─────────────────────────────────────────────
        #  FIX 4: corrected sig_required_docs
        #    - Fixed typo:  "servicesow" → "servicessow"
        #      (normalize_str("Services - SOW") = "servicessow")
        #    - Removed "hld" and "configspec" — not present in COMPLIANCE_MATRIX
        # ─────────────────────────────────────────────
        sig_required_docs = [
            "designdocfullyexecuted",       # Design Doc fully executed
            "servicessow",                  # Services - SOW  (was "servicesow" — typo fix)
            "ird",                          # IRD
            "internaltransitiondocument",   # Internal Transition Document
            "mintprojectcompletionform",    # MINT Project Completion Form
        ]

        for phase in working_phases:
            phase_docs_dict = COMPLIANCE_MATRIX.get(phase, {})
            phase_results = []

            for doc, allowed_types in phase_docs_dict.items():
                
                # MINT SS EXCEPTION FOR IRD
                if "MINT SS" in folder_name.upper() and normalize_str(doc) == normalize_str("IRD"):
                    if log_callback: log_callback(f"[SYSTEM] MINT SS Project detected. Bypassing IRD requirement.")
                    continue
                    
                if project_type not in allowed_types:
                    continue
                    
                # OPTIONAL/CONDITIONAL CHECK
                is_optional = "optional" in doc.lower() or "conditional" in doc.lower()

                qualities = compliance_map.get(normalize_str(doc), [])

                if not qualities:
                    if is_optional:
                        phase_results.append({
                            "document": doc, "quality": {}, "score": 100, "pass": True,
                            "wrong_folder": False, "actual_folder": "N/A", "expected_phase": phase,
                            "comment": "N/A: Optional Requirement.",
                            # FIX 2: use list instead of single path
                            "signature_image_paths": []
                        })
                        checklist_logs.append(f"[CHECKLIST] {doc} ➖ Bypassed (Optional)")
                    else:
                        phase_results.append({
                            "document": doc, "quality": {}, "score": 0, "pass": False,
                            "wrong_folder": False, "actual_folder": "N/A", "expected_phase": phase,
                            "comment": "Missing: No document submitted for this requirement.",
                            # FIX 2: use list instead of single path
                            "signature_image_paths": []
                        })
                        missing_critical_docs.append(doc)
                        checklist_logs.append(f"[CHECKLIST] {doc} ❌ Missing")
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
                
                is_template = False
                if file_path:
                    is_template = detect_template_heuristics(file_path, company)
                    if is_template:
                        best_score = min(best_score, 40)
                        best_quality["appears_template_only"] = True

                if file_path:
                    actual_folder = os.path.basename(os.path.dirname(file_path))
                    if actual_folder.lower() == company.lower():
                        actual_folder = "Root Directory"
                        
                    phase_keyword = phase.split()[0].lower() 
                    if phase_keyword not in file_path.lower():
                        wrong_folder = True

                comment = best_quality.get("short_summary", "")

                # ─────────────────────────────────────────────
                #  FIX 2 + FIX 3: signature_image_paths is now
                #  a LIST. Extraction runs regardless of score
                #  (removed the best_score < 70 gate).
                # ─────────────────────────────────────────────
                signature_image_paths = []

                if normalize_str(doc) in sig_required_docs:
                    if is_template:
                        comment = "⚠️ Blank Template Detected. Signatures missing. " + comment
                    elif best_score < 70:
                        # FIX 3: still flag the comment but DO attempt extraction
                        comment = "⚠️ Document incomplete (Signatures may be missing). " + comment

                    # FIX 3: extraction is now OUTSIDE the score gate — always runs for PDFs
                    if file_path and file_path.lower().endswith(".pdf"):
                        signature_image_paths = extract_signature_images(file_path, doc, company)
                        if signature_image_paths:
                            comment += f" [System: {len(signature_image_paths)} signature page(s) captured]."
                        elif not HAS_FITZ:
                            comment += " [System Note: PyMuPDF not installed — signature page images skipped]."
                        else:
                            comment += " [System Note: No signature pages detected in PDF]."

                if is_template:
                    comment = f"⚠️ Blank Template Detected. " + comment
                elif wrong_folder:
                    comment = f"⚠️ Wrong Folder ({actual_folder}). " + comment
                elif not comment:
                    comment = "Complete and adherent." if best_score >= 70 else "Incomplete or template-based."

                if best_score >= 70:
                    checklist_logs.append(f"[CHECKLIST] {doc} ✅ Passed ({best_score}%)")
                else:
                    checklist_logs.append(f"[CHECKLIST] {doc} ⚠️ Failed ({best_score}%)")

                phase_results.append({
                    "document": doc, "quality": best_quality, "score": max(0, best_score),
                    "pass": best_score >= 70, "wrong_folder": wrong_folder,
                    "actual_folder": actual_folder, "expected_phase": phase, "comment": comment,
                    # FIX 2: list of paths, one per captured signature page
                    "signature_image_paths": signature_image_paths
                })

            avg_score = round(sum(d["score"] for d in phase_results) / len(phase_results), 2) if phase_results else 0
            final[phase] = {"documents": phase_results, "score": avg_score}

        if log_callback:
            log_callback("--- INTERNAL VERIFICATION CHECKLIST ---")
            for clog in checklist_logs:
                log_callback(clog)
            if missing_critical_docs:
                log_callback(f"[CHECKLIST WARNING] {len(missing_critical_docs)} critical documents completely missing.")
            log_callback("---------------------------------------")

        if forced_phase and forced_phase in PHASE_ORDER:
            detected_phase = forced_phase
        else:
            detected_phase = working_phases[0]
            for phase in working_phases:
                has_real_docs = any(d["score"] >= 70 for d in final[phase]["documents"])
                if has_real_docs: 
                    detected_phase = phase

        detected_index = PHASE_ORDER.index(detected_phase)
        active_phases = PHASE_ORDER[:detected_index + 1]
        
        valid_phase_scores = [final[p]["score"] for p in active_phases if p in final]
        overall_score = round(sum(valid_phase_scores) / len(valid_phase_scores), 2) if valid_phase_scores else 0

        risk = "🟢 Low Risk" if overall_score >= 85 else "🟡 Moderate Risk" if overall_score >= 70 else "🟠 High Risk" if overall_score >= 50 else "🔴 Critical Risk"
        
        executive_summary = f"Project assessed at {detected_phase} phase with {overall_score}% adherence. Classified as {risk}."

        return {
            "overall_score": overall_score, "detected_phase": detected_phase,
            "risk_level": risk, "executive_summary": executive_summary, "phases": final
        }

    finally:
        wolfgang.close()