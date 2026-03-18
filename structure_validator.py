import os
import re
from compliance_matrix import COMPLIANCE_MATRIX


def normalize(text):
    return re.sub(r'[^a-zA-Z0-9]', '', text.lower())


def find_match(doc_name, files):
    doc_clean = normalize(doc_name)

    for f in files:
        file_clean = normalize(os.path.basename(f))
        if all(word in file_clean for word in doc_clean.split()):
            return f
    return None


def validate_structure(grouped_files, project_type):
    """
    Returns structure validation results before AI check.
    """
    structure_results = {}

    for phase, files in grouped_files.items():
        phase_results = []
        matrix = COMPLIANCE_MATRIX.get(phase, {})

        for doc_name, rule in matrix.items():
            matched = find_match(doc_name, files)
            signature_required = project_type in rule.get("R", [])

            if not matched:
                phase_results.append({
                    "document": doc_name,
                    "status": "MISSING",
                    "signature_required": signature_required,
                    "file_path": None
                })
            else:
                phase_results.append({
                    "document": doc_name,
                    "status": "FOUND",
                    "signature_required": signature_required,
                    "file_path": matched
                })

        structure_results[phase] = phase_results

    return structure_results