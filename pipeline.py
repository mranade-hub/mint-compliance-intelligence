import os
import json
from wolfgang_client import WolfgangClient
from structure_extractor import extract_structure
from auditor import ai_structure_validation, ai_deep_audit_batch
from compliance_matrix import COMPLIANCE_MATRIX

PHASE_ORDER = list(COMPLIANCE_MATRIX.keys())

def run_pipeline(company, project_type, log_callback=None, progress_callback=None):
    base = f"downloads/{company}"
    
    if log_callback: log_callback(f"[SYSTEM] Extracting directory structure for {company}...")
    structure_text = extract_structure(base)

    if log_callback: log_callback("[SYSTEM] Booting Wolfgang Client & authenticating session...")
    wolfgang = WolfgangClient()

    try:
        if log_callback: log_callback("[SYSTEM] Running initial folder structure validation...")
        structure_result = ai_structure_validation(
            structure_text,
            project_type,
            wolfgang
        )

        all_files = []
        for root, _, files in os.walk(base):
            for f in files:
                all_files.append(os.path.join(root, f))

        all_files = list(set(all_files))

        if log_callback: log_callback(f"[SYSTEM] Found {len(all_files)} total files. Beginning deep audit...")

        # Pass the callbacks to the batch processor
        ai_results = ai_deep_audit_batch(
            "Full Project",
            all_files,
            wolfgang,
            log_callback=log_callback,
            progress_callback=progress_callback
        )

        if log_callback: log_callback("[SYSTEM] Deep audit complete. Calculating final maturity scores...")

        from collections import defaultdict
        compliance_map = defaultdict(list)

        if isinstance(ai_results, list):
            for item in ai_results:
                compliance_type = item.get("compliance_type")
                if compliance_type:
                    compliance_map[compliance_type].append(item)

        final = {}

        for phase in PHASE_ORDER:
            phase_docs = COMPLIANCE_MATRIX.get(phase, [])
            phase_results = []

            for doc in phase_docs:
                qualities = compliance_map.get(doc, [])

                if not qualities:
                    phase_results.append({
                        "document": doc,
                        "quality": {},
                        "score": 0,
                        "pass": False,
                        "comment": "No document submitted for this compliance requirement."
                    })
                    continue

                best_score = -1
                best_quality = None

                for q in qualities:
                    score = 0
                    if q.get("appears_filled"): score += 30
                    if q.get("contains_project_content"): score += 30
                    if not q.get("appears_template_only"): score += 20
                    if q.get("document_type_correct"): score += 20

                    if score > best_score:
                        best_score = score
                        best_quality = q

                if best_quality is None:
                    best_quality = {}
                    best_score = 0

                comment = best_quality.get("comment", "")
                if not comment:
                    if best_score >= 70:
                        comment = "Document appears complete and compliant."
                    else:
                        comment = "Document incomplete, template-based, or incorrect type."

                phase_results.append({
                    "document": doc,
                    "quality": best_quality,
                    "score": best_score,
                    "pass": best_score >= 70,
                    "comment": comment
                })

            if phase_results:
                avg_score = round(sum(d["score"] for d in phase_results) / len(phase_results), 2)
            else:
                avg_score = 0

            final[phase] = {
                "documents": phase_results,
                "score": avg_score
            }

        detected_phase = PHASE_ORDER[0]
        for phase in PHASE_ORDER:
            if final.get(phase, {}).get("score", 0) >= 70:
                detected_phase = phase
            else:
                break

        active_phases = PHASE_ORDER[:PHASE_ORDER.index(detected_phase) + 1]

        if active_phases:
            overall_score = round(sum(final[p]["score"] for p in active_phases) / len(active_phases), 2)
        else:
            overall_score = 0

        if overall_score >= 85: risk = "🟢 Low Risk"
        elif overall_score >= 70: risk = "🟡 Moderate Risk"
        elif overall_score >= 50: risk = "🟠 High Risk"
        else: risk = "🔴 Critical Risk"

        executive_summary = (
            f"This project is currently assessed at the {detected_phase} phase "
            f"with an overall compliance score of {overall_score}%. "
            f"Risk level is classified as {risk}."
        )

        if log_callback: log_callback("[SYSTEM] Pipeline execution finished successfully.")

        return {
            "overall_score": overall_score,
            "detected_phase": detected_phase,
            "risk_level": risk,
            "executive_summary": executive_summary,
            "phases": final
        }

    finally:
        if log_callback: log_callback("[SYSTEM] Shutting down Wolfgang session...")
        wolfgang.close()