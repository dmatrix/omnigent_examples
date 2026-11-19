"""Custom policy: the content factory's publish gate.

The single teaching point of this example: **unattended cycles produce
freely; publication requires a signature.**

So this policy draws a hard line between two tiers of tool:

* The *free-flowing* tier — ``read_backlog``, ``update_backlog`` and
  ``save_artifact``. Never gated, whatever else the session has done. A
  scheduled 9am cycle must be able to research, draft, edit and stage every
  artifact with nobody watching.
* The *shipping* tier — ``publish_content`` and ``post_social``. Always
  escalated to a human, and hard-DENIED when short-form social content would
  go out ahead of the long-form post it cites.

All cross-turn state lives in ``session_state`` and is mutated only through
``state_updates``, the same shape ``bulk_access_guard`` uses. Approvals and
publish counts are recorded on the ``tool_result`` phase rather than on
``tool_call``, for two reasons: that is the only phase where a tool's
*success* is observable, and the engine withholds ``state_updates`` on an ASK
(see ``PolicyResponse.state_updates``), so a gated call could never record
itself.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from omnigent.policies.schema import PolicyCallable, PolicyEvent, PolicyResponse

_ALLOW: PolicyResponse = {"result": "ALLOW"}

# ``session_state`` keys. Deliberately NOT prefixed ``_policy_`` — the engine
# reserves that prefix for approval checkpoints it writes itself.
_APPROVED_SLUGS_KEY = "_publish_gate_approved_slugs"
_CYCLE_PUBLISHES_KEY = "_publish_gate_cycle_publishes"

_PUBLISH_CONTENT = "publish_content"
_POST_SOCIAL = "post_social"
_UPDATE_BACKLOG = "update_backlog"

# The shipping tier — every call here faces a rule below.
_GUARDED_TOOLS = frozenset({_PUBLISH_CONTENT, _POST_SOCIAL})

# The free-flowing tier. Spelled out rather than implied by the absence of a
# rule, because the contrast between the two tiers *is* the example.
_UNGATED_TOOLS = frozenset({"read_backlog", _UPDATE_BACKLOG, "save_artifact"})

_APPROVED_STATUS = "APPROVED"


# ── Event readers ────────────────────────────────────────────────────────────


def _tool_name(event: PolicyEvent) -> str:
    """Resolve the tool identity for an event across both enforcement paths.

    The server-side engine sets ``event["target"]`` and shapes ``data`` as
    ``{"name": ..., "arguments": {...}}``; the runner-local inner gate sets
    ``target`` too but passes the bare argument dict as ``data``. Prefer
    ``target`` (the dispatched identity, which an earlier policy cannot have
    rewritten) and fall back to the payload.

    :param event: The policy event.
    :returns: The tool name, or ``""`` when it cannot be determined.
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


def _tool_args(data: object) -> dict[str, Any]:  # type: ignore[explicit-any]
    """Extract the tool-call argument dict from an event payload.

    :param data: ``event["data"]`` on ``tool_call``, or ``event["request_data"]``
        on ``tool_result``.
    :returns: The arguments dict, or ``{}`` when the payload carries none.
    """
    if not isinstance(data, dict):
        return {}
    args = data.get("arguments")
    if isinstance(args, dict):
        return args
    # Inner path: ``data`` already *is* the argument dict.
    return data


def _result_payload(data: object) -> object:
    """Parse a ``tool_result`` payload into its structured form.

    Handles the server shape (``{"result": "<json-or-text>"}``) and the
    runner shape (a raw string or an already-structured value).

    :param data: The raw ``event["data"]`` on a ``tool_result`` event.
    :returns: The parsed structure when the payload was JSON, else the raw value.
    """
    inner = data
    if isinstance(data, dict) and "result" in data:
        inner = data["result"]
    if isinstance(inner, str):
        try:
            return json.loads(inner)
        except (ValueError, TypeError):
            return inner
    return inner


def _succeeded(payload: object) -> bool:
    """Decide whether a tool result represents a successful call.

    Every content-factory tool returns a JSON-serializable dict and signals
    failure with an ``error`` key. Anything that is not a dict counts as a
    failure: this gate fails closed, so an unconfirmed ``update_backlog``
    never unlocks ``post_social``.

    :param payload: A parsed tool-result payload.
    :returns: ``True`` only for a dict carrying no ``error``.
    """
    return isinstance(payload, dict) and not payload.get("error")


# ── State readers ────────────────────────────────────────────────────────────


def _approved_slugs(state: dict[str, object]) -> list[str]:
    """Read the slugs this session has seen reach ``APPROVED``.

    :param state: The event's ``session_state``.
    :returns: Approved slugs, or ``[]`` when none are recorded or the stored
        value is unreadable.
    """
    raw = state.get(_APPROVED_SLUGS_KEY, "[]")
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return []
    return [str(item) for item in value] if isinstance(value, list) else []


