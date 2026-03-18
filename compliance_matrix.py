PROJECT_TYPES = [
    "New Project",
    "Transitioned Project",
    "SubContracted Project",
    "Reseller Project"
]

# ============================
# REQUIRED DOCUMENTS PER PHASE
# ============================

COMPLIANCE_MATRIX = {
    "Management": [
        "Project Plan",
        "Action Log",
        "Project Status Report",
        "Communication Plan"
    ],
    "Engage": [
        "Sales - Project Blue Print",
        "Hand Off Document - Sales to Services",
        "Services - SOW",
        "Pre-Kick Off Deck",
        "Kickoff Deck",
        "Kickoff Meeting Notes",
        "RACI Document"
    ],
    "Design": [
        "Design Doc fully executed",
        "Project Plan",
        "IRD",
        "Gap Analysis Transaction (If needed)"
    ],
    "Build": [
        "Configuration Documents",
        "Action Log",
        "Project Status Report"
    ],
    "Partner OnBoarding": [
        "On Boarding Kick Off Deck",
        "On Boarding Process",
        "Partner Onboarding Status"
    ],
    "Validation": [
        "UAT Execution Tracker",
        "MINT Configuration Template",
        "Integration Completion Certification"
    ],
    "Closure": [
        "Internal Transtion Document",
        "MINT Project Completion Form"
    ]
}

# ====================================
# REQUIRED (R) AND CONDITIONAL (C) MAP
# ====================================

REQUIREMENT_RULES = {
    "Kickoff Deck": ["New Project", "Transitioned Project"],
    "Kickoff Meeting Notes": ["New Project", "Transitioned Project"],
    "RACI Document": ["New Project", "Transitioned Project"],
    "Design Doc fully executed": PROJECT_TYPES,
    "Project Plan": ["New Project", "Transitioned Project", "SubContracted Project"],
    "IRD": ["New Project", "Transitioned Project", "SubContracted Project"],
    "Action Log": ["New Project", "Transitioned Project", "SubContracted Project"],
    "Project Status Report": PROJECT_TYPES,
    "Communication Plan": ["New Project", "Transitioned Project", "SubContracted Project"],
    "Configuration Documents": ["New Project", "Transitioned Project", "SubContracted Project"],
    "On Boarding Kick Off Deck": ["New Project", "Transitioned Project", "SubContracted Project"],
    "On Boarding Process": PROJECT_TYPES,
    "UAT Execution Tracker": ["New Project", "Transitioned Project", "SubContracted Project"],
    "MINT Configuration Template": ["New Project", "Transitioned Project", "SubContracted Project"],
    "Integration Completion Certification": PROJECT_TYPES,
    "MINT Project Completion Form": PROJECT_TYPES
}

# ====================================
# CONDITIONAL DOCUMENTS (C)
# ====================================

CONDITIONAL_DOCS = {
    "Internal Transtion Document": ["New Project", "Transitioned Project", "SubContracted Project"]
}