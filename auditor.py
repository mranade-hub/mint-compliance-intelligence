import re
import json
from compliance_matrix import COMPLIANCE_MATRIX


def safe_json_extract(text):
    """
    Robust JSON extractor.
    Handles:
    - Markdown fences
    - 'Retrieved XX sources' text
    - Multiple JSON blocks
    - Arrays or single objects
    """

    if not text:
        return None

    import re
    import json

    # Remove markdown fences
    text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text)

    # ✅ Try extracting JSON array first
    array_matches = re.findall(r"\[[\s\S]*?\]", text)
    for match in array_matches:
        try:
            parsed = json.loads(match)
            if isinstance(parsed, list):
                return parsed
        except:
            continue

    # ✅ Try extracting JSON object
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

    # fallback keyword detection
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


def ai_deep_audit_batch(phase, file_paths, wolfgang):

    if not file_paths:
        return {}

    MAX_FILES = 5
    results = []

    for i in range(0, len(file_paths), MAX_FILES):

        batch = file_paths[i:i+MAX_FILES]

        wolfgang.upload_multiple(batch)

        prompt = f"""
You are auditing MINT compliance documents.

For EACH uploaded file:

1. Identify which compliance document type it belongs to 
   (must match EXACT name from compliance matrix).
2. Evaluate quality fields.

Return ONLY JSON array:

[
  {{
    "document_name": "...",
    "compliance_type": "...",
    "appears_filled": true/false,
    "contains_project_content": true/false,
    "appears_template_only": true/false,
    "document_type_correct": true/false
  }}
]
"""

        response = wolfgang.send_prompt(prompt)
        parsed = safe_json_extract(response)

        if isinstance(parsed, list):
            results.extend(parsed)

    return results