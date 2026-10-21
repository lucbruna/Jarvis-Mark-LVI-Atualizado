"""core/rag.py - semantic search with sentence-transformers + FAISS.

Falls back to TF-IDF (sklearn) and then lexical matching when the heavy
deps are missing. Used by memory_manager for recall and by rag_indexer plugin.
"""
from __future__ import annotations

import threading
from typing import Any

_LOCK = threading.Lock()
_MODEL = None
_FAISS = None
_TFIDF = None


def _sentence_transformers_available() -> bool:
    try:
        import sentence_transformers  # noqa
        return True
    except Exception:
        return False


def _faiss_available() -> bool:
    try:
        import faiss  # noqa
        return True
    except Exception:
        return False


def _sklearn_available() -> bool:
    try:
        import sklearn  # noqa
        return True
    except Exception:
        return False


def get_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    with _LOCK:
        if _MODEL is not None:
            return _MODEL
        if not _sentence_transformers_available():
            _MODEL = False
            return _MODEL
        try:
            from sentence_transformers import SentenceTransformer
            _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            _MODEL = False
        return _MODEL


def embed(texts: list[str]) -> Any:
    model = get_model()
    if not model:
        return None
    try:
        return model.encode(texts, convert_to_numpy=True)
    except Exception:
        return None


def semantic_search(query: str, docs: list[tuple[str, str]], top_k: int = 5) -> list[tuple[str, float]]:
    """Return [(doc_id, score)] sorted by relevance."""
    if not docs:
        return []
    # Try sentence-transformers + FAISS
    if _sentence_transformers_available() and _faiss_available():
        try:
            import faiss
            import numpy as np
            model = get_model()
            if model:
                doc_texts = [d[1] for d in docs]
                doc_embs = model.encode(doc_texts, convert_to_numpy=True).astype("float32")
                q_emb = model.encode([query], convert_to_numpy=True).astype("float32")
                index = faiss.IndexFlatIP(doc_embs.shape[1])
                faiss.normalize_L2(doc_embs)
                faiss.normalize_L2(q_emb)
                index.add(doc_embs)
                scores, idx = index.search(q_emb, min(top_k, len(docs)))
                return [(docs[i][0], float(scores[0][j])) for j, i in enumerate(idx[0]) if i >= 0]
        except Exception:
            pass
    # Try TF-IDF
    if _sklearn_available():
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            vec = TfidfVectorizer(stop_words="english")
            mat = vec.fit_transform([d[1] for d in docs])
            qv = vec.transform([query])
            sims = cosine_similarity(qv, mat).flatten()
            idx = sims.argsort()[::-1][:top_k]
            return [(docs[i][0], float(sims[i])) for i in idx if sims[i] > 0]
        except Exception:
            pass
    # Lexical fallback
    ql = query.lower().split()
    scored = []
    for did, text in docs:
        tl = text.lower()
        sc = sum(tl.count(w) for w in ql)
        if sc > 0:
            scored.append((did, float(sc)))
    scored.sort(key=lambda x: -x[1])
    return scored[:top_k]


def is_available() -> bool:
    return _sentence_transformers_available() or _sklearn_available()
