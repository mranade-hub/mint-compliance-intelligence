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

        # ─── AGENT A: THE MAKER PROMPT ───
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
        response1 = wolfgang.send_prompt(prompt)
        parsed1 = safe_json_extract(response1)

        if isinstance(parsed1, list):
            parsed1 = map_full_paths(parsed1, batch)
            
            # ─── AGENT B: THE QA CHECKER ───
            if log_callback: log_callback(f"[QA AGENT] Verifying AI classification logic for Batch {batch_idx + 1}...")
            
            qa_prompt = f"""
You are a strict Quality Assurance auditor.
Review the following AI-generated document classifications against their actual physical filenames.

Filenames in this batch: {batch_filenames}
AI Classifications to review: {json.dumps(parsed1)}

Task: Check if the 'compliance_type' logically aligns with the filename. For example, a file named 'Kickoff_Notes' cannot be classified as a 'Statement of Work'.
Return ONLY a plain text JSON array adding 'qa_pass' (boolean) and 'qa_reason' (string explaining why it logically matches or fails). Do NOT use markdown.
[
  {{
    "file_path": "...",
    "qa_pass": true/false,
    "qa_reason": "..."
  }}
]
"""
            if hasattr(wolfgang, 'clear_chat'): wolfgang.clear_chat()
            
            # Send QA prompt purely as text evaluation (no files needed for metadata check)
            qa_response = wolfgang.send_prompt(qa_prompt)
            qa_parsed = safe_json_extract(qa_response)
            
            has_errors = False
            failed_items = []
            
            if isinstance(qa_parsed, list):
                for item in qa_parsed:
                    if not item.get("qa_pass", True):
                        has_errors = True
                        failed_items.append(item)
                        
            # ─── SELF-CORRECTION LOOP ───
            if has_errors:
                if log_callback: log_callback(f"[QA FLAG] AI Misclassifications detected. Forcing Self-Correction loop...")
                
                correction_prompt = prompt + f"\n\nCRITICAL QA FEEDBACK: Your previous classification had errors. Review the files again and fix them based on this QA feedback:\n{json.dumps(failed_items)}\n\nReturn the fully corrected JSON array in the exact format requested."
                
                if hasattr(wolfgang, 'clear_chat'): wolfgang.clear_chat()
                wolfgang.upload_multiple(batch) # Re-upload files for the correction pass
                response2 = wolfgang.send_prompt(correction_prompt)
                parsed2 = safe_json_extract(response2)
                
                if isinstance(parsed2, list):
                    parsed2 = map_full_paths(parsed2, batch)
                    results.extend(parsed2)
                    if log_callback: log_callback(f"[SUCCESS] Batch {batch_idx + 1} successfully self-corrected.")
                else:
                    results.extend(parsed1) # Fallback to original if correction JSON breaks
                    if log_callback: log_callback(f"[WARNING] Self-correction parsing failed. Using original results.")
            else:
                results.extend(parsed1)
                if log_callback: log_callback(f"[SUCCESS] Batch {batch_idx + 1} passed QA verification flawlessly.")
                
        else:
            # ─── TOTAL FAILURE FALLBACK (1-by-1) ───
            if log_callback: log_callback(f"[WARNING] Batch {batch_idx + 1} completely failed formatting. Falling back to 1-by-1 processing...")
            
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