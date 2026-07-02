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
