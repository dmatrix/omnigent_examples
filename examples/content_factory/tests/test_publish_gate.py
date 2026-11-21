"""Executable spec for ``policies/publish_gate.py``.

Four interacting rules over two differently-scoped pieces of session state is
more than a reader can verify by eye, so the behaviour is pinned here.

Run it either way::

    python examples/content_factory/tests/test_publish_gate.py
    pytest examples/content_factory/tests/

Stdlib only. The policy imports ``omnigent.policies.schema`` for its type
aliases; if Omnigent is not installed, a stub stands in for those names (they
are annotations only, never evaluated at runtime) so the suite still runs on a
bare checkout.

This directory is NOT ``tools/python/``, so nothing here is auto-discovered as
an agent tool -- keep it that way.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from datetime import UTC, datetime, timedelta
from pathlib import Path

EXAMPLE_ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = EXAMPLE_ROOT / "policies" / "publish_gate.py"


def _load_policy_module() -> types.ModuleType:
    """Import the policy by path, stubbing its type-only dependency if needed."""
    try:  # pragma: no cover - depends on the environment, not the policy
        import omnigent.policies.schema  # noqa: F401
    except ImportError:
        schema = types.ModuleType("omnigent.policies.schema")
        for name in ("PolicyCallable", "PolicyEvent", "PolicyResponse"):
            setattr(schema, name, dict)
        policies = types.ModuleType("omnigent.policies")
        policies.schema = schema  # type: ignore[attr-defined]
        omnigent = types.ModuleType("omnigent")
        omnigent.policies = policies  # type: ignore[attr-defined]
        sys.modules.setdefault("omnigent", omnigent)
        sys.modules.setdefault("omnigent.policies", policies)
        sys.modules.setdefault("omnigent.policies.schema", schema)

    spec = importlib.util.spec_from_file_location("publish_gate_under_test", POLICY_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pg = _load_policy_module()

MAX_ARTICLES = 3
SERVER = {"conversation_id": "conv-under-test"}  # state is authoritative
RUNNER_LOCAL = {"conversation_id": None}  # no engine, no persisted state


# ── a miniature policy engine ───────────────────────────────────────────────


def gate():
    """A fresh policy callable at the documented default ceiling."""
    return pg.publish_gate(max_articles_per_cycle=MAX_ARTICLES)


class Session:
    """One conversation's ``session_state`` plus the engine's SET semantics.

    Mirrors ``PolicyEngine.apply_state_updates``: SET overwrites, and updates
    returned alongside an ASK are withheld (the engine does not persist state
    for a call that has not been approved yet).
    """

    def __init__(self, context: dict[str, object] | None = None) -> None:
        self.state: dict[str, object] = {}
        self.context = SERVER if context is None else context
        self.evaluate = gate()

    # -- phases ----------------------------------------------------------

    def call(self, tool: str, **arguments: object) -> dict[str, object]:
        """A ``tool_call`` event: the gating decision, no state applied."""
        return self.evaluate(
            {
                "type": "tool_call",
                "target": tool,
                "data": {"name": tool, "arguments": arguments},
                "context": self.context,
                "session_state": self.state,
            }
        )

    def result(self, tool: str, payload: dict[str, object], **arguments: object):
        """A ``tool_result`` event, with any ``state_updates`` applied."""
        response = self.evaluate(
            {
                "type": "tool_result",
                "target": tool,
                # Tool output reaches the policy JSON-encoded on the server path.
                "data": {"result": json.dumps(payload)},
                "request_data": {"name": tool, "arguments": arguments},
                "context": self.context,
                "session_state": self.state,
            }
        )
        self._apply(response)
        return response

    def _apply(self, response: dict[str, object]) -> None:
        if response.get("result") == "ASK":
            return
        for update in response.get("state_updates") or []:
            assert update["action"] == "set", update
            self.state[update["key"]] = update["value"]

    # -- convenience flows ------------------------------------------------

    def approve(self, slug: str) -> None:
        """Step 8: the editor PASSed, so the entry reaches APPROVED."""
        self.result(
            "update_backlog",
            {"slug": slug, "old_status": "DRAFTED", "new_status": "APPROVED"},
            slug=slug,
            status="APPROVED",
        )

    def stage_social(self, slug: str, *variants: str) -> None:
        """Step 10: stage the short-form copy. Ungated; only observed."""
        for variant in variants:
            self.result(
                "save_artifact",
                {
                    "path": f"/repo/examples/content_factory/artifacts/social/{slug}-{variant}.md",
                    "bytes": 128,
                    "kind": "social",
                },
                kind="social",
                slug=slug,
                variant=variant,
            )

    def publish(self, slug: str) -> None:
        self.result("publish_content", {"slug": slug, "published": ["p"]}, slug=slug)

    def post(self, slug: str, channel: str) -> None:
        self.result(
            "post_social",
            {"slug": slug, "channel": channel, "simulated": True, "record": "r"},
            slug=slug,
            channel=channel,
        )

    def ship(self, slug: str, *channels: str) -> None:
        """A full article: approve, stage, publish, post every staged channel."""
        self.approve(slug)
        self.stage_social(slug, *channels)
        self.publish(slug)
        for channel in channels:
            self.post(slug, channel)

    def mark_published(self, slug: str) -> dict[str, object]:
        """Step 13: the claim R4 adjudicates."""
        return self.call("update_backlog", slug=slug, status="PUBLISHED")

    # -- views over state -------------------------------------------------

    def cycle_slugs(self) -> list[str]:
        return pg._cycle_shipped_slugs(self.state)

    def approved(self) -> list[str]:
        return pg._approved_slugs(self.state)

    def progress(self, slug: str) -> dict[str, object]:
        return pg._ship_progress(self.state).get(slug, {})


class clock_at:
    """Freeze the policy's clock, to exercise the UTC-day cycle boundary."""

    def __init__(self, moment: datetime) -> None:
        self.moment = moment

    def __enter__(self):
        self.real = pg.datetime
        moment = self.moment

        class Frozen:
            @staticmethod
            def now(tz=None):
                return moment

        pg.datetime = Frozen
        return self

    def __exit__(self, *_exc) -> None:
        pg.datetime = self.real


