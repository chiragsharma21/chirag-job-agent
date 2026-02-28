"""
scorer/engine.py — Local AI Job Scorer (ZERO API COST)

Uses rule-based NLP + keyword matching against Chirag's profile.
No OpenAI, no Claude API, no Ollama required.
Scores 0–10 based on:
  - Role title match (3 pts)
  - Skill overlap (4 pts)
  - Experience level fit (2 pts)
  - Location match (1 pt)
"""
import re
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CANDIDATE, TARGET_ROLES, TARGET_LOCATIONS, EXPERIENCE_RANGE


# ── ROLE KEYWORD MAPPING ─────────────────────────────────────────
ROLE_KEYWORDS = {
    "Business Consultant":      ["business consultant", "management consultant", "strategy consultant"],
    "Business Analyst":         ["business analyst", "BA ", "systems analyst", "process analyst", "functional analyst"],
    "Product Manager":          ["product manager", "APM", "associate product manager", "PM ", "product owner"],
    "IT Sales / BD":            ["it sales", "business development", "bd executive", "sales executive",
                                 "pre-sales", "presales", "inside sales", "account executive", "bd manager"],
    "Project Manager":          ["project manager", "delivery manager", "program manager", "scrum master"],
    "Pre-Sales Consultant":     ["pre-sales", "presales", "solution consultant", "sales engineer"],
}

# Chirag's skills mapped to keyword variants for matching
SKILL_VARIANTS = {
    "BRD Writing":              ["brd", "business requirement", "requirement document", "business requirements"],
    "PRD Writing":              ["prd", "product requirement", "product document"],
    "Proposal Writing":         ["proposal", "pitch deck", "rfp", "bid document", "eoi"],
    "HubSpot CRM":              ["hubspot", "crm", "salesforce", "zoho crm", "customer relationship"],
    "LinkedIn Sales Navigator": ["linkedin", "sales navigator", "lead generation", "outreach"],
    "Figma":                    ["figma", "ui/ux", "prototyping", "wireframe", "mockup"],
    "Agile":                    ["agile", "scrum", "sprint", "kanban", "jira"],
    "Stakeholder Management":   ["stakeholder", "client management", "account management", "client facing"],
    "Market Research":          ["market research", "competitive analysis", "research"],
    "IT Staffing":              ["staffing", "c2c", "c2h", "recruitment", "talent acquisition"],
    "Documentation":            ["documentation", "technical writing", "user stories", "sow", "mou"],
    "Cross-functional":         ["cross-functional", "coordination", "collaboration", "team management"],
    "Excel":                    ["excel", "spreadsheet", "data analysis", "mis"],
    "Project Coordination":     ["project coordination", "delivery", "milestone", "timeline management"],
}

# Negative signals (roles or requirements that don't match Chirag's level)
NEGATIVE_SIGNALS = [
    "10+ years", "15 years", "senior director", "vp of", "vice president",
    "cto", "ceo", "chief ", "head of product", "phd required",
    "data science", "machine learning", "deep learning", "python developer",
    "java developer", "software engineer", "backend developer", "frontend developer",
    "full stack", "devops", "cloud engineer", "security engineer",
    "ca required", "chartered accountant", "mba required",
]

POSITIVE_SIGNALS = [
    "0-2 years", "1-3 years", "0-3 years", "fresher", "entry level",
    "junior", "associate", "assistant manager", "trainee",
    "1+ year", "1-2 years", "recent graduate",
]