def _cycle_id() -> str:
    """Identify the current cycle.

    Cycles are daily (``rrule: FREQ=DAILY``) and their artifact is
    ``artifacts/cycles/<YYYY-MM-DD>-cycle.md``, so the UTC calendar day *is*
    the cycle identity. A count carrying an older day has expired.

    :returns: The current UTC date as ``"YYYY-MM-DD"``.
    """
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _cycle_publishes(state: dict[str, object]) -> int:
    """Read the number of successful publishes recorded for the current cycle.

    :param state: The event's ``session_state``.
    :returns: The count for today's cycle; ``0`` when the stored record
        belongs to an earlier cycle or is unreadable.
    """
    raw = state.get(_CYCLE_PUBLISHES_KEY, "")
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return 0
    if not isinstance(value, dict) or str(value.get("cycle", "")) != _cycle_id():
        return 0
    try:
        return int(value.get("count", 0) or 0)
    except (ValueError, TypeError):
        return 0


# ── Rules ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _GateCtx:
    """Everything the three rules need about one guarded ``tool_call``.

    :param tool: The guarded tool being called.
    :param slug: The backlog slug from the call arguments.
    :param channel: The ``post_social`` channel, ``""`` for ``publish_content``.
    :param approved: Slugs already seen reach ``APPROVED`` this session.
    :param publishes: Successful publishes already seen this cycle.
    :param max_publishes_per_cycle: The batch-publish ceiling.
    """

    tool: str
    slug: str
    channel: str
    approved: tuple[str, ...]
    publishes: int
    max_publishes_per_cycle: int


def _artifact_kind(ctx: _GateCtx) -> str:
    """Name the artifact a guarded call is about to ship, for the ASK reason.

    :param ctx: The gate context.
    :returns: A human-readable artifact description.
    """
    if ctx.tool == _POST_SOCIAL:
        channel = ctx.channel or "social"
        return f"{channel} short-form post"
    return "long-form blog draft (plus any staged social variants)"


def _rule_r1_social_before_approval(ctx: _GateCtx) -> PolicyResponse | None:
    """R1 — DENY short-form content that would precede its long-form post.

    :param ctx: The gate context.
    :returns: A DENY response, or ``None`` when the rule does not apply.
    """
    if ctx.tool != _POST_SOCIAL or ctx.slug in ctx.approved:
        return None
    return {
        "result": "DENY",
        "reason": (
            f"Publish gate: posting social content for '{ctx.slug}' is denied. "
            f"No successful update_backlog(slug='{ctx.slug}', "
            f"status='{_APPROVED_STATUS}') has been seen in this session, so the "
            f"blog post for '{ctx.slug}' is not approved yet. Short-form content "
            f"cannot precede the long-form post it cites."
        ),
    }


def _rule_r2_shipping_needs_signature(ctx: _GateCtx) -> PolicyResponse | None:
    """R2 — ASK on any other publish or post call.

    :param ctx: The gate context.
    :returns: An ASK response, or ``None`` when the rule does not apply.
    """
    if ctx.tool not in _GUARDED_TOOLS:
        return None
    return {
        "result": "ASK",
        "reason": (
            f"Publish gate: {ctx.tool} is about to ship the {_artifact_kind(ctx)} "
            f"for '{ctx.slug}'. Drafting, editing and staging run unattended, but "
            f"publication requires a human signature. Approve?"
        ),
    }


def _rule_r3_batch_ceiling(ctx: _GateCtx) -> PolicyResponse | None:
    """R3 — ASK once the cycle's batch-publish ceiling has been reached.

    Note on precedence: the contract fixes the rule order as R1, R2, R3, and
    R2 matches *every* guarded tool. R3 is therefore a backstop that the
    stated order never reaches — see this module's note in the PR. It is kept
    as a live predicate rather than folded into R2 so the ceiling stays an
    explicit, separately-reasoned rule; moving it ahead of R2 is the one-line
    change that makes its reason surface.

    :param ctx: The gate context.
    :returns: An ASK response, or ``None`` when the rule does not apply.
    """
    if ctx.tool not in _GUARDED_TOOLS or ctx.publishes < ctx.max_publishes_per_cycle:
        return None
    return {
        "result": "ASK",
        "reason": (
            f"Publish gate: batch-publish ceiling reached — {ctx.publishes} "
            f"successful publishes already in cycle {_cycle_id()} (limit: "
            f"{ctx.max_publishes_per_cycle}). {ctx.tool} for '{ctx.slug}' needs a "
            f"fresh human signature before this cycle ships anything else. Approve?"
        ),
    }


_RULES = (
    _rule_r1_social_before_approval,
    _rule_r2_shipping_needs_signature,
    _rule_r3_batch_ceiling,
)


# ── Phase handlers ───────────────────────────────────────────────────────────


