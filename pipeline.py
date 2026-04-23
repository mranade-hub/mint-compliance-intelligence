import os
import json
import re
from wolfgang_client import WolfgangClient
from auditor import ai_deep_audit_batch
from compliance_matrix import COMPLIANCE_MATRIX

PHASE_ORDER = list(COMPLIANCE_MATRIX.keys())

def normalize_str(s):
    if not s: return ""
    return re.sub(r'[^a-z0-9]', '', str(s).lower())

def run_pipeline(company, project_type, log_callback=None, progress_callback=None):
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

        for phase in PHASE_ORDER:
            phase_docs_dict = COMPLIANCE_MATRIX.get(phase, {})
            phase_results = []

            for doc, allowed_types in phase_docs_dict.items():
                if project_type not in allowed_types:
                    continue

                qualities = compliance_map.get(normalize_str(doc), [])

                if not qualities:
                    phase_results.append({
                        "document": doc, "quality": {}, "score": 0, "pass": False,
                        "wrong_folder": False, "actual_folder": "N/A", "expected_phase": phase,
                        "comment": "Missing: No document submitted for this requirement."
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
                        # Removed the harsh 10-point penalty for being in the wrong folder

                comment = best_quality.get("short_summary", "")
                
                if wrong_folder:
                    comment = f"⚠️ Wrong Folder ({actual_folder}). " + comment
                elif not comment:
                    comment = "Complete and adherent." if best_score >= 70 else "Incomplete or template-based."

                phase_results.append({
                    "document": doc, "quality": best_quality, "score": max(0, best_score),
                    "pass": best_score >= 70, "wrong_folder": wrong_folder,
                    "actual_folder": actual_folder, "expected_phase": phase, "comment": comment
                })

            avg_score = round(sum(d["score"] for d in phase_results) / len(phase_results), 2) if phase_results else 0
            final[phase] = {"documents": phase_results, "score": avg_score}

        # --- SMART PHASE DETECTION & SCORING LOGIC ---
        detected_phase = PHASE_ORDER[0]
        for phase in PHASE_ORDER:
            has_real_docs = any(d["score"] >= 50 for d in final[phase]["documents"])
            if has_real_docs: 
                detected_phase = phase

        detected_index = PHASE_ORDER.index(detected_phase)
        active_phases = PHASE_ORDER[:detected_index + 1]
        overall_score = round(sum(final[p]["score"] for p in active_phases) / len(active_phases), 2) if active_phases else 0

        risk = "🟢 Low Risk" if overall_score >= 85 else "🟡 Moderate Risk" if overall_score >= 70 else "🟠 High Risk" if overall_score >= 50 else "🔴 Critical Risk"
        
        # Updated Terminology
        executive_summary = f"Project assessed at {detected_phase} phase with {overall_score}% adherence. Classified as {risk}."

        return {
            "overall_score": overall_score, "detected_phase": detected_phase,
            "risk_level": risk, "executive_summary": executive_summary, "phases": final
        }

    finally:
        wolfgang.close()