# ══ R3 — the ceiling counts ARTICLES, not guarded calls ════════════════════


def test_ceiling_counts_articles_not_guarded_calls():
    s = Session()
    s.ship("alpha", "x", "linkedin")  # 3 guarded calls
    assert s.cycle_slugs() == ["alpha"]
    s.ship("bravo", "x", "linkedin")  # 6 guarded calls
    assert s.cycle_slugs() == ["alpha", "bravo"]
    # Counting calls would already have hard-stopped at the ceiling of 3.
    assert s.call("publish_content", slug="charlie")["result"] == "ASK"


def test_finish_what_you_started_but_do_not_start_a_new_one():
    s = Session()
    for slug in ("alpha", "bravo"):
        s.ship(slug, "x", "linkedin")
    s.approve("charlie")
    s.stage_social("charlie", "x", "linkedin")
    s.publish("charlie")
    assert s.cycle_slugs() == ["alpha", "bravo", "charlie"]  # at the ceiling

    # The in-flight article finishes: its slug is already counted.
    for channel in ("x", "linkedin"):
        assert s.call("post_social", slug="charlie", channel=channel)["result"] == "ASK"
        s.post("charlie", channel)
    assert s.cycle_slugs() == ["alpha", "bravo", "charlie"]  # no inflation

    # A new article does not begin.
    s.approve("delta")
    denied = s.call("publish_content", slug="delta")
    assert denied["result"] == "DENY"
    assert "article ceiling reached" in denied["reason"]
    assert "may still be finished" in " ".join(denied["reason"].split())
    # Approved, so this is R3 talking, not R1.
    assert s.call("post_social", slug="delta", channel="x")["result"] == "DENY"


