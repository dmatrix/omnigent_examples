"""Custom policy: bulk customer access guard.

ASKs for approval when the agent queries more than ``max_customers``
distinct customer records in a single session. Tracks customer IDs
seen via ``session_state``.
"""

from __future__ import annotations

import json
import re
from typing import Any

from omnigent.policies.schema import PolicyCallable, PolicyEvent, PolicyResponse

_ALLOW: PolicyResponse = {"result": "ALLOW"}
_STATE_KEY = "_bulk_access_customers_seen"
_CUSTOMER_TOOLS = frozenset({"query_customers", "query_billing"})
_CUSTOMER_ID_RE = re.compile(r"CUST-\d+", re.IGNORECASE)


def bulk_access_guard(
    *,
    max_customers: int = 3,
) -> PolicyCallable:
    """Factory: ASK when distinct customer count exceeds *max_customers*.

    Inspects tool call arguments for customer ID patterns (CUST-XXXX)
    and tracks them across the session.
    """

    def evaluate(event: PolicyEvent) -> PolicyResponse:
        if event.get("type") != "tool_call":
            return _ALLOW

        tool_name = event.get("tool_name", "")
        if tool_name not in _CUSTOMER_TOOLS:
            return _ALLOW

        state = event.get("session_state") or {}
        seen_raw = state.get(_STATE_KEY, "[]")
        seen: list[str] = json.loads(seen_raw) if isinstance(seen_raw, str) else seen_raw

        args = event.get("tool_args") or {}
        args_str = json.dumps(args) if isinstance(args, dict) else str(args)
        new_ids = _CUSTOMER_ID_RE.findall(args_str)

        updated = list(set(seen) | {cid.upper() for cid in new_ids})

        if len(updated) > max_customers and len(seen) <= max_customers:
            return {
                "result": "ASK",
                "reason": (
                    f"Bulk access guard: this session has accessed "
                    f"{len(updated)} distinct customer records "
                    f"(limit: {max_customers}). Continue?"
                ),
                "state_updates": [
                    {"key": _STATE_KEY, "action": "set", "value": json.dumps(updated)},
                ],
            }

        return {
            "result": "ALLOW",
            "state_updates": [
                {"key": _STATE_KEY, "action": "set", "value": json.dumps(updated)},
            ],
        }

    return evaluate  # type: ignore[return-value]


POLICY_REGISTRY: list[dict[str, Any]] = [
    {
        "handler": (
            "examples.telco_customer_agent.policies."
            "bulk_access_guard.bulk_access_guard"
        ),
        "kind": "factory",
        "name": "Bulk Customer Access Guard",
        "description": (
            "ASKs for approval when the session queries more than "
            "max_customers distinct customer records."
        ),
        "params_schema": {
            "type": "object",
            "properties": {
                "max_customers": {
                    "type": "integer",
                    "description": "Max distinct customers before ASK",
                    "default": 3,
                },
            },
        },
    },
]
