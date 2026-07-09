"""Retrieve MLflow traces for evaluation."""

from __future__ import annotations

from omnigent_client.tools import tool


@tool
def collect_traces(experiment_name: str = "default") -> str:
    """
    Retrieve recent MLflow traces from the tracking server.

    Fetches traces that contain agent interactions — tool calls, LLM
    requests, and policy evaluations. Traces must have been captured
    via the MLflow tracing skills (/setup-mlflow-tracing-claude or
    /setup-mlflow-tracing-codex) before this tool is called.

    :param experiment_name: MLflow experiment name to search. Defaults to "default".
    :returns: JSON summary of traces with spans, or an error message.
    """
    import json

    try:
        import mlflow
    except ImportError:
        return "Error: mlflow is not installed. Run: pip install mlflow"

    try:
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment is None:
            return (f"No MLflow experiment named '{experiment_name}' found. "
                    "Ensure MLflow tracing is enabled via the "
                    "/setup-mlflow-tracing-claude skill.")

        traces = mlflow.search_traces(
            experiment_ids=[experiment.experiment_id],
            max_results=50,
        )

        if traces.empty:
            return (f"No traces found in experiment '{experiment_name}'. "
                    "Run the target agent with MLflow tracing enabled first.")

        summary = {
            "experiment": experiment_name,
            "experiment_id": experiment.experiment_id,
            "trace_count": len(traces),
            "columns": list(traces.columns),
        }

        trace_details = []
        for _, row in traces.iterrows():
            detail = {
                "request_id": str(row.get("request_id", "")),
                "status": str(row.get("status", "")),
                "timestamp": str(row.get("timestamp_ms", "")),
            }
            if "request" in row and row["request"]:
                req = row["request"]
                detail["request_preview"] = str(req)[:500]
            if "response" in row and row["response"]:
                resp = row["response"]
                detail["response_preview"] = str(resp)[:500]
            trace_details.append(detail)

        summary["traces"] = trace_details
        return json.dumps(summary, indent=2, default=str)

    except Exception as e:
        return f"Error collecting traces: {e}"