def test_cycle_set_is_keyed_on_the_utc_day():
    s = Session()
    for slug in ("a1", "a2", "a3"):
        s.ship(slug, "x")
    stored = json.loads(s.state[pg._CYCLE_SLUGS_KEY])
    assert stored["cycle"] == datetime.now(UTC).strftime("%Y-%m-%d")
    assert sorted(stored) == ["cycle", "slugs"]

    with clock_at(datetime.now(UTC) + timedelta(days=1)):
        assert s.cycle_slugs() == []  # yesterday's cycle is stale
        s.approve("a4")
        assert s.call("publish_content", slug="a4")["result"] == "ASK"
        s.publish("a4")
        assert s.cycle_slugs() == ["a4"]  # the new cycle starts clean


def test_failed_shipping_call_does_not_consume_the_ceiling():
    s = Session()
    s.approve("foxtrot")
    s.result("publish_content", {"error": "Draft artifact not found"}, slug="foxtrot")
    assert s.cycle_slugs() == []
    assert s.progress("foxtrot") == {}
    denied = s.mark_published("foxtrot")
    assert denied["result"] == "DENY"
    assert "no successful publish_content or post_social" in denied["reason"]


# ══ R1 / R2 — unchanged by R4 ══════════════════════════════════════════════


def test_r1_denies_social_before_the_blog_is_approved():
    s = Session()
    denied = s.call("post_social", slug="never-approved", channel="linkedin")
    assert denied["result"] == "DENY"
    assert "is not approved" in denied["reason"]


def test_r1_does_not_apply_to_publish_content():
    assert Session().call("publish_content", slug="never-approved")["result"] == "ASK"


def test_r2_asks_and_names_the_artifact():
    s = Session()
    s.approve("echo")
    social = s.call("post_social", slug="echo", channel="x")
    assert social["result"] == "ASK"
    assert "x short-form post" in social["reason"]
    blog = s.call("publish_content", slug="echo")
    assert blog["result"] == "ASK"
    assert "long-form blog draft" in blog["reason"]


def test_r1_still_precedes_r3():
    s = Session()
    for slug in ("a1", "a2", "a3"):
        s.ship(slug, "x")
    denied = s.call("post_social", slug="unapproved-at-ceiling", channel="x")
    # The sequencing violation is the more useful message.
    assert "is not approved" in denied["reason"]


def test_runner_local_path_defers_both_stateful_shipping_rules():
    local = Session(RUNNER_LOCAL)
    assert local.call("post_social", slug="never-approved", channel="x")["result"] == "ASK"
    at_ceiling = Session()
    for slug in ("a1", "a2", "a3"):
        at_ceiling.ship(slug, "x")
    local.state = at_ceiling.state
    assert local.call("publish_content", slug="brand-new")["result"] == "ASK"


# ══ the ungated tier ═══════════════════════════════════════════════════════


def test_read_backlog_and_save_artifact_are_never_gated():
    at_ceiling = Session()
    for slug in ("a1", "a2", "a3"):
        at_ceiling.ship(slug, "x")
    for context in (SERVER, RUNNER_LOCAL):
        for state in ({}, at_ceiling.state):
            s = Session(context)
            s.state = dict(state)
            for tool in ("read_backlog", "save_artifact"):
                assert s.call(tool, slug="whatever", status="PUBLISHED") == {"result": "ALLOW"}


def test_update_backlog_is_free_for_every_status_except_published():
    s = Session()
    for status in ("READY", "DRAFTED", "EDITED", "APPROVED"):
        assert s.call("update_backlog", slug="never-shipped", status=status) == {
            "result": "ALLOW"
        }, status
    # Only the terminal claim is checked.
    assert s.mark_published("never-shipped")["result"] == "DENY"


