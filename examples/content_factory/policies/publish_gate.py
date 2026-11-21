"""Custom policy: the content factory's publish gate.

Unattended cycles produce freely: ``read_backlog`` and ``save_artifact`` are
never gated, and neither is ``update_backlog`` for any status that describes
work in progress. Shipping is different. ``publish_content`` and
``post_social`` face three rules (R1, R3, R2), and a fourth rule R4 checks the
one ``update_backlog`` call that is not a description of work but a *claim that
the work finished*: the terminal ``PUBLISHED`` status.

So the tiers are still "produce freely, ship under supervision" — R4 does not
gate any work, it only refuses to record a completion that did not happen, and
it does so with a DENY rather than an ASK, so no human is ever added to the
unattended path.

All cross-turn state lives in ``session_state``, mutated only through
``state_updates``, under two deliberately separate scopes:

- ``_publish_gate_cycle_slugs`` — CYCLE-scoped (one UTC day). The ceiling's
  record. Resets at midnight, which is the point of it.
- ``_publish_gate_ship_progress`` — SESSION-scoped, per slug. What this session
  has actually watched ship. R4's record. Never resets inside a session,
  because an article does not become unshipped at midnight.

Mixing those two scopes would be a bug: see R4's docstring.
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
# Holds {<slug>: {"staged": [...], "published": bool, "posted": [...]}} — what
# this SESSION has watched actually ship, per article. Deliberately NOT
# cycle-scoped: R4 asks "did this ship?", and the answer does not change at
# midnight the way the ceiling's does.
_SHIP_PROGRESS_KEY = "_publish_gate_ship_progress"

_PUBLISH_CONTENT = "publish_content"
_POST_SOCIAL = "post_social"
_UPDATE_BACKLOG = "update_backlog"
_SAVE_ARTIFACT = "save_artifact"
_GUARDED_TOOLS = frozenset({_PUBLISH_CONTENT, _POST_SOCIAL})
_APPROVED_STATUS = "APPROVED"
_PUBLISHED_STATUS = "PUBLISHED"
# The channels post_social accepts, and therefore the social variants
# save_artifact can stage. Kept in sync with both tools by hand.
_SOCIAL_CHANNELS = ("x", "linkedin")


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


def _ship_progress(state: dict[str, object]) -> dict[str, dict[str, object]]:
    """Per-slug shipping progress this session has witnessed.

    Shape: ``{slug: {"staged": [...], "published": bool, "posted": [...]}}``.
    Decoded defensively — a corrupt or foreign value reads as "nothing has
    shipped", which makes R4 fail closed.
    """
    value = _read_state(state, _SHIP_PROGRESS_KEY)
    if not isinstance(value, dict):
        return {}
    progress: dict[str, dict[str, object]] = {}
    for slug, entry in value.items():
        if isinstance(entry, dict):
            progress[str(slug)] = dict(entry)
    return progress


def _entry_channels(entry: dict[str, object], key: str) -> list[str]:
    """Read a channel list out of one progress entry."""
    value = entry.get(key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item) in _SOCIAL_CHANNELS]


def _ship_completion(progress: dict[str, dict[str, object]], slug: str) -> tuple[bool, str]:
    """Has ``slug`` FULLY shipped in this session? Plus why not, if not.

    "Fully" is the whole point of R4, and it means two things together:

    1. ``publish_content`` succeeded for the slug, and
    2. every social variant the cycle STAGED for it was then posted.

    Condition 2 is keyed on what was staged rather than on a fixed list of
    channels, because a cycle may legitimately produce only one variant — and
    a post that was never written cannot be demanded. The honest limit of that
    choice: an article for which NO social variant was staged counts as
    complete once published, so R4 cannot tell "this article had no social
    copy by design" from "step 10 was skipped entirely". It still catches the
    realistic failure, which is social copy staged and then never posted.
    """
    entry = progress.get(slug) or {}
    if not entry:
        return False, (
            "this session has recorded no successful publish_content or "
            "post_social for it at all"
        )
    if not entry.get("published"):
        return False, "publish_content has not succeeded for it in this session"
    posted = set(_entry_channels(entry, "posted"))
    outstanding = [
        channel for channel in _entry_channels(entry, "staged") if channel not in posted
    ]
    if outstanding:
        return False, (
            f"publish_content succeeded, but the staged {', '.join(outstanding)} "
            f"post(s) were never posted — the article is only half shipped"
        )
    return True, ""


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


def _decide_published_claim(
    event: PolicyEvent, args: dict[str, Any], state: dict[str, object]
) -> PolicyResponse:  # type: ignore[explicit-any]
    """R4 — DENY a ``PUBLISHED`` claim this session cannot show actually shipped.

    ``PUBLISHED`` is the one ``update_backlog`` status that is not a
    description of work but an assertion that the work finished — and it is
    the status a status dashboard reads. Step 13 of the supervisor prompt is
    the only thing that orders it correctly, and a prompt is not enforcement:
    a model under pressure can write it optimistically. R4 makes it
    structural.

    Scope matters, and getting it wrong here produces FALSE DENIALS of
    legitimate writes. Two records could back this rule and only one is
    right:

    - the ceiling's ``_publish_gate_cycle_slugs`` is CYCLE-scoped and resets
      at UTC midnight, so a publish at 23:59 and its status write at 00:01
      would be refused — and the first call of each new cycle would reset it
      out from under a perfectly good article.
    - ``_publish_gate_ship_progress`` is SESSION-scoped, and in the normal
      flow the publish and this write happen in the same session moments
      apart (steps 12 and 13).

    So R4 reads the session-scoped record, matching R1's existing scope: one
    story for "what this session witnessed", with the cycle scope left to the
    ceiling that needs it.

    When a LEGITIMATE ``PUBLISHED`` write is still refused: when the publish
    happened in a DIFFERENT session from the status write. The daily schedule
    uses ``session_mode: new``, so if a cycle ships an article and then dies
    before step 13, a later session cannot close the entry out — exactly as a
    later session cannot post social copy for an article it did not watch
    reach ``APPROVED`` (R1). Re-run the cycle, or edit ``backlog.md`` by hand.

    And what R4 is NOT: a security boundary. It gates a tool call, so it says
    nothing about an agent that edits ``backlog.md`` directly and never calls
    ``update_backlog`` at all. The caveat still holds; only its mechanism has
    changed. It used to be the supervisor's own ``os_env: caller_process`` with
    ``sandbox: none``, which handed it the framework's ``sys_os_*`` tools --
    and a real run used exactly that to rewrite a sub-agent's config. No agent
    in this bundle declares ``os_env`` now. What remains is ``blog_writer``,
    which runs ``harness: codex``: Codex's own ``apply_patch`` is not an
    Omnigent tool, is not gated by any policy (native calls arrive already
    executed), and can write anywhere in the workspace. So the supervisor is
    one delegation hop from a direct ``backlog.md`` edit. R4 raises the floor
    on careless optimism; it does not stop a determined agent.
    """
    status = str(args.get("status", "")).strip().upper()
    # Every other status describes work in progress and stays free: READY,
    # DRAFTED, EDITED and APPROVED are never gated on any path.
    if status != _PUBLISHED_STATUS:
        return _ALLOW

    # Stateful, so it defers on the runner-local path exactly as R1 and R3 do
    # — a rule that DENIED on permanently-absent state would fail every
    # PUBLISHED write there. Note the honest cost, which R1 does not pay:
    # there is no coarse backstop on update_backlog, so a deferred R4 means
    # the write goes through unchecked locally.
    if not _state_available(event):
        return _ALLOW

    slug = str(args.get("slug", "")).strip() or "(no slug given)"
    complete, unfinished_because = _ship_completion(_ship_progress(state), slug)
    if complete:
        return _ALLOW
    return {
        "result": "DENY",
        "reason": (
            f"Refusing to record '{slug}' as {_PUBLISHED_STATUS}: "
            f"{unfinished_because}. {_PUBLISHED_STATUS} is a record of what "
            f"shipped, not of what was intended, so it is only written once "
            f"publish_content and every staged social post have actually "
            f"succeeded in this session. Leave the entry at "
            f"{_APPROVED_STATUS} and report what did not ship."
        ),
    }


def _decide_tool_call(event: PolicyEvent, max_articles_per_cycle: int) -> PolicyResponse:
    """Apply R4, then R1 (DENY), R3 (DENY) and R2 (ASK), to a ``tool_call``."""
    tool = _tool_name(event)
    args = _tool_args(event.get("data"))
    state = event.get("session_state") or {}

    # R4 targets a DIFFERENT tool from R1/R3's guarded pair, so it is its own
    # early branch rather than a condition threaded through the chain below.
    if tool == _UPDATE_BACKLOG:
        return _decide_published_claim(event, args, state)

    # The rest of the producing tier — read_backlog and save_artifact — is
    # absent from _GUARDED_TOOLS and falls out here, ungated, on every call.
    if tool not in _GUARDED_TOOLS:
        return _ALLOW

    slug = str(args.get("slug", "")).strip() or "(no slug given)"

    # R1 and R3 are stateful, and only the server engine persists state. The
    # runner-local gate builds a fresh EvaluationContext per call and drops
    # returned state_updates (runner/policy.py), so its session_state is
    # permanently {} — deciding R1 there would deny EVERY post_social, a
    # properly approved one included. All three stateful rules therefore defer
    # when state is unavailable (R4 does the same, above) rather than judge on
    # state known to be missing. Not a hole here: stateless R2 below still ASKs
    # on every guarded call there, as does the guarded_tools risk_score layer.
    # A present-but-empty state on the server is a different case and still
    # denies — that is R1's point.
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
        if slug not in shipped and len(shipped) >= max_articles_per_cycle:
            return {
                "result": "DENY",
                "reason": (
                    f"Per-cycle article ceiling reached: {len(shipped)} article(s) "
                    f"already shipped in cycle {_cycle_id()} (limit "
                    f"{max_articles_per_cycle} per cycle), and '{slug}' is not "
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


def _set_state(key: str, value: object) -> dict[str, object]:
    """One ``state_updates`` entry, JSON-encoded like the rest of this policy."""
    return {"key": key, "action": "set", "value": json.dumps(value)}


def _call_field(event: PolicyEvent, payload: object, field: str) -> str:
    """Read one field from a tool result, falling back to the call arguments."""
    result = payload if isinstance(payload, dict) else {}
    value = str(result.get(field, "")).strip()
    if value:
        return value
    # The server path carries the originating call; the runner-local one does
    # not, but its state_updates are discarded anyway.
    return str(_tool_args(event.get("request_data")).get(field, "")).strip()


def _staged_social_target(event: PolicyEvent, payload: object) -> tuple[str, str]:
    """``(slug, variant)`` for a successful social ``save_artifact``, else ``("", "")``.

    ``save_artifact`` returns only ``{path, bytes, kind}``, so the slug and
    variant come from the originating arguments where available and from the
    staged path otherwise. The path is unambiguous even for slugs containing
    hyphens, because the suffix is matched against the known channel names.
    """
    args = _tool_args(event.get("request_data"))
    if str(args.get("kind", "")).strip().lower() == "social":
        slug = str(args.get("slug", "")).strip()
        variant = str(args.get("variant", "")).strip().lower()
        if slug and variant in _SOCIAL_CHANNELS:
            return slug, variant

    result = payload if isinstance(payload, dict) else {}
    if str(result.get("kind", "")).strip().lower() != "social":
        return "", ""
    name = str(result.get("path", "")).replace("\\", "/").rsplit("/", 1)[-1]
    for channel in _SOCIAL_CHANNELS:
        suffix = f"-{channel}.md"
        if name.endswith(suffix) and len(name) > len(suffix):
            return name[: -len(suffix)], channel
    return "", ""


def _record_staged_social(event: PolicyEvent, payload: object) -> PolicyResponse:
    """Record that a social variant was staged, so R4 knows what owes a post.

    ``save_artifact`` itself stays ungated — this is bookkeeping on its
    *result*, and it is what lets R4 distinguish "this article had no social
    copy" from "its social copy was written and never posted".
    """
    if not _succeeded(payload):
        return _ALLOW
    slug, variant = _staged_social_target(event, payload)
    if not slug:
        return _ALLOW

    progress = _ship_progress(event.get("session_state") or {})
    entry = dict(progress.get(slug) or {})
    staged = _entry_channels(entry, "staged")
    if variant in staged:
        return _ALLOW
    entry["staged"] = [*staged, variant]
    progress[slug] = entry
    return {
        "result": "ALLOW",
        "state_updates": [_set_state(_SHIP_PROGRESS_KEY, progress)],
    }


def _record_shipping_progress(
    event: PolicyEvent, tool: str, payload: object
) -> PolicyResponse:
    """Record a successful shipping call against both shipping records.

    Two updates, two scopes, deliberately not merged:

    - the CYCLE-scoped ceiling set gains the slug on its FIRST successful
      guarded call, so the set size counts articles rather than calls.
    - the SESSION-scoped progress entry gains the specific fact that just
      became true — ``published``, or one posted channel — so R4 can tell a
      finished article from a half-shipped one.
    """
    if not _succeeded(payload):
        return _ALLOW
    slug = _call_field(event, payload, "slug")
    if not slug:
        return _ALLOW
    state = event.get("session_state") or {}
    updates: list[dict[str, object]] = []

    shipped = _cycle_shipped_slugs(state)
    if slug not in shipped:
        updates.append(
            _set_state(_CYCLE_SLUGS_KEY, {"cycle": _cycle_id(), "slugs": [*shipped, slug]})
        )

    progress = _ship_progress(state)
    entry = dict(progress.get(slug) or {})
    advanced = False
    if tool == _PUBLISH_CONTENT and not entry.get("published"):
        entry["published"] = True
        advanced = True
    elif tool == _POST_SOCIAL:
        channel = _call_field(event, payload, "channel").lower()
        posted = _entry_channels(entry, "posted")
        if channel in _SOCIAL_CHANNELS and channel not in posted:
            entry["posted"] = [*posted, channel]
            advanced = True
    if advanced:
        progress[slug] = entry
        updates.append(_set_state(_SHIP_PROGRESS_KEY, progress))

    if not updates:
        return _ALLOW
    return {"result": "ALLOW", "state_updates": updates}


def _decide_tool_result(event: PolicyEvent) -> PolicyResponse:
    """Record session state from a completed call.

    *This* policy never gates a tool result, only ever returning ALLOW here.
    The framework does allow gating one: the server withholds or suppresses
    output on ASK / DENY and the runner collapses a result ASK into a denial.
    """
    tool = _tool_name(event)
    if tool not in {_UPDATE_BACKLOG, _SAVE_ARTIFACT, *_GUARDED_TOOLS}:
        return _ALLOW
    payload = _result_payload(event.get("data"))
    if tool == _UPDATE_BACKLOG:
        return _record_approved_slug(event, payload)
    if tool == _SAVE_ARTIFACT:
        return _record_staged_social(event, payload)
    return _record_shipping_progress(event, tool, payload)


def publish_gate(
    *,
    max_articles_per_cycle: int = 3,
) -> PolicyCallable:
    """Factory: gate publication while leaving drafting and staging free.

    :param max_articles_per_cycle: Distinct articles (backlog slugs) that may
        be shipped in one daily cycle. Once that many have shipped, the first
        guarded call for a NEW slug is refused until the next cycle; slugs
        already counted may still finish their remaining posts. Note this
        caps the articles a cycle may START, not the number of shipping
        actions: an article already counted can be re-shipped within the same
        cycle, though R2 still ASKs on every one of those calls.
    :returns: A one-argument policy callable.
    """

    def evaluate(event: PolicyEvent) -> PolicyResponse:
        phase = event.get("type")
        if phase == "tool_call":
            return _decide_tool_call(event, max_articles_per_cycle)
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
            "publish_content / post_social call. Also DENIES an "
            "update_backlog PUBLISHED claim for an article this session did "
            "not watch fully ship. Drafting, editing and artifact staging stay "
            "ungated, as does update_backlog for every status other than "
            "PUBLISHED."
        ),
        "params_schema": {
            "type": "object",
            "properties": {
                "max_articles_per_cycle": {
                    "type": "integer",
                    "description": (
                        "Distinct articles (slugs) a cycle may start shipping before a "
                        "new one is refused"
                    ),
                    "default": 3,
                },
            },
        },
    },
]
