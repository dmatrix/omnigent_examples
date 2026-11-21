"""Custom policy: the content factory's publish gate.

Unattended cycles produce freely — ``read_backlog``, ``update_backlog`` and
``save_artifact`` are never gated. Shipping is different: ``publish_content``
and ``post_social`` face three rules, and cross-turn state lives in
``session_state``, mutated only through ``state_updates``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from omnigent.policies.schema import PolicyCallable, PolicyEvent, PolicyResponse

# An explicit ALLOW, not ``None``. There is no distinct ABSTAIN verdict:
# ``_coerce_to_policy_result`` (policies/function.py) maps ``None`` to ALLOW and
# calls it a "defensive fallback". ALLOW masks nothing — the engine accumulates
# ASKs across policies and short-circuits only on DENY.
_ALLOW: PolicyResponse = {"result": "ALLOW"}

# ``session_state`` keys. Deliberately NOT prefixed ``_policy_`` — the engine
# reserves that prefix for approval checkpoints it writes itself.
_APPROVED_SLUGS_KEY = "_publish_gate_approved_slugs"
# Holds {"cycle": <UTC date>, "slugs": [...]} — the DISTINCT articles shipped
# in the current cycle. Renamed from ``_publish_gate_cycle_publishes``, which
# held a call count, so a stale value from that shape is never half-parsed.
_CYCLE_SLUGS_KEY = "_publish_gate_cycle_slugs"

_PUBLISH_CONTENT = "publish_content"
_POST_SOCIAL = "post_social"
_UPDATE_BACKLOG = "update_backlog"
_GUARDED_TOOLS = frozenset({_PUBLISH_CONTENT, _POST_SOCIAL})
_APPROVED_STATUS = "APPROVED"


def _tool_name(event: PolicyEvent) -> str:
    """Resolve the tool identity across both enforcement paths.

    Prefer ``target`` (the dispatched identity, which an earlier policy cannot
    have rewritten); fall back to the payload, which the runner-local inner
    gate shapes differently from the server engine.
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
    """Extract a tool-call argument dict from an event payload."""
    if not isinstance(data, dict):
        return {}
    args = data.get("arguments")
    # Inner path: ``data`` already *is* the argument dict.
    return args if isinstance(args, dict) else data


def _result_payload(data: object) -> object:
    """Parse a ``tool_result`` payload, server- or runner-shaped."""
    inner = data["result"] if isinstance(data, dict) and "result" in data else data
    if isinstance(inner, str):
        try:
            return json.loads(inner)
        except (ValueError, TypeError):
            return inner
    return inner


def _succeeded(payload: object) -> bool:
    """True only for a result dict carrying no ``error``.

    Every content-factory tool returns a dict and flags failure with ``error``.
    Anything else counts as failure, so this gate fails closed: an unconfirmed
    ``update_backlog`` never unlocks ``post_social``.
    """
    return isinstance(payload, dict) and not payload.get("error")


def _state_available(event: PolicyEvent) -> bool:
    """Whether this event's ``session_state`` is authoritative.

    ``_build_event`` (policies/function.py) flattens an absent
    ``session_state`` to ``{}``, so an empty dict alone is ambiguous: "server
    engine, nothing approved yet" or "runner-local gate, no state at all".
    ``conversation_id`` disambiguates — the engine injects it on every
    ``evaluate`` (runtime/policies/engine.py) and it is documented as ``None``
    "only in contexts with no engine", i.e. exactly the runner-local gate.
    """
    context = event.get("context") or {}
    conversation_id = context.get("conversation_id")
    return isinstance(conversation_id, str) and bool(conversation_id)


def _read_state(state: dict[str, object], key: str) -> object:
    """Decode one ``session_state`` value; ``None`` when absent or corrupt."""
    raw = state.get(key)
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return None


def _approved_slugs(state: dict[str, object]) -> list[str]:
    """Slugs this session has seen reach ``APPROVED``."""
    value = _read_state(state, _APPROVED_SLUGS_KEY)
    return [str(item) for item in value] if isinstance(value, list) else []


def _cycle_id() -> str:
    """The current cycle: cycles are daily, so the UTC day is the identity."""
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _cycle_shipped_slugs(state: dict[str, object]) -> list[str]:
    """Distinct article slugs shipped in the current cycle; empty if stale.

    A stored cycle that is not today's is ignored rather than migrated, which
    is what makes the ceiling reset on its own at the UTC day boundary.
    """
    value = _read_state(state, _CYCLE_SLUGS_KEY)
    if not isinstance(value, dict) or str(value.get("cycle", "")) != _cycle_id():
        return []
    slugs = value.get("slugs")
    if not isinstance(slugs, list):
        return []
    return [str(item) for item in slugs]


def _artifact_kind(tool: str, channel: str) -> str:
    """Name the artifact a guarded call is about to ship."""
    if tool == _POST_SOCIAL:
        return f"{channel or 'social'} short-form post"
    return "long-form blog draft (plus any staged social variants)"