def test_non_terminal_backlog_statuses_are_free_on_the_runner_local_path():
    local = Session(RUNNER_LOCAL)
    for status in ("READY", "DRAFTED", "EDITED", "APPROVED"):
        assert local.call("update_backlog", slug="runner-local", status=status) == {
            "result": "ALLOW"
        }, status


# ══ R4 — PUBLISHED must match what shipped ═════════════════════════════════


def test_r4_denies_published_for_an_article_that_never_shipped():
    s = Session()
    s.approve("golf")
    denied = s.mark_published("golf")
    assert denied["result"] == "DENY"
    assert "no successful publish_content or post_social" in denied["reason"]


def test_r4_denies_published_when_only_the_blog_published():
    """The realistic failure: staged social copy that never went out."""
    s = Session()
    s.approve("hotel")
    s.stage_social("hotel", "x", "linkedin")
    s.publish("hotel")
    denied = s.mark_published("hotel")
    assert denied["result"] == "DENY"
    assert "half shipped" in denied["reason"]
    assert "x, linkedin" in denied["reason"]


def test_r4_denies_published_when_one_staged_channel_is_outstanding():
    s = Session()
    s.approve("india")
    s.stage_social("india", "x", "linkedin")
    s.publish("india")
    s.post("india", "x")
    denied = s.mark_published("india")
    assert denied["result"] == "DENY"
    assert "linkedin" in denied["reason"]
    assert "x," not in denied["reason"]  # the posted channel is not listed


def test_r4_denies_published_when_the_blog_never_published():
    s = Session()
    s.approve("juliet")
    s.stage_social("juliet", "x")
    s.post("juliet", "x")
    denied = s.mark_published("juliet")
    assert denied["result"] == "DENY"
    assert "publish_content has not succeeded" in denied["reason"]


def test_r4_allows_published_after_a_complete_ship_in_this_session():
    """The normal step-12 -> step-13 flow."""
    s = Session()
    s.ship("kilo", "x", "linkedin")
    assert s.progress("kilo") == {
        "staged": ["x", "linkedin"],
        "published": True,
        "posted": ["x", "linkedin"],
    }
    assert s.mark_published("kilo") == {"result": "ALLOW"}


def test_r4_measures_completeness_against_what_was_staged():
    """A cycle may legitimately produce only one social variant."""
    s = Session()
    s.ship("lima", "linkedin")
    assert s.mark_published("lima") == {"result": "ALLOW"}


def test_r4_treats_an_article_with_no_staged_social_as_complete_once_published():
    """A documented limit: R4 cannot demand a post nobody wrote."""
    s = Session()
    s.approve("mike")
    s.publish("mike")
    assert s.mark_published("mike") == {"result": "ALLOW"}


def test_r4_reads_the_staged_path_when_arguments_are_absent():
    """Slugs containing hyphens still resolve, because the suffix is matched."""
    s = Session()
    s.approve("multi-word-slug")
    s.result(
        "save_artifact",
        {"path": "artifacts/social/multi-word-slug-linkedin.md", "bytes": 10, "kind": "social"},
    )
    assert s.progress("multi-word-slug") == {"staged": ["linkedin"]}
    s.publish("multi-word-slug")
    assert s.mark_published("multi-word-slug")["result"] == "DENY"
    s.post("multi-word-slug", "linkedin")
    assert s.mark_published("multi-word-slug") == {"result": "ALLOW"}


def test_r4_defers_on_the_runner_local_path():
    """No persisted state there, so denying would fail EVERY local write."""
    local = Session(RUNNER_LOCAL)
    assert local.mark_published("never-shipped") == {"result": "ALLOW"}


