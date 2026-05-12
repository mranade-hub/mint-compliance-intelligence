# compliance_matrix.py

MINT_MATRIX = {
    "Engage": {
        "Sales Project Blue Print / Hand Off Document - Sales to Sales": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"],
        "Services SOW": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"],
        "Pre-Kick Off Deck / Kick Off Deck": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"],
        "Kickoff Meeting Notes": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"],
        "RACI Document": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"]
    },
    "Design": {
        "Design Doc fully executed": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"],
        "Project Plan (Potentially has RACI in it)": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"],
        "IRD": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"],
        "Template Transaction Gap Analysis (Optional)": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"]
    },
    "Build": {
        "Project Status Report": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"],
        "Action Log and Comm Plan": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"]
    },
    "Execute": {
        "UAT Execution Tracker": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"],
        "Production Readiness Document": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"],
        "MINT Configuration Template": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"],
        "Integration Completion Certification": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"]
    },
    "Test": {
        "Internal Transition Document": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"],
        "MINT Project Completion Form": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"]
    }
}

SOLUTION_PARTNER_MATRIX = {
    "Engage": {
        "Kickoff Deck": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"],
        "Kickoff Meeting Notes": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"]
    },
    "Design": {
        "Statement of Work": ["New Project", "SubContracted Project", "Reseller Project"],
        "Design Doc fully executed with the same name as the signature (Includes IRD if Applicable)": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"]
    },
    "Execute": {
        "Change Order and Change Order Log (Conditional)": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"],
        "Fully executed Configuration spec": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"]
    },
    "Test": {
        "Integration Certificate (Conditional)": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"]
    },
    "Deploy": {},
    "Service": {
        "Transition to Support fully executed": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"]
    }
}

TT_MATRIX = {
    "Engage": {
        "Kickoff Deck": ["New Project", "SubContracted Project"],
        "Kickoff Meeting Notes": ["New Project", "SubContracted Project"],
        "Communication Plan, Action Log or Consolidated version": ["New Project", "Transitioned Project", "SubContracted Project"]
    },
    "Design": {
        "Project Plan": ["New Project", "Transitioned Project", "SubContracted Project"],
        "Design Doc fully executed with the same name as the signature (Includes IRD if Applicable)": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"],
        "Vendor Form": ["New Project", "Transitioned Project", "SubContracted Project"]
    },
    "Execute": {
        "Change Order and Change Order Log (Conditional)": ["New Project", "Transitioned Project", "SubContracted Project"],
        "Fully executed Configuration spec": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"],
        "Action Log": ["New Project", "Transitioned Project", "SubContracted Project"]
    },
    "Test": {
        "Integration Certificate (Conditional)": ["New Project", "Transitioned Project", "SubContracted Project"]
    },
    "Deploy": {
        "System Readiness fully executed": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"]
    },
    "Service": {
        "Transition to Support fully executed": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"],
        "Project Completion fully executed": ["New Project", "Transitioned Project", "SubContracted Project", "Reseller Project"]
    }
}

ALL_MATRICES = {
    "MINT": MINT_MATRIX,
    "Solution Partner": SOLUTION_PARTNER_MATRIX,
    "Track and Trace": TT_MATRIX
}
# Add this to the bottom of compliance_matrix.py for backward compatibility
# COMPLIANCE_MATRIX = MINT_MATRIX