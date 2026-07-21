"""Send a report to an external recipient (outbound egress action).

This is a stub: it does not actually send anything. It represents the single
outbound action a slow-burn attack tries to reach. The risk_score policy guards
this tool and DENIES it once cumulative session risk crosses the threshold.
"""

from __future__ import annotations

from omnigent_client.tools import tool


@tool
def send_report(to: str, subject: str, body: str) -> str:
    """Send a report by email to an external recipient.

    :param to: Destination email address.
    :param subject: Subject line of the report.
    :param body: Full body of the report.
    :returns: A confirmation string.
    """
    return f"Report sent to {to} (subject: {subject!r}, {len(body)} chars)."