def _decide_tool_call(event: PolicyEvent, max_publishes_per_cycle: int) -> PolicyResponse:
    """Apply R1 (DENY) then R3 (DENY) then R2 (ASK) to a ``tool_call`` event."""
    tool = _tool_name(event)
    # The producing tier — read_backlog, update_backlog, save_artifact — is
    # absent from _GUARDED_TOOLS and falls out here, ungated, on every call.
    if tool not in _GUARDED_TOOLS:
        return _ALLOW

    args = _tool_args(event.get("data"))
    slug = str(args.get("slug", "")).strip() or "(no slug given)"
    state = event.get("session_state") or {}

    # R1 and R3 are stateful, and only the server engine persists state. The
    # runner-local gate builds a fresh EvaluationContext per call and drops
    # returned state_updates (runner/policy.py), so its session_state is
    # permanently {} — deciding R1 there would deny EVERY post_social, a
    # properly approved one included. Both stateful rules therefore defer when
    # state is unavailable rather than judge on state known to be missing. Not
    # a hole: stateless R2 below still ASKs on every guarded call there, as
    # does the guarded_tools risk_score layer. A present-but-empty state on
    # the server is a different case and still denies — that is R1's point.
    if _state_available(event):
        # R1 — short-form content may not precede the post it cites.
        if tool == _POST_SOCIAL and slug not in _approved_slugs(state):
            return {
                "result": "DENY",
                "reason": (
                    f"Posting social content for '{slug}' is denied: no successful "
                    f"update_backlog(slug='{slug}', status='{_APPROVED_STATUS}') in "
                    f"this session, so the blog post for '{slug}' is not approved "
                    f"yet. Short-form content cannot precede the long-form post it "
                    f"cites."
                ),
            }

        # R3 — the cycle's ceiling is a hard stop, not a prompt, and it counts
        # ARTICLES (distinct slugs) rather than guarded calls. Shipping one
        # article fully is normally three guarded calls — publish_content plus
        # a post_social per channel — so counting calls would hard-stop the
        # second article partway through. The rule is therefore: you may
        # FINISH an article you have already started, but you may not START a
        # new one past the ceiling. A slug already in this cycle's shipped set
        # is never refused here, so no article is left published with its
        # social copy stranded.
        shipped = _cycle_shipped_slugs(state)
        if slug not in shipped and len(shipped) >= max_publishes_per_cycle:
            return {
                "result": "DENY",
                "reason": (
                    f"Per-cycle article ceiling reached: {len(shipped)} article(s) "
                    f"already shipped in cycle {_cycle_id()} (limit "
                    f"{max_publishes_per_cycle} per cycle), and '{slug}' is not "
                    f"one of them. {tool} for '{slug}' is refused until the next "
                    f"cycle. Articles already started in this cycle may still be "
                    f"finished."
                ),
            }

    # R2 — anything else that ships needs a human signature.
    channel = str(args.get("channel", "")).strip()
    return {
        "result": "ASK",
        "reason": (
            f"{tool} is about to ship the {_artifact_kind(tool, channel)} for "
            f"'{slug}'. Drafting, editing and staging run unattended, but "
            f"publication requires a human signature. Approve?"
        ),
    }


def _record_approved_slug(event: PolicyEvent, payload: object) -> PolicyResponse:
    """Record a slug that just reached ``APPROVED``, so R1 can pass it."""
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
    value = json.dumps([*seen, slug])
    return {
        "result": "ALLOW",
        "state_updates": [{"key": _APPROVED_SLUGS_KEY, "action": "set", "value": value}],
    }


def _record_shipped_slug(event: PolicyEvent, payload: object) -> PolicyResponse:
    """Count a successful shipping call's slug against the cycle's ceiling.

    The first guarded call for a slug puts it in the cycle's shipped set; the
    rest of that article's calls find it already there and add nothing. So the
    set size is the number of ARTICLES shipped this cycle, however many
    publish_content / post_social calls each one took.
    """
    if not _succeeded(payload):
        return _ALLOW
    result = payload if isinstance(payload, dict) else {}
    slug = str(result.get("slug", "")).strip()
    if not slug:
        # Fall back to the originating call's arguments (server path only).
        slug = str(_tool_args(event.get("request_data")).get("slug", "")).strip()
    if not slug:
        return _ALLOW

    shipped = _cycle_shipped_slugs(event.get("session_state") or {})
    if slug in shipped:
        return _ALLOW
    value = json.dumps({"cycle": _cycle_id(), "slugs": [*shipped, slug]})
    return {
        "result": "ALLOW",
        "state_updates": [{"key": _CYCLE_SLUGS_KEY, "action": "set", "value": value}],
    }


def _decide_tool_result(event: PolicyEvent) -> PolicyResponse:
    """Record session state from a completed call.

    *This* policy never gates a tool result, only ever returning ALLOW here.
    The framework does allow gating one: the server withholds or suppresses
    output on ASK / DENY and the runner collapses a result ASK into a denial.
    """
    tool = _tool_name(event)
    if tool not in {_UPDATE_BACKLOG, *_GUARDED_TOOLS}:
        return _ALLOW
    payload = _result_payload(event.get("data"))
    if tool == _UPDATE_BACKLOG:
        return _record_approved_slug(event, payload)
    return _record_shipped_slug(event, payload)


def publish_gate(
    *,
    max_publishes_per_cycle: int = 3,
) -> PolicyCallable:
    """Factory: gate publication while leaving drafting and staging free.

    :param max_publishes_per_cycle: Distinct articles (backlog slugs) that may
        be shipped in one daily cycle. Once that many have shipped, the first
        guarded call for a NEW slug is refused until the next cycle; slugs
        already counted may still finish their remaining posts.
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
        "handler": "examples.content_factory.policies.publish_gate.publish_gate",
        "kind": "factory",
        "name": "Content Factory Publish Gate",
        "description": (
            "DENIES short-form social posts for a slug whose long-form post is "
            "not yet APPROVED, DENIES shipping a NEW article once a cycle's "
            "article ceiling is reached — articles already started in that "
            "cycle may still be finished — and ASKs on every other "
            "publish_content / post_social call. Drafting, editing and artifact "
            "staging stay ungated."
        ),
        "params_schema": {
            "type": "object",
            "properties": {
                "max_publishes_per_cycle": {
                    "type": "integer",
                    "description": (
                        "Distinct articles (slugs) shippable per cycle before a new one "
                        "is refused"
                    ),
                    "default": 3,
                },
            },
        },
    },
]
