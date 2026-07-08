import re
import os
import spacy
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

_models: dict = {}
_RESOURCES = Path(__file__).parent.parent.parent / "resources"


def _load(key: str, path: str):
    if key not in _models:
        _models[key] = spacy.load(path)
    return _models[key]

def get_model1():
    return _load("model1", os.getenv("MODEL1_PATH"))

def get_model2():
    return _load("model2", os.getenv("MODEL2_PATH"))

def get_skills_nlp():
    if "skills" not in _models:
        nlp = spacy.load("en_core_web_sm")
        ruler = nlp.add_pipe("entity_ruler", before="ner")
        ruler.from_disk(str(_RESOURCES / "skills.jsonl"))
        _models["skills"] = nlp
    return _models["skills"]


def run_ner(text: str, nlp) -> dict:
    """Run NER and return a dict of {LABEL: [span_text, ...]}."""
    doc = nlp(text)
    result = defaultdict(list)
    for ent in doc.ents:
        result[ent.label_.upper()].append(ent.text)
    return dict(result)


def run_skills_ner(text: str) -> dict:
    """
    SpaCy en_core_web_sm + EntityRuler (skills.jsonl) NER.
    Extracts: SKILLS (pattern-matched), NAME (PERSON), COMPANIES (ORG),
    LOCATIONS (GPE), EMAIL and PHONE via regex.
    """
    nlp = get_skills_nlp()
    doc = nlp(text)

    skills, names, companies, locations = [], [], [], []
    seen: set = set()
    for ent in doc.ents:
        val = ent.text.strip()
        key = (ent.label_, val.lower())
        if key in seen:
            continue
        seen.add(key)
        if ent.label_ == "SKILL":
            skills.append(val)
        elif ent.label_ == "PERSON":
            names.append(val)
        elif ent.label_ == "ORG":
            companies.append(val)
        elif ent.label_ == "GPE":
            locations.append(val)

    emails = list(dict.fromkeys(
        re.findall(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b", text)
    ))
    phones = list(dict.fromkeys(
        re.findall(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}\b", text)
    ))

    result = {}
    if names:     result["NAME"]      = names
    if emails:    result["EMAIL"]     = emails
    if phones:    result["PHONE"]     = phones
    if skills:    result["SKILLS"]    = skills
    if companies: result["COMPANIES"] = companies
    if locations: result["LOCATIONS"] = locations
    return result


# Per-label routing: use whichever model scores higher on each label.
# Populated from meta.json F1 scores; update if you retrain.
_LABEL_WINNER = {
    "ADDRESS":        "model1",
    "CERTIFICATIONS": "model1",
    "COLLEGENAME":    "model1",
    "COMPANIES":      "model1",
    "DESIGNATION":    "model1",
    "EDUCATION":      "model1",
    "EMAIL":          "model1",
    "EXPERIENCE":     "model1",
    "LINKS":          "model1",
    "LOCATION":       "model1",
    "NAME":           "model1",
    "PHONE":          "model1",
    "PROJECTS":       "model1",
    "REWARDS":        "model1",
    "SKILLS":         "model1",
    "TECHNOLOGY":     "model1",
}

def merge_ner(ner1: dict, ner2: dict) -> dict:
    """Return per-label best result based on routing table."""
    all_labels = set(ner1) | set(ner2)
    merged = {}
    for label in all_labels:
        winner = _LABEL_WINNER.get(label, "model1")
        source = ner1 if winner == "model1" else ner2
        if label in source:
            merged[label] = source[label]
        else:
            fallback = ner2 if winner == "model1" else ner1
            if label in fallback:
                merged[label] = fallback[label]
    return merged


import datetime

MONTHS_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12
}

def clean_experience_text(text: str) -> str:
    lines = text.split('\n')
    experience_lines = []
    in_education = False
    
    edu_headers = ["education", "academic", "study", "studies", "university", "degree", "qualification", "school"]
    exp_headers = ["experience", "employment", "work history", "professional background", "career history", "projects", "work experience"]
    
    for line in lines:
        line_clean = line.strip().lower()
        if len(line_clean) < 60:
            is_edu_header = False
            for eh in edu_headers:
                if eh in line_clean and any(sep in line_clean or line_clean == eh for sep in ["", ":", " -", "—"]):
                    is_edu_header = True
                    break
            
            is_exp_header = False
            for ex in exp_headers:
                if ex in line_clean and any(sep in line_clean or line_clean == ex for sep in ["", ":", " -", "—"]):
                    is_exp_header = True
                    break
            
            if is_edu_header:
                in_education = True
                continue
            if is_exp_header:
                in_education = False
                continue
                
        if not in_education:
            experience_lines.append(line)
            
    return "\n".join(experience_lines)

