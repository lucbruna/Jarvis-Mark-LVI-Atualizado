"""JARVIS plugin - build a local RAG index over files/memory for semantic recall.

Uses scikit-learn TF-IDF when available (no heavy ML deps). Indexes a folder
or memory entries and answers semantic-ish queries. Complements search_memory.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

from core import outcome

PLUGIN = {
    "name": "rag_indexer",
    "description": (
        "Builds a local TF-IDF index over a folder (or memory) and answers "
        "queries by semantic-ish similarity. Use for 'search my notes for X', "
        "'find documents about Y'. Requires scikit-learn for best results; "
        "falls back to keyword matching otherwise."
    ),
    "brief": "Local RAG index (TF-IDF) over files or memory.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "index|query|stats"},
            "path": {"type": "STRING", "description": "Folder to index (default: documents)."},
            "query": {"type": "STRING", "description": "Query for action=query."},
            "top_k": {"type": "INTEGER", "description": "Results to return (default 5)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}

_STATE = {"vectorizer": None, "matrix": None, "docs": [], "lock": threading.Lock()}


def _collect_docs(folder: Path) -> list[tuple[str, str]]:
    out = []
    for p in folder.rglob("*"):
        if p.is_file() and p.suffix.lower() in (".txt", ".md", ".py", ".json", ".csv"):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")[:4000]
                out.append((str(p), text))
            except Exception:
                pass
    return out


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower().strip()
    top_k = int(params.get("top_k") or 5)

    if action == "index":
        folder = Path(params.get("path") or str(Path.home() / "Documents")).expanduser()
        if not folder.exists():
            return outcome.failed("rag_indexer", f"folder not found: {folder}")
        docs = _collect_docs(folder)
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            vec = TfidfVectorizer(stop_words="english", max_features=5000)
            mat = vec.fit_transform([d[1] for d in docs])
            with _STATE["lock"]:
                _STATE["vectorizer"] = vec
                _STATE["matrix"] = mat
                _STATE["docs"] = docs
            msg = f"Indexed {len(docs)} documents from {folder}"
            if player:
                try: player.write_log(f"JARVIS: {msg}")
                except Exception: pass
            return outcome.done("rag_indexer", note=msg, count=len(docs))
        except ImportError:
            with _STATE["lock"]:
                _STATE["docs"] = docs
                _STATE["vectorizer"] = None
                _STATE["matrix"] = None
            return outcome.done("rag_indexer", note=f"Indexed {len(docs)} docs (keyword fallback; install scikit-learn for TF-IDF)")

    if action == "query":
        q = params.get("query", "").strip()
        if not q:
            return outcome.failed("rag_indexer", "query required")
        with _STATE["lock"]:
            docs = list(_STATE["docs"])
            vec = _STATE["vectorizer"]
            mat = _STATE["matrix"]
        if not docs:
            return outcome.failed("rag_indexer", "no index; run action=index first")
        if vec is not None and mat is not None:
            try:
                from sklearn.metrics.pairwise import cosine_similarity
                import numpy as np
                qv = vec.transform([q])
                sims = cosine_similarity(qv, mat).flatten()
                idx = sims.argsort()[::-1][:top_k]
                results = [(docs[i][0], float(sims[i])) for i in idx if sims[i] > 0]
            except Exception:
                results = []
        else:
            ql = q.lower().split()
            scored = []
            for path, text in docs:
                tl = text.lower()
                sc = sum(tl.count(w) for w in ql)
                if sc > 0:
                    scored.append((path, sc))
            scored.sort(key=lambda x: -x[1])
            results = scored[:top_k]
        if not results:
            return outcome.done("rag_indexer", note="no matches")
        lines = [f"{i+1}. {p} (score {s:.3f})" for i, (p, s) in enumerate(results)]
        msg = "RAG results:\n" + "\n".join(lines)
        if player:
            try: player.write_log(f"JARVIS: {msg[:400]}")
            except Exception: pass
        return outcome.done("rag_indexer", note=msg[:400], results=results)

    if action == "stats":
        with _STATE["lock"]:
            n = len(_STATE["docs"])
            has_vec = _STATE["vectorizer"] is not None
        return outcome.done("rag_indexer", note=f"docs={n}, tfidf={has_vec}")

    return outcome.failed("rag_indexer", f"unknown action: {action}")
