import os
import re
import json
from compliance_matrix import COMPLIANCE_MATRIX


def safe_json_extract(text):
    if not text:
        return None

    import re
    import json

    text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text)

    array_matches = re.findall(r"\[[\s\S]*?\]", text)
    for match in array_matches:
        try:
            parsed = json.loads(match)
            if isinstance(parsed, list):
                return parsed
        except:
            continue

    object_matches = re.findall(r"\{[\s\S]*?\}", text)
    for match in object_matches:
        try:
            parsed = json.loads(match)
            if isinstance(parsed, dict):
                return parsed
        except:
            continue

    return None


def ai_structure_validation(structure_text, project_type, wolfgang):

    expected_format = {
        phase: {doc: "FOUND/MISSING" for doc in docs}
        for phase, docs in COMPLIANCE_MATRIX.items()
    }

    prompt = f"""
Return ONLY valid JSON.
No explanation.
No markdown.
No code fences.

Format EXACTLY like this:
{json.dumps(expected_format, indent=2)}

Folder Structure:
{structure_text}
"""

    response = wolfgang.send_prompt(prompt)
    parsed = safe_json_extract(response)

    if isinstance(parsed, dict):
        return parsed

    fallback = {}
    lower_structure = structure_text.lower()

    for phase, docs in COMPLIANCE_MATRIX.items():
        fallback[phase] = {}
        for doc in docs:
            keyword = doc.split()[0].lower()
            fallback[phase][doc] = (
                "FOUND" if keyword in lower_structure else "MISSING"
            )

    return fallback


def ai_deep_audit_batch(phase, file_paths, wolfgang, log_callback=None, progress_callback=None):

    if not file_paths:
        return []

    MAX_FILES = 4 # Reduced from 5 to lessen LLM output truncation
    results = []
    
    total_batches = (len(file_paths) + MAX_FILES - 1) // MAX_FILES

    prompt = """
You are auditing MINT compliance documents.
For EACH uploaded file:
1. Identify which compliance document type it belongs to (must match EXACT name from compliance matrix).
2. Evaluate quality fields.
Return ONLY a valid JSON array of objects. Do not truncate the output.
[
  {
    "document_name": "...",
    "compliance_type": "...",
    "appears_filled": true/false,
    "contains_project_content": true/false,
    "appears_template_only": true/false,
    "document_type_correct": true/false
  }
]
"""

    for batch_idx, i in enumerate(range(0, len(file_paths), MAX_FILES)):
        batch = file_paths[i:i+MAX_FILES]

        # WIPE MEMORY: Prevent context window from blowing up on large folders
        if hasattr(wolfgang, 'clear_chat'):
            wolfgang.clear_chat()

        if log_callback:
            log_callback(f"[WOLFGANG] Uploading Batch {batch_idx + 1}/{total_batches} ({len(batch)} files)...")

        # --- ATTEMPT 1: FULL BATCH ---
        wolfgang.upload_multiple(batch)
        response = wolfgang.send_prompt(prompt)
        parsed = safe_json_extract(response)

        if isinstance(parsed, list):
            results.extend(parsed)
            if log_callback:
                log_callback(f"[SUCCESS] Batch {batch_idx + 1} analyzed. Extracted {len(parsed)} evaluations.")
        else:
            if log_callback:
                log_callback(f"[WARNING] Batch {batch_idx + 1} failed JSON extraction. Files may be too large. Falling back to 1-by-1 processing...")

            # --- ATTEMPT 2: DYNAMIC FALLBACK (ONE BY ONE) ---
            for file_path in batch:
                if hasattr(wolfgang, 'clear_chat'):
                    wolfgang.clear_chat() # Wipe memory for each large file
                
                filename = os.path.basename(file_path)
                if log_callback:
                    log_callback(f"[WOLFGANG] Uploading single file fallback: {filename}...")
                
                wolfgang.upload_multiple([file_path])
                response_single = wolfgang.send_prompt(prompt)
                parsed_single = safe_json_extract(response_single)
                
                # Single file might return a list [ {dict} ] or just a {dict}
                if isinstance(parsed_single, list):
                    results.extend(parsed_single)
                    if log_callback: log_callback(f"[SUCCESS] Isolated file '{filename}' analyzed.")
                elif isinstance(parsed_single, dict):
                    results.append(parsed_single)
                    if log_callback: log_callback(f"[SUCCESS] Isolated file '{filename}' analyzed.")
                else:
                    if log_callback: log_callback(f"[FATAL] Isolated file '{filename}' failed. Unreadable or corrupted. Skipping.")

        # Update the UI progress bar after the batch completes (or completely fails)
        if progress_callback:
            progress_callback(batch_idx + 1, total_batches, f"Analyzing documents: Batch {batch_idx + 1} of {total_batches}")

    return results