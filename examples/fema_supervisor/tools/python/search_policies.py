"""Semantic search tool for FEMA policy documents."""

from __future__ import annotations

import hashlib
import os
from typing import List

import mlflow
import numpy as np
from openai import OpenAI
from omniagents_client.tools import tool

from .policy_docs import get_policy_documents

_EMBEDDING_CACHE: dict[str, List[float]] = {}
_DOC_EMBEDDINGS: dict[str, List[float]] = {}
_POLICY_DOCUMENTS: dict[str, str] = {}

EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")


def _get_client() -> OpenAI:
    return OpenAI()


def _embed_text(text: str) -> List[float]:
    cache_key = hashlib.md5(text.encode()).hexdigest()
    if cache_key in _EMBEDDING_CACHE:
        return _EMBEDDING_CACHE[cache_key]
    response = _get_client().embeddings.create(model=EMBED_MODEL, input=text)
    embedding = response.data[0].embedding
    _EMBEDDING_CACHE[cache_key] = embedding
    return embedding


def _ensure_doc_embeddings() -> None:
    global _POLICY_DOCUMENTS
    if _DOC_EMBEDDINGS:
        return
    _POLICY_DOCUMENTS = get_policy_documents()
    for doc_id, text in _POLICY_DOCUMENTS.items():
        _DOC_EMBEDDINGS[doc_id] = _embed_text(text)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    a_arr, b_arr = np.array(a), np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))


@tool
@mlflow.trace(name="search_policies", span_type="RETRIEVER")
def search_policies(query: str, top_k: int = 3) -> str:
    """
    Semantic search over FEMA policy documents.

    :param query: Natural language search query.
    :param top_k: Number of top results to return (default 3).
    :returns: Matching documents with relevance scores.
    """
    _ensure_doc_embeddings()
    query_embedding = _embed_text(query)

    similarities = []
    for doc_id, doc_embedding in _DOC_EMBEDDINGS.items():
        score = _cosine_similarity(query_embedding, doc_embedding)
        similarities.append({"doc_id": doc_id, "score": score, "text": _POLICY_DOCUMENTS[doc_id]})

    similarities.sort(key=lambda x: x["score"], reverse=True)
    results = similarities[:top_k]

    span = mlflow.get_current_active_span()
    if span:
        span.set_attributes({
            "top_k": top_k,
            "top_score": results[0]["score"] if results else 0,
            "retrieved_docs": [r["doc_id"] for r in results],
        })

    parts = []
    for r in results:
        parts.append(f"[{r['doc_id']}] (relevance: {r['score']:.3f})\n{r['text']}")

    return "\n\n".join(parts)
