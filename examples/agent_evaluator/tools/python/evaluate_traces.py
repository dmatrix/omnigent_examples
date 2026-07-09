"""Score MLflow traces with LLM judges — no eval dataset needed."""

from __future__ import annotations

from omnigent_client.tools import tool


@tool
def evaluate_traces(
    experiment_name: str = "default",
    custom_guidelines: list[str] | None = None,
) -> str:
    """
    Run mlflow.genai.evaluate() on collected traces with LLM-judge scorers.

    Scores traces for relevance, safety, guideline adherence, tool selection,
    and logical consistency. No eval dataset or ground truth needed — all
    scorers work directly from the input/output pairs in the traces.

    :param experiment_name: MLflow experiment to evaluate. Defaults to "default".
    :param custom_guidelines: Optional list of custom guideline strings for the Guidelines scorer.
    :returns: JSON evaluation results with per-scorer metrics, or an error message.
    """
    import json

    try:
        import mlflow
        from mlflow.genai.scorers import RelevanceToQuery, Safety, Guidelines
    except ImportError:
        return ("Error: mlflow is not installed or missing genai module. "
                "Run: pip install mlflow")

    try:
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment is None:
            return (f"No MLflow experiment named '{experiment_name}' found. "
                    "Run collect_traces first to verify traces exist.")

        traces = mlflow.search_traces(
            experiment_ids=[experiment.experiment_id],
            max_results=50,
        )

        if traces.empty:
            return "No traces found to evaluate."

        scorers = [
            RelevanceToQuery(),
            Safety(),
        ]

        guidelines = custom_guidelines or [
            "Must use tools for every answer, never answer from training data",
            "Must decline out-of-scope questions rather than guessing",
        ]
        scorers.append(Guidelines(guidelines=guidelines))

        try:
            from mlflow.genai.scorers.trulens import ToolSelection, LogicalConsistency
            scorers.append(ToolSelection(model="openai:/gpt-5-mini"))
            scorers.append(LogicalConsistency(model="openai:/gpt-5-mini"))
        except ImportError:
            pass

        results = mlflow.genai.evaluate(
            data=traces,
            scorers=scorers,
        )

        output = {
            "experiment": experiment_name,
            "traces_evaluated": len(traces),
            "scorers_used": [type(s).__name__ for s in scorers],
        }

        if hasattr(results, "metrics") and results.metrics:
            output["metrics"] = {
                k: round(v, 4) if isinstance(v, float) else v
                for k, v in results.metrics.items()
            }

        if hasattr(results, "tables") and results.tables:
            for table_name, table_df in results.tables.items():
                output[f"table_{table_name}"] = table_df.to_dict(orient="records")

        return json.dumps(output, indent=2, default=str)

    except Exception as e:
        return f"Error evaluating traces: {e}"
