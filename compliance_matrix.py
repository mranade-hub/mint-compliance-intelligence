# compliance_matrix.py

# Maps phases to documents, and lists which Project Types require them.
COMPLIANCE_MATRIX = {
    "Manage": {
        "Project Status Report": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"],
        "Communication Plan": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"],
        "Hand off Document Sales to Services": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"],
        "Services SOW": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"]
    },
    "Engage": {
        "Project Plan": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"],
        "Project kick off Presentation": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"]
    },
    "Design": {
        "Solution Design Document": ["New Project", "Transitioned Project", "Subcontracted Project"],
        "Solution Design sign off email": ["New Project", "Transitioned Project", "Subcontracted Project"],
        "Requirements Traceability Matrix": ["New Project", "Transitioned Project", "Subcontracted Project"],
        "Integration Specification Document": ["New Project", "Transitioned Project"],
        "Integration Specification sign off email": ["New Project", "Transitioned Project"],
        "Migration Specification Document": ["New Project", "Transitioned Project"],
        "Migration Specification sign off email": ["New Project", "Transitioned Project"],
        "Validation Plan": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"]
    },
    "Build": {
        "Build Specification": ["New Project", "Transitioned Project", "Subcontracted Project"],
        "System Test Plan": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"],
        "Test Scripts": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"],
        "Test Results": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"],
        "System Test Summary Report": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"],
        "Deployment Plan": ["New Project", "Transitioned Project", "Subcontracted Project"],
        "Solution hand off Demo sign off email": ["New Project", "Transitioned Project", "Subcontracted Project"]
    },
    "Partner OnBoarding": {
        "Onboarding Kickoff Presentation": ["New Project", "Transitioned Project"],
        "Partner Information collection": ["New Project", "Transitioned Project"],
        "Welcome Pack to Partners": ["New Project", "Transitioned Project"],
        "Partner Go-Live Email": ["New Project", "Transitioned Project"]
    },
    "Validation": {
        "Validation Summary Report": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"],
        "UAT Test Plan": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"],
        "UAT Test Scripts": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"],
        "UAT Test Results": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"],
        "UAT Sign Off Email": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"],
        "Traceability Matrix validation": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"],
        "Configuration specification": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"]
    },
    "Closure": {
        "Go Live Cutover Plan": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"],
        "Go Live / Deployment Email to Customer": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"],
        "Project Closure Report / Post Go Live Check List": ["New Project", "Transitioned Project", "Subcontracted Project", "Reseller Project"]
    }
}