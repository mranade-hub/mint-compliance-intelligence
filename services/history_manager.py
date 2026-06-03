import os
import json
import datetime
from services.sheets_db import load_company_history

def save_audit_history(company, results):
    os.makedirs("audit_history", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results["audit_timestamp"] = timestamp
    with open(f"audit_history/{company}_{timestamp}.json", "w") as f:
        json.dump(results, f)

def get_last_audit_rfc3339(company):
    """Fetches the latest audit timestamp and formats it correctly for Google Drive UTC comparison."""
    history = load_company_history(company)
    if not history:
        return None
    
    last_audit = history[0]
    ts_str = last_audit.get("audit_timestamp")

    try:
        dt = datetime.datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
        dt_aware = dt.astimezone()
        dt_utc = dt_aware.astimezone(datetime.timezone.utc)
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except Exception:
        return None
    
def merge_incremental_results(old_results, new_results):
    """Blends the newly audited files into the historical master report."""
    merged = old_results.copy()
    
    if "project_category" in new_results:
        merged["project_category"] = new_results["project_category"]
    
    for phase, new_phase_data in new_results.get("phases", {}).items():
        if phase not in merged["phases"]:
            merged["phases"][phase] = new_phase_data
            continue
        
        existing_docs = {d["document"]: i for i, d in enumerate(merged["phases"][phase]["documents"])}
        
        for new_doc in new_phase_data["documents"]:
            if new_doc.get("actual_folder") != "N/A" or new_doc.get("is_bypassed"):
                if new_doc["document"] in existing_docs:
                    idx = existing_docs[new_doc["document"]]
                    merged["phases"][phase]["documents"][idx] = new_doc
                else:
                    merged["phases"][phase]["documents"].append(new_doc)
        
        valid_docs = [d["score"] for d in merged["phases"][phase]["documents"] if not d.get("is_bypassed", False)]
        merged["phases"][phase]["score"] = round(sum(valid_docs) / len(valid_docs), 2) if valid_docs else 100

    valid_phase_scores = [merged["phases"][p]["score"] for p in merged["phases"]]
    merged["overall_score"] = round(sum(valid_phase_scores) / len(valid_phase_scores), 2) if valid_phase_scores else 0
    
    score = merged["overall_score"]
    merged["risk_level"] = "🟢 Low Risk" if score >= 85 else "🟡 Moderate Risk" if score >= 70 else "🟠 High Risk" if score >= 50 else "🔴 Critical Risk"
    
    return merged