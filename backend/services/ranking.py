import re
import os
import ssl
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Bypass corporate network SSL intercept verify failures using robust monkeypatching
import requests
original_requests_send = requests.Session.send
def patched_requests_send(self, request, **kwargs):
    kwargs['verify'] = False
    return original_requests_send(self, request, **kwargs)
requests.Session.send = patched_requests_send

try:
    import httpx
    original_httpx_init = httpx.Client.__init__
    def patched_httpx_init(self, *args, **kwargs):
        kwargs['verify'] = False
        original_httpx_init(self, *args, **kwargs)
    httpx.Client.__init__ = patched_httpx_init
    
    original_httpx_async_init = httpx.AsyncClient.__init__
    def patched_httpx_async_init(self, *args, **kwargs):
        kwargs['verify'] = False
        original_httpx_async_init(self, *args, **kwargs)
    httpx.AsyncClient.__init__ = patched_httpx_async_init
except ImportError:
    pass

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


_transformer_model = None

def _get_transformer_model():
    global _transformer_model
    if _transformer_model is None:
        from sentence_transformers import SentenceTransformer
        _transformer_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _transformer_model


def _rank_transformer(jd_text: str, cvs: list, hybrid: bool) -> list:
    """Rank CVs using SentenceTransformer 'all-MiniLM-L6-v2' similarity, optionally blending keyword overlap."""
    model = _get_transformer_model()
    jd_emb = model.encode(jd_text or "")
    
    cv_texts = [cv.get("raw_text") or "" for cv in cvs]
    if not cv_texts:
        return []
        
    cv_embs = model.encode(cv_texts)
    
    # Reshape for cosine similarity calculation
    jd_emb = jd_emb.reshape(1, -1)
    sims = cosine_similarity(jd_emb, cv_embs)[0]
    
    results = []
    for cv, score in zip(cvs, sims):
        embed_score = float(score) * 100
        if hybrid:
            ner1 = ner_service.run_ner(jd_text or "", ner_service.get_model1())
            ner2 = ner_service.run_ner(jd_text or "", ner_service.get_model2())
            jd_ner = ner_service.merge_ner(ner1, ner2)
            keyword_score = _ner_keyword_score(jd_ner, cv.get("ner_merged") or {})
            score_val = EMBEDDING_WEIGHT * embed_score + KEYWORD_WEIGHT * keyword_score
            results.append({
                **cv,
                "match_score": round(score_val, 2),
                "embedding_score": round(embed_score, 2),
                "keyword_score": round(keyword_score, 2),
            })
        else:
            results.append({**cv, "match_score": round(embed_score, 2)})
            
    return results


_nbk_model = None
_nbk_tokenizer = None

def _get_nbk_model_and_tokenizer():
    global _nbk_model, _nbk_tokenizer
    if _nbk_model is None or _nbk_tokenizer is None:
        import sys
        import torch
        from types import ModuleType
        
        # Apply compatibility patches for HF / PyTorch v5
        if 'transformers.onnx' not in sys.modules:
            transformers_onnx_mock = ModuleType('transformers.onnx')
            transformers_onnx_mock.OnnxConfig = object
            sys.modules['transformers.onnx'] = transformers_onnx_mock
            
        import transformers.pytorch_utils
        if not hasattr(transformers.pytorch_utils, 'find_pruneable_heads_and_indices'):
            def find_pruneable_heads_and_indices(heads, n_heads, head_size, already_pruned_heads):
                mask = torch.ones(n_heads, head_size)
                heads = sorted(list(set(heads) - already_pruned_heads))
                for head in heads:
                    mask[head] = 0
                heads = set(heads) | already_pruned_heads
                indices = mask.view(-1).nonzero().view(-1)
                return heads, indices
            transformers.pytorch_utils.find_pruneable_heads_and_indices = find_pruneable_heads_and_indices
            
        from transformers.configuration_utils import PretrainedConfig
        if not hasattr(PretrainedConfig, '__patched_getattribute'):
            orig_getattribute = PretrainedConfig.__getattribute__
            def patched_getattribute(self, key):
                try:
                    return orig_getattribute(self, key)
                except AttributeError:
                    if key in ('is_decoder', 'add_cross_attention'):
                        return False
                    raise
            PretrainedConfig.__getattribute__ = patched_getattribute
            PretrainedConfig.__patched_getattribute = True
            
        import transformers
        if not hasattr(transformers.PreTrainedModel, 'get_head_mask'):
            def get_head_mask(self, head_mask, num_hidden_layers, is_attention_chunked=False):
                if head_mask is None:
                    return [None] * num_hidden_layers
                return [None] * num_hidden_layers
            transformers.PreTrainedModel.get_head_mask = get_head_mask

        from transformers import AutoModel, AutoTokenizer
        _nbk_tokenizer = AutoTokenizer.from_pretrained('0xnbk/nbk-ats-semantic-v1-en', trust_remote_code=True)
        _nbk_model = AutoModel.from_pretrained('0xnbk/nbk-ats-semantic-v1-en', trust_remote_code=True)
        _nbk_model.eval()
        
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        _nbk_model = _nbk_model.to(device)
        
    return _nbk_model, _nbk_tokenizer