def score_job(job: dict) -> dict:
    """
    Score a job against Chirag's profile.
    Returns a score dict with fit_score 0–10 and explanation.
    """
    title       = (job.get("title", "") or "").lower()
    description = (job.get("description", "") or "").lower()
    location    = (job.get("location", "") or "").lower()
    company     = (job.get("company", "") or "").lower()

    combined = f"{title} {description}"

    # ── 1. ROLE TITLE MATCH (0–3 pts) ───────────────────────────
    role_score = 0
    matched_role = "General"
    for role_name, keywords in ROLE_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in combined:
                role_score = 3
                matched_role = role_name
                break
        if role_score > 0:
            break

    # Partial match — any target role keyword in title
    if role_score == 0:
        for target in TARGET_ROLES:
            if any(word.lower() in title for word in target.split()):
                role_score = 1.5
                matched_role = target
                break

    # ── 2. SKILL OVERLAP (0–4 pts) ──────────────────────────────
    matched_skills = []
    missing_skills = []
    skill_score    = 0

    for skill_name, variants in SKILL_VARIANTS.items():
        found = any(v.lower() in combined for v in variants)
        if found:
            matched_skills.append(skill_name)

    skill_score = min(4, len(matched_skills) * 0.6)

    # Check for skills in JD that Chirag might be missing
    required_maybe_missing = []
    missing_indicators = [
        ("MBA", ["mba", "master of business", "post graduate"]),
        ("PMP Certification", ["pmp", "prince2", "project management certification"]),
        ("SQL / Data", ["sql", "power bi", "tableau", "data analytics"]),
        ("Python / Coding", ["python", "coding", "programming", "javascript"]),
        ("CA / Finance", ["ca ", "chartered accountant", "finance degree", "cfa"]),
    ]
    for skill_label, indicators in missing_indicators:
        if any(ind in combined for ind in indicators):
            required_maybe_missing.append(skill_label)

    # ── 3. EXPERIENCE LEVEL FIT (0–2 pts) ───────────────────────
    exp_score = 1.5  # default: assume OK

    # Negative: requires too much experience
    for neg in NEGATIVE_SIGNALS:
        if neg.lower() in combined:
            if "years" in neg or "year" in neg:
                exp_score = 0
            else:
                exp_score = max(0, exp_score - 0.5)

    # Positive: matches fresh/junior profile
    for pos in POSITIVE_SIGNALS:
        if pos.lower() in combined:
            exp_score = 2
            break

    # ── 4. LOCATION FIT (0–1 pt) ────────────────────────────────
    loc_score = 0
    for loc in TARGET_LOCATIONS:
        if loc.lower() in location:
            loc_score = 1
            break
    if "remote" in location or "work from home" in location or "wfh" in location:
        loc_score = 1

    # ── FINAL SCORE ─────────────────────────────────────────────
    raw_score    = role_score + skill_score + exp_score + loc_score
    fit_score    = round(min(10, raw_score))

    # Penalty for complete role mismatch
    if role_score == 0:
        fit_score = min(fit_score, 4)

    # ── ROLE MATCH LABEL ────────────────────────────────────────
    if fit_score >= 8:
        role_match = "High"
    elif fit_score >= 6:
        role_match = "Medium"
    else:
        role_match = "Low"

    # ── GENERATE HUMAN SUMMARY ──────────────────────────────────
    summary = _generate_summary(
        job["title"], fit_score, matched_role,
        matched_skills, required_maybe_missing, role_score, exp_score
    )

    # ── KEY REQUIREMENT ─────────────────────────────────────────
    key_req = _extract_key_requirement(description)

    return {
        "fit_score":       fit_score,
        "role_category":   matched_role,
        "role_match":      role_match,
        "matching_skills": matched_skills[:6],
        "missing_skills":  required_maybe_missing[:4],
        "key_requirement": key_req,
        "summary":         summary,
        # Debug breakdown
        "_breakdown": {
            "role_score": role_score,
            "skill_score": round(skill_score, 1),
            "exp_score": exp_score,
            "loc_score": loc_score,
        }
    }


def _generate_summary(title, score, matched_role, skills, missing, role_score, exp_score) -> str:
    """Generate a plain English 2-sentence summary."""
    if score >= 8:
        strength = f"Strong match — your {matched_role} background aligns well with this role."
    elif score >= 6:
        strength = f"Decent match — your consulting and {matched_role.lower()} experience is relevant here."
    else:
        strength = f"Partial match — the role overlaps with some of your skills but may not be ideal."

    if skills:
        skills_str = ", ".join(skills[:3])
        detail = f"Key overlapping skills: {skills_str}."
    else:
        detail = "Limited keyword overlap found in the job description."

    if missing:
        detail += f" Possible gaps: {', '.join(missing[:2])}."

    return f"{strength} {detail}"


def _extract_key_requirement(description: str) -> str:
    """Try to extract the primary requirement sentence."""
    sentences = re.split(r'[.!?]', description)
    key_words = ["required", "must have", "should have", "looking for", "ideal candidate",
                 "we need", "you will", "responsibilities", "experience in"]
    for sent in sentences:
        sent_lower = sent.lower().strip()
        if any(kw in sent_lower for kw in key_words) and len(sent.strip()) > 20:
            return sent.strip()[:150]
    # Fallback: first meaningful sentence
    for sent in sentences:
        if len(sent.strip()) > 30:
            return sent.strip()[:150]
    return ""


def batch_score(jobs: list[dict]) -> list[dict]:
    """Score a list of jobs. Returns jobs with score data attached."""
    scored = []
    for job in jobs:
        try:
            score_data = score_job(job)
            job.update(score_data)
            scored.append(job)
        except Exception as e:
            print(f"  [Scorer] Error scoring '{job.get('title')}': {e}")
    return scored


if __name__ == "__main__":
    # Test with sample job
    test_job = {
        "title": "Business Analyst - Digital Transformation",
        "company": "Deloitte India",
        "location": "Gurugram, Delhi NCR",
        "description": (
            "Looking for a Business Analyst with 1-3 years of experience. "
            "You will be responsible for BRD writing, stakeholder management, and "
            "collaborating with cross-functional teams. Experience with Agile/Scrum "
            "methodology required. HubSpot CRM knowledge is a plus. "
            "Strong communication and presentation skills needed."
        )
    }
    result = score_job(test_job)
    print(f"\n--- Score Result ---")
    print(f"Score:     {result['fit_score']}/10 ({result['role_match']})")
    print(f"Category:  {result['role_category']}")
    print(f"Matches:   {result['matching_skills']}")
    print(f"Missing:   {result['missing_skills']}")
    print(f"Summary:   {result['summary']}")
    print(f"Breakdown: {result['_breakdown']}")
