# MLflow Docs RAG Agent

**Self-building RAG pipeline that answers questions about MLflow by searching a local corpus of documentation.**

![MLflow Docs RAG Architecture](../../images/rag_mlflow_docs_architecture.svg)

---

## Overview

The RAG agent answers questions about MLflow by searching a local corpus of 10 documentation pages. It has two auto-discovered tools:

- **`build_docs_db`** -- Creates a SQLite database with 10 MLflow doc pages and their OpenAI embeddings. Called automatically on first query. Idempotent -- skips if the database already exists.

- **`search_docs`** -- Semantic search over the embedded documents using cosine similarity. Returns the top-k most relevant documents with relevance scores.

The agent builds its own database on first use -- no setup script needed. Converted from [tutorial #9](https://github.com/dmatrix/mlflow-genai-tutorials/blob/main/09_complete_rag_application.ipynb) in the mlflow-genai-tutorials repo.

---

## Setup

No database setup needed -- the agent builds its own DB on the first query. You only need:

1. **Set up the OpenAI API key** (for embeddings):

```bash
echo 'OPENAI_API_KEY="sk-..."' > .env
```

2. **Run the agent:**

```bash
omniagents run examples/rag_mlflow_docs/
```

This uses `databricks-gpt-5-5` via Databricks AI Gateway (requires `databricks auth login`).

---

## Example Queries

```
What tracing capabilities does MLflow provide?
How does MLflow help with cost tracking?
Can MLflow integrate with LangChain?
What is the purpose of MLflow Prompt Registry?
What evaluation scorers does MLflow offer?
Is MLflow open source and what license does it use?
How does MLflow support collaborative development?
What is the MLflow Gateway?
What ML lifecycle stages does MLflow manage?
How do I use MLflow for experiment tracking?
```

---

## Tools

### `build_docs_db`

Creates `examples/tools/data/mlflow_docs.db` with 10 MLflow documentation pages and their OpenAI embeddings. Only needs to run once -- the agent calls it automatically on the first query. Subsequent calls are no-ops.

### `search_docs`

Semantic search over the embedded documents using OpenAI embeddings (`text-embedding-3-small`) and cosine similarity. Returns matching documents with relevance scores. Filters out-of-scope queries by returning a `no_match` sentinel when no documents exceed the relevance threshold.

---

## Known Limitation

The `search_docs` tool correctly filters out-of-scope queries (returns no documents below the relevance threshold), but `databricks-gpt-5-5` ignores the "refuse to answer" prompt instruction and answers from training data anyway. For strict RAG-only behavior where the agent declines out-of-scope questions, use a Claude model (`databricks-claude-sonnet-4-6` with the `claude-sdk` harness) which follows system prompt constraints more reliably.