def _rank_nbk_ats_semantic(jd_text: str, cvs: list) -> list:
    """Rank CVs against a job description using fine-tuned 0xnbk/nbk-ats-semantic-v1-en model."""
    import torch
    import numpy as np
    
    model, tokenizer = _get_nbk_model_and_tokenizer()
    device = next(model.parameters()).device
    
    jd_text_val = jd_text or ""
    cv_texts = [cv.get("raw_text") or "" for cv in cvs]
    if not cv_texts:
        return []
        
    def mean_pooling(model_output, attention_mask):
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        
    # Encode Job Description
    with torch.no_grad():
        jd_inputs = tokenizer(jd_text_val, padding=True, truncation=True, max_length=8192, return_tensors='pt').to(device)
        jd_output = model(**jd_inputs)
        jd_emb = mean_pooling(jd_output, jd_inputs['attention_mask']).cpu().numpy()[0]
        
    # Encode CVs
    scores = []
    for cv_text in cv_texts:
        with torch.no_grad():
            cv_inputs = tokenizer(cv_text, padding=True, truncation=True, max_length=8192, return_tensors='pt').to(device)
            cv_output = model(**cv_inputs)
            cv_emb = mean_pooling(cv_output, cv_inputs['attention_mask']).cpu().numpy()[0]
            
            # Cosine similarity
            similarity = np.dot(jd_emb, cv_emb) / (np.linalg.norm(jd_emb) * np.linalg.norm(cv_emb))
            score = float(similarity * 100)
            scores.append(score)
            
    results = []
    for cv, score in zip(cvs, scores):
        results.append({**cv, "match_score": round(score, 2)})
        
    return results


def _rank_lda(jd_text: str, cvs: list) -> list:
    """Rank CVs against a job description using LDA Topic modeling cosine similarity."""
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.decomposition import LatentDirichletAllocation
    
    jd_clean = jd_text or ""
    cv_texts = [cv.get("raw_text") or "" for cv in cvs]
    if not cv_texts:
        return []
        
    corpus = [jd_clean] + cv_texts
    
    # Fit CountVectorizer on the corpus to extract counts
    vectorizer = CountVectorizer(stop_words='english')
    try:
        counts = vectorizer.fit_transform(corpus)
    except ValueError:
        # If vocabulary is empty (e.g. all stop words)
        return [{**cv, "match_score": 0.0} for cv in cvs]
        
    # Fit LDA on corpus (n_components = 5 topics)
    lda = LatentDirichletAllocation(n_components=5, random_state=42)
    topic_dist = lda.fit_transform(counts)
    
    jd_topic_vec = topic_dist[0:1] # Shape: (1, 5)
    cv_topic_vecs = topic_dist[1:] # Shape: (num_cvs, 5)
    
    sims = cosine_similarity(jd_topic_vec, cv_topic_vecs)[0]
    
    results = []
    for cv, score in zip(cvs, sims):
        results.append({**cv, "match_score": round(float(score) * 100, 2)})
        
    return results


def _rank_doc2vec(jd_text: str, cvs: list) -> list:
    """Rank CVs against a job description using Doc2Vec cosine similarity."""
    from gensim.models.doc2vec import Doc2Vec, TaggedDocument
    import numpy as np
    
    jd_clean = jd_text or ""
    cv_texts = [cv.get("raw_text") or "" for cv in cvs]
    if not cv_texts:
        return []
        
    # Tagged documents for gensim
    tagged_data = [TaggedDocument(words=jd_clean.lower().split(), tags=["jd"])]
    for idx, cv in enumerate(cvs):
        text = cv.get("raw_text") or ""
        tagged_data.append(TaggedDocument(words=text.lower().split(), tags=[str(idx)]))
        
    # Train a Doc2Vec model on the corpus
    model = Doc2Vec(vector_size=50, window=4, min_count=1, workers=2, epochs=40, seed=42)
    model.build_vocab(tagged_data)
    model.train(tagged_data, total_examples=model.corpus_count, epochs=model.epochs)
    
    # Infer vectors
    jd_vec = model.dv["jd"].reshape(1, -1)
    cv_vecs = [model.dv[str(idx)] for idx in range(len(cvs))]
    
    if not cv_vecs:
        return []
        
    sims = cosine_similarity(jd_vec, cv_vecs)[0]
    
    results = []
    for cv, score in zip(cvs, sims):
        results.append({**cv, "match_score": round(float(score) * 100, 2)})
        
    return results


def rank_cvs(jd_text: str, cvs: list, method: str = "tfidf") -> list:
    """
    Rank CVs against a job description.
    method: "tfidf" (default); "model1" / "model2" (pure doc.vector embedding
    similarity — model1's vectors are a tok2vec fallback, see vector_showcase.ipynb,
    not recommended on their own); "model1_hybrid" / "model2_hybrid" (2/3 embedding
    similarity + 1/3 NER-keyword overlap between the JD and the CV's precomputed
    NER for that model); "sentence_transformer" / "sentence_transformer_hybrid"
    (SentenceTransformer semantic matching); "lda" (LDA topic modeling similarity);
    "doc2vec" (Doc2Vec context embedding similarity).
    Each item in cvs must have at least: id, filename, raw_text, and (for the
    hybrid methods) ner_model1 / ner_model2 / ner_merged.
    Returns the same list sorted by match_score DESC with match_score added.
    """
    if method == "doc2vec":
        results = _rank_doc2vec(jd_text, cvs)
    elif method == "lda":
        results = _rank_lda(jd_text, cvs)
    elif method == "nbk_ats_semantic":
        results = _rank_nbk_ats_semantic(jd_text, cvs)
    elif method in ("sentence_transformer", "sentence_transformer_hybrid"):
        results = _rank_transformer(jd_text, cvs, hybrid=(method == "sentence_transformer_hybrid"))
    elif method in _METHOD_CONFIG:
        loader, ner_field, hybrid = _METHOD_CONFIG[method]
        results = _rank_model(jd_text, cvs, loader, ner_field, hybrid)
    else:
        results = _rank_tfidf(jd_text, cvs)

    return sorted(results, key=lambda x: x["match_score"], reverse=True)
