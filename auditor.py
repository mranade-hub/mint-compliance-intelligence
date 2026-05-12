import os
import re
import json
from compliance_matrix import ALL_MATRICES

def safe_json_extract(text):
    if not text: return None
    
    array_match = re.search(r"\[.*\]", text, re.DOTALL)
    if array_match:
        try:
            parsed = json.loads(array_match.group(0))
            if isinstance(parsed, list): return parsed
        except: pass
        
    object_match = re.search(r"\{.*\}", text, re.DOTALL)
    if object_match:
        try:
            parsed = json.loads(object_match.group(0))
            if isinstance(parsed, dict): return parsed
        except: pass
        
    return None

def map_full_paths(parsed_data, original_batch):
    """Reattaches the exact system folder paths to the AI's output."""
    if not isinstance(parsed_data, list):
        parsed_data = [parsed_data] if isinstance(parsed_data, dict) else []
        
    for item in parsed_data:
        returned_path = str(item.get("file_path", ""))
        doc_name = str(item.get("document_name", ""))
        
        best_match = original_batch[0] if len(original_batch) == 1 else ""
        
        if not best_match:
            for full_path in original_batch:
                if returned_path and returned_path.lower() in full_path.lower():
                    best_match = full_path
                    break
                if doc_name and doc_name.lower() in full_path.lower():
                    best_match = full_path
                    break

        if best_match:
            item["file_path"] = best_match
            
    return parsed_data

def ai_deep_audit_batch(phase, file_paths, wolfgang, project_category="MINT", log_callback=None, progress_callback=None):
    if not file_paths: return []

    # FIX: Dynamically fetch ONLY the documents for the selected category
    COMPLIANCE_MATRIX = ALL_MATRICES.get(project_category, ALL_MATRICES.get("MINT", {}))
    
    VALID_DOCS = set()
    for p, docs in COMPLIANCE_MATRIX.items():
        for doc_name in docs.keys():
            VALID_DOCS.add(doc_name)
    
    valid_docs_formatted = "\n".join(f"- {d}" for d in VALID_DOCS)

    MAX_FILES = 4 
    results = []
    total_batches = (len(file_paths) + MAX_FILES - 1) // MAX_FILES

    if hasattr(wolfgang, 'clear_chat'): 
        wolfgang.clear_chat()

    for batch_idx, i in enumerate(range(0, len(file_paths), MAX_FILES)):
        batch = file_paths[i:i+MAX_FILES]
        batch_filenames = [os.path.basename(f) for f in batch]

        prompt = f"""
CRITICAL INSTRUCTION: Ignore all previous files and chat history. ONLY analyze the exact {len(batch)} NEW files just uploaded: 
{batch_filenames}

You MUST classify each file into ONE of the following exact 'compliance_type' categories. If it does not fit any, use "Unknown". Do not invent categories.

Valid Categories:
{valid_docs_formatted}
- Unknown

For EACH uploaded file:
1. Identify which valid compliance category it belongs to.
2. Evaluate quality fields.
3. Return the EXACT "file_path" or file name from the list above.

Return ONLY plain text JSON array. DO NOT use markdown.
[
  {{
    "file_path": "...",
    "document_name": "...",
    "compliance_type": "...",
    "appears_filled": true/false,
    "contains_project_content": true/false,
    "appears_template_only": true/false,
    "document_type_correct": true/false,
    "short_summary": "Provide a 1-sentence concise reason explaining document quality, missing data, or why it passed/failed."
  }}
]
"""
        
        if log_callback: log_callback(f"[WOLFGANG] Uploading Batch {batch_idx + 1}/{total_batches} ({len(batch)} files)...")

        wolfgang.upload_multiple(batch)
        response = wolfgang.send_prompt(prompt)
        parsed = safe_json_extract(response)

        if isinstance(parsed, list):
            parsed = map_full_paths(parsed, batch)
            results.extend(parsed)
            if log_callback: log_callback(f"[SUCCESS] Batch {batch_idx + 1} analyzed.")
        else:
            if log_callback: log_callback(f"[WARNING] Batch {batch_idx + 1} failed. Spawning new chat & retrying...")
            
            if hasattr(wolfgang, 'clear_chat'): 
                wolfgang.clear_chat() 
            
            wolfgang.upload_multiple(batch)
            response_retry = wolfgang.send_prompt(prompt)
            parsed_retry = safe_json_extract(response_retry)
            
            if isinstance(parsed_retry, list):
                parsed_retry = map_full_paths(parsed_retry, batch)
                results.extend(parsed_retry)
                if log_callback: log_callback(f"[SUCCESS] Batch {batch_idx + 1} analyzed after resetting chat memory.")
            else:
                if log_callback: log_callback(f"[WARNING] Batch {batch_idx + 1} failed again. Falling back to 1-by-1...")
                
                if hasattr(wolfgang, 'clear_chat'): 
                    wolfgang.clear_chat()

                for file_path in batch:
                    filename = os.path.basename(file_path)
                    if log_callback: log_callback(f"[WOLFGANG] Uploading single file fallback: {filename}...")
                    
                    wolfgang.upload_multiple([file_path])
                    single_prompt = prompt.replace(str(batch_filenames), f"['{filename}']")
                    parsed_single = safe_json_extract(wolfgang.send_prompt(single_prompt))
                    
                    parsed_single = map_full_paths(parsed_single, [file_path])
                    
                    if isinstance(parsed_single, list):
                        results.extend(parsed_single)
                    elif isinstance(parsed_single, dict):
                        results.append(parsed_single)
                    else:
                        if log_callback: log_callback(f"[ERROR] Single file {filename} failed. Skipping.")

        if progress_callback:
            progress_callback(batch_idx + 1, total_batches, f"Analyzing documents: Batch {batch_idx + 1} of {total_batches}")

    return results