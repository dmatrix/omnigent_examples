"""Custom policy: bulk customer access guard.

ASKs for approval when the agent queries more than ``max_customers``
distinct customer records in a single session. Tracks customer IDs
seen via ``session_state``.

Enforcement path: this policy is stateful, so it is fully effective only
on the **server** path (``omnigent run`` talks to the server engine, which
persists ``session_state`` and applies returned ``state_updates``). The
runner-local inner tool gate passes no ``session_state`` and discards
``state_updates`` (``omnigent/runner/policy.py``), so there the counter
cannot accumulate across calls: a single call naming more than
``max_customers`` distinct IDs still ASKs, but counts do not carry over
from one call to the next. That degradation is deliberate — see the
"Enforcement path" note in README.md.
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


def _tool_name(event: PolicyEvent) -> str:
    """Resolve the tool identity from a ``tool_call`` event.

    ``PolicyEvent`` carries the dispatched tool name in ``target`` and the
    call payload in ``data`` as ``{"name", "arguments"}`` — there is no
    ``tool_name`` key. Prefer ``target``, since an earlier policy in the
    chain cannot have rewritten it; fall back to the payload's own name.
    """
    target = event.get("target")
    if isinstance(target, str) and target:
        return target
    data = event.get("data")
    if isinstance(data, dict):
        for key in ("name", "tool"):
            value = data.get(key)
            if isinstance(value, str) and value:
                return value
    return ""


def _tool_args(event: PolicyEvent) -> dict[str, Any]:  # type: ignore[explicit-any]
    """Extract the call's argument dict from ``data["arguments"]``.

    Both the server engine and the runner-local gate shape a ``tool_call``
    payload as ``{"name", "arguments"}``; the bare-dict fallback is
    defensive, for a caller that passes the arguments alone.
    """
    data = event.get("data")
    if not isinstance(data, dict):
        return {}
    args = data.get("arguments")
    return args if isinstance(args, dict) else data


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

        if _tool_name(event) not in _CUSTOMER_TOOLS:
            return _ALLOW

        state = event.get("session_state") or {}
        seen_raw = state.get(_STATE_KEY, "[]")
        seen: list[str] = json.loads(seen_raw) if isinstance(seen_raw, str) else seen_raw

        args = _tool_args(event)
        args_str = json.dumps(args)
        new_ids = _CUSTOMER_ID_RE.findall(args_str)

        updated = sorted(set(seen) | {cid.upper() for cid in new_ids})

        # ``len(seen) <= max_customers`` makes the ASK fire exactly once, at
        # the crossing: once the stored count is already over the limit, the
        # user has answered and later calls pass through.
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
