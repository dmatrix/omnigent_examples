"""Semantic search over the MLflow documentation database."""

from __future__ import annotations

from omniagents_client.tools import tool

_DOCS_CACHE: dict[str, str] = {}
_EMBEDDINGS_CACHE: dict[str, list[float]] = {}
_QUERY_EMBED_CACHE: dict[str, list[float]] = {}


def _load_env() -> None:
    """Load .env if OPENAI_API_KEY is not already set."""
    import os
    if os.getenv("OPENAI_API_KEY"):
        return
    from pathlib import Path
    candidates = [
        Path(os.getcwd()) / ".env",
        Path.home() / ".env",
    ]
    for candidate in candidates:
        if candidate.exists():
            with open(candidate) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
            return


def _load_db() -> bool:
    """Load documents and embeddings from SQLite into cache. Returns True if loaded."""
    if _DOCS_CACHE:
        return True

    import os
    import sqlite3
    from pathlib import Path
    import numpy as np

    db_path = Path(os.getcwd()) / "examples" / "tools" / "data" / "mlflow_docs.db"
    if not db_path.exists():
        return False

    conn = sqlite3.connect(str(db_path))
    for row in conn.execute("SELECT doc_id, content FROM documents"):
        _DOCS_CACHE[row[0]] = row[1]
    for row in conn.execute("SELECT doc_id, vector FROM embeddings"):
        vector = np.frombuffer(row[1], dtype=np.float32).tolist()
        _EMBEDDINGS_CACHE[row[0]] = vector
    conn.close()
    return True


@tool
def search_docs(query: str) -> str:
    """
    Search MLflow documentation using semantic search.

    Returns the top 3 documents that are above the relevance threshold.
    If no documents are relevant enough, returns a message saying so.

    :param query: Natural language search query about MLflow.
    :returns: Matching documents with relevance scores, or a message if nothing is relevant.
    """
    import hashlib
    import os
    import numpy as np
    from openai import OpenAI

    if not _load_db():
        return "Error: MLflow docs database not found. Call `build_docs_db` first to create it."

    _load_env()

    cache_key = hashlib.md5(query.encode()).hexdigest()
    if cache_key in _QUERY_EMBED_CACHE:
        query_vec = _QUERY_EMBED_CACHE[cache_key]
    else:
        embed_model = os.getenv("EMBED_MODEL", "text-embedding-3-small")
        response = OpenAI().embeddings.create(model=embed_model, input=query)
        query_vec = response.data[0].embedding
        _QUERY_EMBED_CACHE[cache_key] = query_vec

    q = np.array(query_vec)
    similarities = []
    for doc_id, doc_vec in _EMBEDDINGS_CACHE.items():
        d = np.array(doc_vec)
        score = float(np.dot(q, d) / (np.linalg.norm(q) * np.linalg.norm(d)))
        similarities.append({"doc_id": doc_id, "score": score, "content": _DOCS_CACHE[doc_id]})

    similarities.sort(key=lambda x: x["score"], reverse=True)
    TOP_K = 3
    MIN_SCORE = 0.4
    results = [r for r in similarities[:TOP_K] if r["score"] >= MIN_SCORE]

    if not results:
        return (
            "[no_match] (relevance: 0.000)\n"
            "This topic is not covered in the MLflow documentation corpus. "
            "The database contains 10 documents covering: MLflow platform overview, "
            "tracing, framework integrations, evaluation, prompt registry, "
            "collaborative development, cost tracking, open source licensing, "
            "ML lifecycle management, and CLI/gateway tools. "
            "No document matched the query above the relevance threshold of 0.4."
        )

    parts = []
    for r in results:
        parts.append(f"[{r['doc_id']}] (relevance: {r['score']:.3f})\n{r['content']}")

    return "\n\n".join(parts)
