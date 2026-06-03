import re

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

def top_gaps(results):
    gaps = []
    for phase, info in results.get("phases", {}).items():
        for d in info.get("documents", []):
            if not d.get("pass") and "N/A" not in d.get("comment", ""):
                gaps.append((phase, d["document"], d.get("score", 0), False, d.get("actual_folder", "N/A")))
            elif d.get("wrong_folder"):
                gaps.append((phase, d["document"], d.get("score", 0), True, d.get("actual_folder", "N/A")))
    return sorted(gaps, key=lambda x: x[2])[:6]