def test_r4_survives_the_midnight_straddle():
    """A publish at 23:59 and its status write at 00:01 must still be ALLOWED.

    This is why R4 reads the session-scoped progress record and not the
    cycle-scoped ceiling set, which resets at the UTC day boundary.
    """
    s = Session()
    s.ship("november", "x", "linkedin")
    assert s.mark_published("november") == {"result": "ALLOW"}

    with clock_at(datetime.now(UTC) + timedelta(days=1)):
        assert s.cycle_slugs() == []  # the ceiling reset, as designed
        assert s.progress("november")["published"] is True  # progress did not
        assert s.mark_published("november") == {"result": "ALLOW"}


def test_the_two_state_scopes_stay_separate():
    s = Session()
    s.ship("oscar", "x")
    assert s.cycle_slugs() == ["oscar"]
    with clock_at(datetime.now(UTC) + timedelta(days=2)):
        s.ship("papa", "x")
        assert s.cycle_slugs() == ["papa"]  # cycle-scoped: only today's
    progress = pg._ship_progress(s.state)
    assert sorted(progress) == ["oscar", "papa"]  # session-scoped: both


# ══ R4 must not disturb the other rules ═══════════════════════════════════


def test_an_approved_write_still_registers_with_r4_present():
    s = Session()
    assert s.call("update_backlog", slug="quebec", status="APPROVED") == {"result": "ALLOW"}
    s.approve("quebec")
    assert s.approved() == ["quebec"]
    assert s.call("post_social", slug="quebec", channel="x")["result"] == "ASK"


def test_a_published_write_neither_removes_nor_forges_an_approval():
    s = Session()
    s.ship("romeo", "x")
    assert s.approved() == ["romeo"]
    recorded = s.result(
        "update_backlog",
        {"slug": "romeo", "old_status": "APPROVED", "new_status": "PUBLISHED"},
        slug="romeo",
        status="PUBLISHED",
    )
    assert recorded == {"result": "ALLOW"}  # no state_updates
    assert s.approved() == ["romeo"]  # R1's record survives
    assert s.cycle_slugs() == ["romeo"]  # no ceiling slot consumed
    assert s.call("post_social", slug="romeo", channel="linkedin")["result"] == "ASK"

    # ...and PUBLISHED alone never forges an approval.
    fresh = Session()
    fresh.result(
        "update_backlog",
        {"slug": "sierra", "old_status": "READY", "new_status": "PUBLISHED"},
        slug="sierra",
        status="PUBLISHED",
    )
    assert fresh.approved() == []
    assert fresh.call("post_social", slug="sierra", channel="x")["result"] == "DENY"


# ══ the config still binds after the rename ═══════════════════════════════


def test_config_yaml_binds_the_renamed_argument():
    try:
        import yaml
    except ImportError:  # pragma: no cover - bare checkout
        print("    (skipped: PyYAML not installed)")
        return
    import inspect

    config = yaml.safe_load((EXAMPLE_ROOT / "config.yaml").read_text(encoding="utf-8"))
    policy = config["guardrails"]["policies"]["publish_gate"]["function"]
    assert policy["path"].endswith("publish_gate.publish_gate")
    arguments = policy["arguments"]
    assert arguments == {"max_articles_per_cycle": 3}
    # The arguments are bound to the factory signature, so a stale name here
    # would be a TypeError at agent load time.
    inspect.signature(pg.publish_gate).bind(**arguments)
    assert pg.publish_gate(**arguments) is not None


# ── plain-python runner ────────────────────────────────────────────────────


def main() -> int:
    tests = [(n, o) for n, o in sorted(globals().items()) if n.startswith("test_") and callable(o)]
    failures: list[str] = []
    print(f"publish_gate: {len(tests)} cases\n")
    for name, test in tests:
        try:
            test()
        except Exception as error:  # noqa: BLE001 - a test runner reports everything
            failures.append(f"{name}: {type(error).__name__}: {error}")
            print(f"  FAIL  {name}")
        else:
            print(f"  ok    {name}")
    print()
    if failures:
        print(f"{len(failures)} FAILED:")
        for failure in failures:
            print("  -", failure)
        return 1
    print(f"all {len(tests)} publish_gate cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
