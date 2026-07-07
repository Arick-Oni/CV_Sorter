import re
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from . import ner as ner_service

_nlp = None

def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])
    return _nlp

def _clean_for_tfidf(text: str) -> str:
    from spacy.lang.en.stop_words import STOP_WORDS
    cleaned = re.sub(r"[.,\-|•]", " ", text or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    nlp = _get_nlp()
    doc = nlp(cleaned)
    return " ".join(
        token.lemma_.lower().strip()
        for token in doc
        if token.text not in STOP_WORDS and token.pos_ not in ("PUNCT", "SYM", "SPACE")
    )

def _rank_tfidf(jd_text: str, cvs: list) -> list:
    """Rank CVs against a job description using TF-IDF cosine similarity."""
    jd_clean = _clean_for_tfidf(jd_text)
    cv_cleans = [_clean_for_tfidf(cv.get("raw_text") or "") for cv in cvs]

    vectorizer = TfidfVectorizer()
    tfidf = vectorizer.fit_transform([jd_clean] + cv_cleans)
    sims = cosine_similarity(tfidf[0:1], tfidf[1:])[0]

    results = []
    for cv, score in zip(cvs, sims):
        results.append({**cv, "match_score": round(float(score) * 100, 2)})
    return results


def _flatten_ner_keywords(ner: dict) -> set:
    """All entity strings across all labels, normalised for exact-match comparison."""
    keywords = set()
    for vals in (ner or {}).values():
        for v in (vals if isinstance(vals, list) else [vals]):
            norm = str(v).strip().lower()
            if norm:
                keywords.add(norm)
    return keywords


def _ner_keyword_score(jd_ner: dict, cv_ner: dict) -> float:
    """% of the JD's NER keywords that also appear in the CV's NER output."""
    jd_keywords = _flatten_ner_keywords(jd_ner)
    if not jd_keywords:
        return 0.0
    cv_keywords = _flatten_ner_keywords(cv_ner)
    matched = sum(1 for kw in jd_keywords if kw in cv_keywords)
    return (matched / len(jd_keywords)) * 100


EMBEDDING_WEIGHT = 2 / 3
KEYWORD_WEIGHT = 1 / 3

# method -> (nlp loader, CV dict field holding that model's precomputed NER, hybrid?)
_METHOD_CONFIG = {
    "model1":        (ner_service.get_model1, "ner_model1", False),
    "model2":        (ner_service.get_model2, "ner_model2", False),
    "model1_hybrid": (ner_service.get_model1, "ner_model1", True),
    "model2_hybrid": (ner_service.get_model2, "ner_model2", True),
}


def _rank_model(jd_text: str, cvs: list, loader, ner_field: str, hybrid: bool) -> list:
    """
    Rank CVs using a spaCy model's doc.vector cosine similarity, optionally blended
    with an NER-keyword-overlap score: 2/3 embedding + 1/3 keyword match.
    """
    nlp = loader()
    jd_text = jd_text or ""
    jd_vec = nlp(jd_text).vector.reshape(1, -1)
    cv_vecs = [nlp(cv.get("raw_text") or "").vector for cv in cvs]

    results = []
    if not cv_vecs:
        return results

    embed_sims = cosine_similarity(jd_vec, cv_vecs)[0]
    jd_ner = ner_service.run_ner(jd_text, nlp) if hybrid else None

    for cv, embed_sim in zip(cvs, embed_sims):
        embed_score = float(embed_sim) * 100
        if hybrid:
            keyword_score = _ner_keyword_score(jd_ner, cv.get(ner_field) or {})
            score = EMBEDDING_WEIGHT * embed_score + KEYWORD_WEIGHT * keyword_score
            results.append({
                **cv,
                "match_score": round(score, 2),
                "embedding_score": round(embed_score, 2),
                "keyword_score": round(keyword_score, 2),
            })
        else:
            results.append({**cv, "match_score": round(embed_score, 2)})
    return results


def rank_cvs(jd_text: str, cvs: list, method: str = "tfidf") -> list:
    """
    Rank CVs against a job description.
    method: "tfidf" (default); "model1" / "model2" (pure doc.vector embedding
    similarity — model1's vectors are a tok2vec fallback, see vector_showcase.ipynb,
    not recommended on their own); "model1_hybrid" / "model2_hybrid" (2/3 embedding
    similarity + 1/3 NER-keyword overlap between the JD and the CV's precomputed
    NER for that model).
    Each item in cvs must have at least: id, filename, raw_text, and (for the
    hybrid methods) ner_model1 / ner_model2.
    Returns the same list sorted by match_score DESC with match_score added.
    """
    if method in _METHOD_CONFIG:
        loader, ner_field, hybrid = _METHOD_CONFIG[method]
        results = _rank_model(jd_text, cvs, loader, ner_field, hybrid)
    else:
        results = _rank_tfidf(jd_text, cvs)

    return sorted(results, key=lambda x: x["match_score"], reverse=True)