def parse_single_date(date_str: str, default_month: int = 1) -> float:
    if not date_str:
        return 0.0
    date_str = date_str.strip().lower()
    if date_str in ("present", "current", "now"):
        now = datetime.datetime.now()
        return now.year + (now.month - 1) / 12.0
    
    # Try to find year
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", date_str)
    if not year_match:
        return 0.0
    year = int(year_match.group(1))
    
    # Try to find month
    month = default_month
    for m_name, m_val in MONTHS_MAP.items():
        if m_name in date_str:
            month = m_val
            break
    else:
        digit_match = re.search(r"\b(0?[1-9]|1[0-2])\b", date_str.replace(year_match.group(1), ""))
        if digit_match:
            month = int(digit_match.group(1))
            
    return year + (month - 1) / 12.0

def estimate_experience_and_seniority(text: str) -> tuple[float, str]:
    if not text:
        return 0.0, "Junior"
        
    text_clean = clean_experience_text(text)
    
    # 1. Explicit years mention
    exp_patterns = [
        r"(\d+(?:\.\d+)?)\s*(?:\+|plus)?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp|work|relevant)?\b",
        r"(?:experience|exp):\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)?"
    ]
    explicit_years = 0.0
    for pattern in exp_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            try:
                val = float(m)
                if val > explicit_years and val <= 50:
                    explicit_years = val
            except ValueError:
                pass
                
    # 2. Year/Month ranges
    current_date = datetime.datetime.now()
    current_year = current_date.year
    current_month = current_date.month
    current_val = current_year + (current_month - 1) / 12.0
    
    month_regex = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|\d{1,2})"
    range_pattern = rf"((?:{month_regex}[\s,./\\]+)?\b(?:19\d{{2}}|20\d{{2}})\b)\s*(?:-|–|—|to)\s*((?:{month_regex}[\s,./\\]+)?\b(?:19\d{{2}}|20\d{{2}})\b|present|current|now)"
    
    intervals = []
    for match in re.finditer(range_pattern, text_clean, re.IGNORECASE):
        start_str = match.group(1)
        end_str = match.group(2)
        
        start_val = parse_single_date(start_str, default_month=1)
        end_val = parse_single_date(end_str, default_month=12)
        
        if 0.0 < start_val <= end_val and (current_val - start_val) <= 50:
            intervals.append((start_val, end_val))
            
    # Sort and merge intervals
    intervals.sort(key=lambda x: x[0])
    merged = []
    for start, end in intervals:
        if not merged or merged[-1][1] < start:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            
    range_years = sum(end - start for start, end in merged)
    estimated_years = max(explicit_years, range_years)
    estimated_years = round(estimated_years, 1)
    
    # Classify seniority
    text_lower = text.lower()
    executive_kws = ["director", "vp", "vice president", "chief", "cto", "cio", "ceo", "cfo", "head of"]
    lead_kws = ["lead", "principal", "manager", "architect"]
    senior_kws = ["senior", "sr.", "sr"]
    junior_kws = ["junior", "jr.", "jr", "entry", "intern", "associate"]
    
    has_exec = any(kw in text_lower for kw in executive_kws)
    has_lead = any(kw in text_lower for kw in lead_kws)
    has_senior = any(kw in text_lower for kw in senior_kws)
    has_junior = any(kw in text_lower for kw in junior_kws)
    
    if estimated_years >= 10:
        if has_exec:
            seniority = "Executive"
        elif has_lead:
            seniority = "Lead / Principal"
        else:
            seniority = "Senior"
    elif estimated_years >= 5:
        if has_exec:
            seniority = "Executive"
        elif has_lead:
            seniority = "Lead / Principal"
        else:
            seniority = "Senior"
    elif estimated_years >= 2:
        if has_lead:
            seniority = "Lead / Principal"
        elif has_junior and not has_senior:
            seniority = "Junior"
        else:
            seniority = "Mid-level"
    else:
        if has_senior:
            seniority = "Senior"
        else:
            seniority = "Junior"
            
    return estimated_years, seniority

