import re
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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

def rank_cvs(jd_text: str, cvs: list) -> list:
    """
    Rank CVs against a job description using TF-IDF cosine similarity.
    Each item in cvs must have at least: id, filename, raw_text.
    Returns the same list sorted by match_score DESC with match_score added.
    """
    jd_clean = _clean_for_tfidf(jd_text)
    cv_cleans = [_clean_for_tfidf(cv.get("raw_text") or "") for cv in cvs]

    vectorizer = TfidfVectorizer()
    tfidf = vectorizer.fit_transform([jd_clean] + cv_cleans)
    sims = cosine_similarity(tfidf[0:1], tfidf[1:])[0]

    results = []
    for cv, score in zip(cvs, sims):
        results.append({**cv, "match_score": round(float(score) * 100, 2)})

    return sorted(results, key=lambda x: x["match_score"], reverse=True)
