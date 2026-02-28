import os

CANDIDATE = {
    "name":            "Chirag Sharma",
    "email":           "ashu200221@gmail.com",
    "phone":           "+91-9821829084",
    "location":        "Ghaziabad, Delhi NCR",
    "experience":      1.5,
    "current_role":    "Associate Business Consultant",
    "current_company": "VAYUZ Technologies",
    "skills": [
        "Business Development", "IT Sales", "BRD Writing", "PRD Writing",
        "EOI Documentation", "Proposal Writing", "Pitch Decks",
        "HubSpot CRM", "Zoho CRM", "Salesforce",
        "LinkedIn Sales Navigator", "Lusha", "ContactOut", "Apollo.io",
        "Figma", "Miro", "Lucidchart", "Trello", "Asana", "Notion",
        "Agile", "Scrum", "Stakeholder Management", "User Flow Mapping",
        "Market Research", "Account Management", "Pre-sales Support",
        "C2C Staffing", "C2H Staffing", "Client Onboarding",
        "Cross-functional Coordination", "Excel", "Google Workspace",
    ],
    "achievements": [
        "Closed 10+ client accounts in app/web development and IT staffing",
        "Worked with clients in India and Middle East markets",
        "Led complete sales cycles from lead engagement to deal closure",
        "Managed post-sales, AMC discussions, cross-sell opportunities",
        "Created BRDs, PRDs, EOIs and pitch decks for 5+ product projects",
    ],
    "education": "B.Tech Computer Science, JIIT Noida, 2024 (CGPA 7.11)"
}

TARGET_ROLES = [
    "Business Consultant", "Business Analyst",
    "Product Manager", "IT Sales",
    "Business Development", "Associate Product Manager",
    "Project Manager", "Pre-Sales Consultant",
]

TARGET_LOCATIONS = ["Delhi", "Noida", "Gurugram", "Gurgaon", "Delhi NCR", "Remote"]
MIN_FIT_SCORE = 6

EMAIL_SENDER   = "ashu200221@gmail.com"
EMAIL_TO       = "ashu200221@gmail.com"
EMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD", "")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "data", "jobs.db")
LOG_PATH = os.path.join(BASE_DIR, "logs", "agent.log")