def _decide_tool_call(event: PolicyEvent, max_publishes_per_cycle: int) -> PolicyResponse:
    """Apply R1 → R2 → R3 to a ``tool_call`` event.

    :param event: The ``tool_call`` policy event.
    :param max_publishes_per_cycle: The batch-publish ceiling.
    :returns: The first matching rule's verdict, else ALLOW.
    """
    tool = _tool_name(event)
    # The free-flowing tier short-circuits before any rule can see it, so no
    # future rule can accidentally gate the ungated tools.
    if tool in _UNGATED_TOOLS or tool not in _GUARDED_TOOLS:
        return _ALLOW

    args = _tool_args(event.get("data"))
    state = event.get("session_state") or {}
    ctx = _GateCtx(
        tool=tool,
        slug=str(args.get("slug", "")).strip() or "(no slug given)",
        channel=str(args.get("channel", "")).strip(),
        approved=tuple(_approved_slugs(state)),
        publishes=_cycle_publishes(state),
        max_publishes_per_cycle=max_publishes_per_cycle,
    )

    for rule in _RULES:
        decision = rule(ctx)
        if decision is not None:
            return decision
    return _ALLOW


def _record_approved_slug(event: PolicyEvent, payload: object) -> PolicyResponse:
    """Record a slug that just reached ``APPROVED``, so R1 can let it through.

    :param event: The ``update_backlog`` ``tool_result`` event.
    :param payload: Its parsed result payload.
    :returns: ALLOW, carrying a ``state_updates`` entry when a new slug was
        approved.
    """
    if not _succeeded(payload):
        return _ALLOW
    result = payload if isinstance(payload, dict) else {}
    slug = str(result.get("slug", "")).strip()
    status = str(result.get("new_status", "")).strip().upper()
    if status != _APPROVED_STATUS:
        # Fall back to the originating call's arguments (server path only).
        args = _tool_args(event.get("request_data"))
        status = str(args.get("status", "")).strip().upper()
        slug = slug or str(args.get("slug", "")).strip()
    if status != _APPROVED_STATUS or not slug:
        return _ALLOW

    seen = _approved_slugs(event.get("session_state") or {})
    if slug in seen:
        return _ALLOW
    return {
        "result": "ALLOW",
        "state_updates": [
            {
                "key": _APPROVED_SLUGS_KEY,
                "action": "set",
                "value": json.dumps([*seen, slug]),
            },
        ],
    }


def _record_publish(event: PolicyEvent, payload: object) -> PolicyResponse:
    """Count a successful publish against the current cycle's ceiling.

    :param event: The ``publish_content`` / ``post_social`` ``tool_result`` event.
    :param payload: Its parsed result payload.
    :returns: ALLOW, carrying a ``state_updates`` entry on success.
    """
    if not _succeeded(payload):
        return _ALLOW
    count = _cycle_publishes(event.get("session_state") or {}) + 1
    return {
        "result": "ALLOW",
        "state_updates": [
            {
                "key": _CYCLE_PUBLISHES_KEY,
                "action": "set",
                "value": json.dumps({"cycle": _cycle_id(), "count": count}),
            },
        ],
    }


def _decide_tool_result(event: PolicyEvent) -> PolicyResponse:
    """Record session state from a completed tool call. Never gates.

    :param event: The ``tool_result`` policy event.
    :returns: An ALLOW response, with ``state_updates`` when there is
        something to remember.
    """
    tool = _tool_name(event)
    if tool not in {_UPDATE_BACKLOG, *_GUARDED_TOOLS}:
        return _ALLOW
    payload = _result_payload(event.get("data"))
    if tool == _UPDATE_BACKLOG:
        return _record_approved_slug(event, payload)
    return _record_publish(event, payload)


# ── Factory ──────────────────────────────────────────────────────────────────


def publish_gate(
    *,
    max_publishes_per_cycle: int = 3,
) -> PolicyCallable:
    """Factory: gate publication while leaving drafting and staging free.

    :param max_publishes_per_cycle: Successful publishes allowed in one daily
        cycle before the batch-publish ceiling rule applies.
    :returns: A one-argument policy callable.
    """

    def evaluate(event: PolicyEvent) -> PolicyResponse:
        phase = event.get("type")
        if phase == "tool_call":
            return _decide_tool_call(event, max_publishes_per_cycle)
        if phase == "tool_result":
            return _decide_tool_result(event)
        return _ALLOW

    return evaluate  # type: ignore[return-value]


POLICY_REGISTRY: list[dict[str, Any]] = [  # type: ignore[explicit-any]
    {
        "handler": (
            "examples.content_factory.policies.publish_gate.publish_gate"
        ),
        "kind": "factory",
        "name": "Content Factory Publish Gate",
        "description": (
            "DENIES short-form social posts for a slug whose long-form post is "
            "not yet APPROVED, ASKs on every publish_content / post_social "
            "call, and ASKs again once a cycle's batch-publish ceiling is "
            "reached. Drafting, editing and artifact staging stay ungated."
        ),
        "params_schema": {
            "type": "object",
            "properties": {
                "max_publishes_per_cycle": {
                    "type": "integer",
                    "description": "Successful publishes per cycle before the ceiling ASK",
                    "default": 3,
                },
            },
        },
    },
]
