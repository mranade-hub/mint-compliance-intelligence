# compliance_matrix.py

# Maps phases to documents, and lists which Project Types require (R) or conditionally require (C) them.
COMPLIANCE_MATRIX = {
    "Engage": {
        "Sales - Project Blue Print / Hand Off Document - Sales to Sales": {"New Project": "R", "Transitioned Project": "R", "SubContracted Project": "R", "Reseller Project": "R"},
        "Services - SOW": {"New Project": "R", "Transitioned Project": "R", "SubContracted Project": "R", "Reseller Project": "R"},
        "Pre-Kick Off Deck": {"New Project": "R", "Transitioned Project": "R", "SubContracted Project": "R", "Reseller Project": "R"},
        "Kickoff Deck": {"New Project": "R", "Transitioned Project": "R", "SubContracted Project": "R", "Reseller Project": "R"},
        "Kickoff Meeting Notes": {"New Project": "R", "Transitioned Project": "R", "SubContracted Project": "R", "Reseller Project": "R"},
        "RACI Document": {"New Project": "R", "Transitioned Project": "R", "SubContracted Project": "R", "Reseller Project": "R"}
    },
    "Design": {
        "Design Doc fully executed": {"New Project": "R", "Transitioned Project": "R", "SubContracted Project": "R", "Reseller Project": "C"},
        "Project Plan": {"New Project": "R", "Transitioned Project": "R", "SubContracted Project": "R", "Reseller Project": "R"},
        "IRD": {"New Project": "R", "Transitioned Project": "R", "SubContracted Project": "C", "Reseller Project": "C"},
        "Template Transaction Gap Analysis (Optional)": {"New Project": "C", "Transitioned Project": "C", "SubContracted Project": "C", "Reseller Project": "C"}
    },
    "Build": {
        "Action Log": {"New Project": "R", "Transitioned Project": "R", "SubContracted Project": "R", "Reseller Project": "R"},
        "Project Status Report": {"New Project": "R", "Transitioned Project": "R", "SubContracted Project": "R", "Reseller Project": "R"},
        "Communication Plan (Engage), Action Log (Execute) or the newer Consolidated version (Execute)": {"New Project": "R", "Transitioned Project": "R", "SubContracted Project": "R", "Reseller Project": "R"}
    },
    "Partner OnBoarding": {
        "On Boarding Kick Off Deck": {"Reseller Project": "R"},
        "On Boarding Process": {"Reseller Project": "R"},
        "Partner Onboarding Status": {"Reseller Project": "R"}
    },
    "Execute": {
        "UAT Execution Tracker": {"New Project": "R", "Transitioned Project": "R", "SubContracted Project": "R", "Reseller Project": "R"},
        "MINT Configuration Template": {"New Project": "R", "Transitioned Project": "R", "SubContracted Project": "R", "Reseller Project": "R"},
        "Integration Completion Certification": {"New Project": "R", "Transitioned Project": "R", "SubContracted Project": "C", "Reseller Project": "C"}
    },
    "Test": {
        "Internal Transition Document": {"New Project": "R", "Transitioned Project": "R", "SubContracted Project": "R", "Reseller Project": "R"},
        "MINT Project Completion Form": {"New Project": "R", "Transitioned Project": "R", "SubContracted Project": "R", "Reseller Project": "R"}
    }
}