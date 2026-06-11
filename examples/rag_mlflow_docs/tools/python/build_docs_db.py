"""Build the MLflow documentation SQLite database with embeddings."""

from __future__ import annotations

from omnigent_client.tools import tool

MLFLOW_DOCS = {
    "doc1": (
        "MLflow is an open-source platform for managing the complete machine learning and GenAI lifecycle. "
        "It provides tools for experiment tracking, model packaging, versioning, and deployment. MLflow is "
        "designed to work with any ML library and can be used in any environment. It supports Python, R, "
        "and Java APIs, and integrates with popular ML frameworks like TensorFlow, PyTorch, and scikit-learn."
    ),
    "doc2": (
        "MLflow Tracing provides comprehensive observability for GenAI applications. It automatically captures "
        "inputs, outputs, and metadata at each step of your AI pipeline. Traces can be viewed in the MLflow UI "
        "with a waterfall visualization showing timing, token usage, and the complete call hierarchy. Tracing "
        "supports both auto-instrumentation (via mlflow.langchain.autolog()) and manual span creation with "
        "@mlflow.trace decorators."
    ),
    "doc3": (
        "MLflow integrates with over 40 popular frameworks and libraries. Key integrations include LangChain, "
        "LlamaIndex, OpenAI, Anthropic, DSPy, CrewAI, AutoGen, and Hugging Face Transformers. Each integration "
        "provides automatic tracing, model logging, and evaluation support. The mlflow.langchain.autolog() "
        "function enables one-line instrumentation for LangChain applications, capturing all chain executions, "
        "tool calls, and LLM interactions as structured traces."
    ),
    "doc4": (
        "MLflow Evaluation provides a systematic framework for assessing AI model quality. It includes over 60 "
        "built-in scorers for common metrics like RelevanceToQuery, Correctness, Faithfulness, and Safety. "
        "Custom scorers can be created using the @scorer decorator. MLflow also supports LLM-as-a-judge "
        "evaluation where a powerful model grades the outputs of the model being evaluated. Evaluation results "
        "are logged to MLflow experiments for comparison across runs."
    ),
    "doc5": (
        "The MLflow Prompt Registry provides centralized management for prompts used in GenAI applications. "
        "It supports versioning, tagging, and collaborative editing of prompt templates. Prompts can use "
        "Jinja2 templating with variable substitution. The registry integrates with MLflow Tracking so prompt "
        "changes are automatically linked to experiment runs, enabling A/B testing of different prompt versions "
        "and rollback to previous versions if needed."
    ),
    "doc6": (
        "MLflow supports collaborative development through its tracking server and model registry. Teams can "
        "share experiments, compare model versions, and manage the model lifecycle from development to production. "
        "The model registry provides stage transitions (Staging, Production, Archived) and approval workflows. "
        "MLflow's REST API and CLI enable integration with CI/CD pipelines for automated model deployment."
    ),
    "doc7": (
        "MLflow provides comprehensive cost tracking and optimization for LLM applications. Token usage is "
        "automatically captured in traces, enabling teams to monitor API costs per request, per user, and per "
        "model. Cost dashboards in the MLflow UI show spending trends over time. Teams can use this data to "
        "optimize prompt engineering, implement caching strategies, and choose the most cost-effective models "
        "for their use cases."
    ),
    "doc8": (
        "MLflow is fully open source under the Apache 2.0 license and is vendor-neutral. It can run on any "
        "cloud provider (AWS, Azure, GCP) or on-premises infrastructure. MLflow's artifact storage supports "
        "S3, Azure Blob Storage, GCS, HDFS, and local file systems. The tracking server can use SQLite, "
        "PostgreSQL, or MySQL as its backend store. This flexibility ensures teams are never locked into a "
        "single vendor or platform."
    ),
    "doc9": (
        "MLflow manages the complete ML lifecycle from experimentation to production. Key capabilities include: "
        "experiment tracking (parameters, metrics, artifacts), model packaging (MLmodel format with conda/pip "
        "environments), model registry (versioning, stage transitions, annotations), and model serving "
        "(REST API endpoints, batch inference). MLflow also provides tools for model comparison, A/B testing, "
        "and automated retraining pipelines."
    ),
    "doc10": (
        "MLflow includes several additional tools for AI development. The MLflow CLI provides commands for "
        "running projects, serving models, and managing the tracking server. MLflow Projects define reproducible "
        "runs with conda or Docker environments. MLflow Recipes provide predefined templates for common ML tasks "
        "like classification and regression. The MLflow Gateway (AI Gateway) provides a unified API for accessing "
        "multiple LLM providers with rate limiting, authentication, and cost tracking."
    ),
}


@tool
def build_docs_db() -> str:
    """
    Build the MLflow documentation database with embeddings.

    Creates a SQLite database at examples/tools/data/mlflow_docs.db containing
    10 MLflow documentation pages and their OpenAI embeddings. Skips if the
    database already exists.

    :returns: Summary of what was built.
    """
    import os
    import sqlite3
    from pathlib import Path

    db_path = Path(os.getcwd()) / "examples" / "tools" / "data" / "mlflow_docs.db"
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        conn.close()
        return f"Database already exists at {db_path} with {count} documents. No rebuild needed."

    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Load .env for OPENAI_API_KEY
    env_path = Path(os.getcwd()) / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

    import numpy as np
    from openai import OpenAI

    client = OpenAI()
    embed_model = os.getenv("EMBED_MODEL", "text-embedding-3-small")

    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE documents (doc_id TEXT PRIMARY KEY, content TEXT)")
    conn.execute("CREATE TABLE embeddings (doc_id TEXT PRIMARY KEY, vector BLOB)")

    for doc_id, content in MLFLOW_DOCS.items():
        conn.execute("INSERT INTO documents VALUES (?, ?)", (doc_id, content))
        response = client.embeddings.create(model=embed_model, input=content)
        vector = np.array(response.data[0].embedding, dtype=np.float32)
        conn.execute("INSERT INTO embeddings VALUES (?, ?)", (doc_id, vector.tobytes()))

    conn.commit()
    conn.close()
    return f"Built database at {db_path} with {len(MLFLOW_DOCS)} documents and embeddings."
