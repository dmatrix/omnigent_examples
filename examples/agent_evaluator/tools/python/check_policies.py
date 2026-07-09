"""Verify policy compliance by inspecting MLflow trace spans."""

from __future__ import annotations

from omnigent_client.tools import tool


@tool
def check_policies(
    experiment_name: str = "default",
    expected_denies: list[str] | None = None,
    expected_asks: list[str] | None = None,
    expected_labels: list[str] | None = None,
) -> str:
    """
    Inspect MLflow trace spans for policy evaluation events.

    Checks whether the expected DENY, ASK, and label-setting events
    occurred during the agent's execution. This verifies that governance
    policies fired correctly — e.g., that web_search was blocked after
    PII access, or that risk_score triggered an ASK after threshold.

    :param experiment_name: MLflow experiment to inspect. Defaults to "default".
    :param expected_denies: Policy names expected to have fired DENY (e.g. ["block_web_after_pii"]).
    :param expected_asks: Policy names expected to have fired ASK (e.g. ["risk_score", "bulk_access_guard"]).
    :param expected_labels: Labels expected to have been set (e.g. ["has_pii", "has_financial"]).
    :returns: JSON report of policy events found vs expected, or an error message.
    """
    import json

    try:
        import mlflow
    except ImportError:
        return "Error: mlflow is not installed. Run: pip install mlflow"

    try:
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment is None:
            return f"No MLflow experiment named '{experiment_name}' found."

        traces = mlflow.search_traces(
            experiment_ids=[experiment.experiment_id],
            max_results=50,
        )

        if traces.empty:
            return "No traces found to inspect for policy events."

        deny_events = []
        ask_events = []
        label_events = []
        all_spans = []

        for _, row in traces.iterrows():
            request_id = str(row.get("request_id", ""))
            trace = mlflow.get_trace(request_id)
            if trace is None:
                continue

            if not hasattr(trace, "data") or not hasattr(trace.data, "spans"):
                continue

            for span in trace.data.spans:
                span_info = {
                    "name": span.name,
                    "status": str(span.status) if hasattr(span, "status") else "",
                    "request_id": request_id,
                }
                all_spans.append(span_info)

                attrs = {}
                if hasattr(span, "attributes") and span.attributes:
                    attrs = span.attributes if isinstance(span.attributes, dict) else {}

                span_name_lower = span.name.lower()
                if "policy" in span_name_lower or "deny" in span_name_lower:
                    action = attrs.get("action", attrs.get("policy_action", ""))
                    policy_name = attrs.get("policy_name", span.name)
                    if str(action).upper() == "DENY":
                        deny_events.append({
                            "policy": policy_name,
                            "span": span.name,
                            "request_id": request_id,
                        })
                    elif str(action).upper() == "ASK":
                        ask_events.append({
                            "policy": policy_name,
                            "span": span.name,
                            "request_id": request_id,
                        })

                if "label" in span_name_lower or "taint" in span_name_lower:
                    label_name = attrs.get("label_name", attrs.get("label", span.name))
                    label_events.append({
                        "label": label_name,
                        "span": span.name,
                        "request_id": request_id,
                    })

        report = {
            "experiment": experiment_name,
            "total_traces": len(traces),
            "total_spans_inspected": len(all_spans),
            "deny_events_found": deny_events,
            "ask_events_found": ask_events,
            "label_events_found": label_events,
        }

        if expected_denies:
            found_deny_names = {e["policy"] for e in deny_events}
            report["expected_denies"] = {
                name: "FOUND" if name in found_deny_names else "MISSING"
                for name in expected_denies
            }

        if expected_asks:
            found_ask_names = {e["policy"] for e in ask_events}
            report["expected_asks"] = {
                name: "FOUND" if name in found_ask_names else "MISSING"
                for name in expected_asks
            }

        if expected_labels:
            found_label_names = {e["label"] for e in label_events}
            report["expected_labels"] = {
                name: "FOUND" if name in found_label_names else "MISSING"
                for name in expected_labels
            }

        missing = []
        for section in ["expected_denies", "expected_asks", "expected_labels"]:
            if section in report:
                missing.extend(
                    f"{section.replace('expected_', '')}: {k}"
                    for k, v in report[section].items()
                    if v == "MISSING"
                )

        report["compliance"] = "PASS" if not missing else "FAIL"
        if missing:
            report["missing_events"] = missing

        return json.dumps(report, indent=2, default=str)

    except Exception as e:
        return f"Error checking policies: {e}"
