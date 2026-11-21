"""Executable spec for the supervisor's inability to edit its own bundle.

A real smoke run of this example hit a machine-level sandbox failure launching
the Codex sub-agent and responded by rewriting
``agents/blog_writer/config.yaml`` to ``harness: codex-native`` with
``yolo: true`` -- turning a sandbox off, unprompted, in an example whose whole
subject is that irreversible actions need a human. It could do that because the
supervisor declared ``os_env: {type: caller_process, sandbox: {type: none}}``,
which is what makes the loader hand it ``sys_os_write`` / ``sys_os_edit`` /
``sys_os_shell``.

The fix is the absence of a capability, and absences are easy to re-add by
accident -- ``os_env`` is the boilerplate CLAUDE.md documents. So the invariant
is pinned here:

1. The supervisor, ``editor`` and ``social_writer`` declare no ``os_env``, so
   none of them is given a file-write tool at all.
2. The supervisor still carries the ``no_self_modification`` backstop, wired to
   the registry builtin, so re-adding ``os_env`` does not silently restore the
   capability.
3. That backstop, built from the arguments the config actually passes, DENIES
   writes to every part of the bundle and abstains on the five staging tools.
4. ``blog_writer`` keeps its ``os_env`` -- a known, documented bypass. Asserted
   so the bypass cannot close by accident and leave the docs lying.

Run it either way::

    python examples/content_factory/tests/test_self_edit_guard.py
    pytest examples/content_factory/tests/

Stdlib only for the config invariants, which is the part that must hold on a
bare checkout. The cases that execute the real ``read_only_os`` builtin are
skipped when Omnigent is not installed -- they verify framework code, not this
bundle, and cannot be stubbed without testing the stub.

This directory is NOT ``tools/python/``, so nothing here is auto-discovered as
an agent tool -- keep it that way.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

EXAMPLE_ROOT = Path(__file__).resolve().parent.parent

SUPERVISOR = EXAMPLE_ROOT / "config.yaml"
AGENTS = EXAMPLE_ROOT / "agents"

# The handler the backstop must point at. A registry builtin on purpose: a
# custom handler would make the supervisor unloadable against a remote server
# (see CLAUDE.md "Custom policies do not run against a remote server").
BACKSTOP_HANDLER = "omnigent.policies.builtins.orchestration.read_only_os"

# Agents that must hold no OS environment. Their prompts all say they do not
# write files; with no `os_env` they also cannot.
NO_OS_ENV = ("<supervisor>", "editor", "social_writer")

# Bundle paths a write must never reach. The first is the file the real run
# actually rewrote.
PROTECTED = (
    "examples/content_factory/agents/blog_writer/config.yaml",
    "examples/content_factory/config.yaml",
    "examples/content_factory/policies/publish_gate.py",
    "examples/content_factory/tools/python/save_artifact.py",
    "examples/content_factory/tools/python/read_backlog.py",
    "examples/content_factory/agents/editor/config.yaml",
    "examples/content_factory/skills/blog-style/SKILL.md",
)

# Every argument key a write tool names its target with, across the harnesses
# `read_only_os` covers.
WRITE_CALLS = (
    ("sys_os_write", "path"),
    ("sys_os_edit", "path"),
    ("Write", "file_path"),
    ("Edit", "file_path"),
    ("MultiEdit", "file_path"),
    ("NotebookEdit", "notebook_path"),
    ("write", "path"),
    ("edit", "path"),
)

# The supervisor's own tools. None of them is a file-write tool, so the
# backstop must abstain on all of them -- that is what keeps staging free.
STAGING_CALLS = (
    ("read_backlog", {}),
    ("read_backlog", {"include_artifacts": True}),
    ("update_backlog", {"slug": "demo", "status": "DRAFTED"}),
    ("update_backlog", {"slug": "demo", "status": "PUBLISHED"}),
    ("save_artifact", {"kind": "outline", "slug": "demo", "content": "x"}),
    ("save_artifact", {"kind": "draft", "slug": "demo", "content": "x"}),
    ("save_artifact", {"kind": "social", "slug": "demo", "variant": "x", "content": "x"}),
    ("save_artifact", {"kind": "social", "slug": "demo", "variant": "linkedin", "content": "x"}),
    ("save_artifact", {"kind": "cycle", "slug": "demo", "content": "x"}),
    ("save_artifact", {"kind": "dashboard", "slug": "dashboard", "content": "x"}),
    ("publish_content", {"slug": "demo"}),
    ("post_social", {"slug": "demo", "channel": "x"}),
    ("post_social", {"slug": "demo", "channel": "linkedin"}),
)


class Skipped(Exception):
    """Raised by a case that needs Omnigent installed."""


def _skip(reason: str):
    """Skip the calling case, under pytest or the plain-python runner alike."""
    try:
        import pytest
    except ImportError:
        raise Skipped(reason) from None
    pytest.skip(reason)


def _skip_exceptions() -> tuple[type[BaseException], ...]:
    """Exception types `_skip` can raise, for the plain-python runner to catch."""
    try:
        import pytest
    except ImportError:
        return (Skipped,)
    return (Skipped, pytest.skip.Exception)


def _config(agent: str) -> Path:
    """Path to one agent's ``config.yaml``; ``"<supervisor>"`` is the root one."""
    return SUPERVISOR if agent == "<supervisor>" else AGENTS / agent / "config.yaml"


def _declares_os_env(path: Path) -> bool:
    """Whether a config declares a top-level ``os_env`` block.

    Anchored at column 0 and in multiline mode: ``os_env`` is a top-level key,
    and the word also appears in prose comments, which must not count.
    """
    return re.search(r"(?m)^os_env:", _settings(path)) is not None


def _settings(path: Path) -> str:
    """A config's actual settings, with comment lines dropped.

    The configs explain the self-edit incident in prose, quoting the very
    strings these cases search for (`yolo`, `codex-native`), so a raw text
    search would match the explanation instead of a setting.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(line for line in lines if not line.lstrip().startswith("#"))


def _call(name: str, **arguments: object) -> dict:
    """A V0 ``tool_call`` policy event."""
    return {"type": "tool_call", "data": {"name": name, "arguments": arguments}}


def _backstop():
    """The backstop policy, built from the arguments the config really passes.

    Reads the handler and its ``deny_reason`` out of the YAML rather than
    hardcoding them, so the test exercises the configuration under review and
    not a hand-made copy of it.

    Skips the calling case when Omnigent is not installed.
    """
    try:
        from omnigent.policies.builtins.orchestration import read_only_os
    except ImportError:  # pragma: no cover - environment, not bundle
        _skip("Omnigent is not installed")

    text = SUPERVISOR.read_text(encoding="utf-8")
    block = text[text.index("    no_self_modification:") :]
    assert BACKSTOP_HANDLER in block, "backstop is not wired to the registry builtin"
    reason = re.search(r"(?s)deny_reason: \|\n(.*?)(?=\n    \w|\n\n    #)", block)
    assert reason, "backstop declares no deny_reason"
    return read_only_os(deny_reason=reason.group(1).strip())


# ── the capability is absent ────────────────────────────────────────────────


def test_the_supervisor_declares_no_os_env() -> None:
    """The root cause: `os_env` is what granted `sys_os_edit`."""
    assert not _declares_os_env(SUPERVISOR), (
        "The supervisor must declare no os_env. With one it is handed "
        "sys_os_write / sys_os_edit / sys_os_shell and can rewrite its own "
        "bundle -- which is exactly what a real run did."
    )


def test_the_claude_sub_agents_declare_no_os_env() -> None:
    """Delegation must not route around the supervisor's own lack of access."""
    for agent in ("editor", "social_writer"):
        assert not _declares_os_env(_config(agent)), (
            f"{agent} must declare no os_env: a supervisor that cannot write "
            f"files but can ask a sub-agent to is not confined."
        )


def test_no_agent_in_the_bundle_enables_yolo() -> None:
    """The exact escape the observed run reached for."""
    for config in [SUPERVISOR, *sorted(AGENTS.glob("*/config.yaml"))]:
        text = _settings(config)
        assert not re.search(r"(?m)^\s*yolo:", text), f"{config} sets yolo"
        assert "codex-native" not in text, f"{config} switches to codex-native"


def test_the_sandbox_type_is_never_widened_where_os_env_remains() -> None:
    """A remaining `os_env` may not grant more than the default."""
    for config in [SUPERVISOR, *sorted(AGENTS.glob("*/config.yaml"))]:
        text = _settings(config)
        assert "allow_network: true" not in text, f"{config} widens egress"
        assert "write_paths" not in text, f"{config} grants host write paths"


# ── the backstop is wired ───────────────────────────────────────────────────


def test_the_supervisor_carries_the_self_modification_backstop() -> None:
    """Re-adding `os_env` must not silently restore the capability."""
    text = SUPERVISOR.read_text(encoding="utf-8")
    assert "    no_self_modification:" in text, "backstop policy is missing"
    assert BACKSTOP_HANDLER in text, "backstop is not the registry builtin"


def test_the_backstop_sits_after_publish_gate_in_the_config() -> None:
    """`read_backlog` scans config.yaml by line sequence for the ceiling.

    It walks `guardrails:` -> `  policies:` -> `    publish_gate:` ->
    `      function:` -> `        arguments:` in order, so a policy inserted
    between those lines would silently break the dashboard's
    `article_ceiling`.
    """
    text = SUPERVISOR.read_text(encoding="utf-8")
    assert text.index("    publish_gate:") < text.index("    no_self_modification:")


def test_the_four_policies_are_all_still_declared() -> None:
    """The backstop is an addition, not a replacement."""
    text = SUPERVISOR.read_text(encoding="utf-8")
    for name in ("publish_gate", "guarded_tools", "no_self_modification",
                 "user_daily_cost_budget"):
        assert f"    {name}:" in text, f"policy {name} is missing"


# ── the backstop behaves ────────────────────────────────────────────────────


def test_the_backstop_denies_a_write_to_every_part_of_the_bundle() -> None:
    """Config, sub-agent configs, policies, tools and skills are all refused."""
    evaluate = _backstop()
    for target in PROTECTED:
        for tool, key in WRITE_CALLS:
            decision = evaluate(_call(tool, **{key: target}), {})
            assert decision["result"] == "DENY", f"{tool} -> {target} was {decision}"


def test_the_backstop_denies_the_self_edit_the_real_run_performed() -> None:
    """The exact call, with the exact payload, from the observed failure."""
    evaluate = _backstop()
    decision = evaluate(
        _call(
            "sys_os_edit",
            path="examples/content_factory/agents/blog_writer/config.yaml",
            old_str="    harness: codex",
            new_str="    harness: codex-native\n    yolo: true",
        ),
        {},
    )
    assert decision["result"] == "DENY"
    assert "may not write files" in decision["reason"]


def test_the_backstop_denies_a_write_dressed_up_as_an_artifact_path() -> None:
    """It is the tool that is refused, not a path pattern.

    A write that claims to target `artifacts/` is still denied, because the
    supervisor stages through `save_artifact`, never through a file-write tool.
    """
    evaluate = _backstop()
    decision = evaluate(
        _call("sys_os_write", path="examples/content_factory/artifacts/drafts/demo.md"),
        {},
    )
    assert decision["result"] == "DENY"


def test_the_backstop_abstains_on_all_five_staging_tools() -> None:
    """Drafting, staging and shipping stay exactly as free as before."""
    evaluate = _backstop()
    for name, arguments in STAGING_CALLS:
        decision = evaluate(_call(name, **arguments), {})
        assert decision["result"] == "ALLOW", f"{name}({arguments}) was {decision}"


def test_the_backstop_abstains_on_sub_agent_dispatch_and_reads() -> None:
    """It gates writes only -- coordination and reading are untouched."""
    evaluate = _backstop()
    for name in ("blog_writer", "editor", "social_writer", "ui_open_file",
                 "sys_scheduled_task_create", "Read", "Glob", "Grep"):
        assert evaluate(_call(name, prompt="x"), {})["result"] == "ALLOW"


def test_the_backstop_does_not_gate_shell_a_documented_gap() -> None:
    """Pins the hole the README admits, so the docs cannot drift.

    `read_only_os` covers write/edit tools, not `sys_os_shell`. That is moot
    while no agent here declares `os_env` -- there is no shell tool either --
    but it is why the policy is a backstop and not the mechanism.
    """
    evaluate = _backstop()
    decision = evaluate(
        _call("sys_os_shell", command="echo 'yolo: true' >> agents/blog_writer/config.yaml"),
        {},
    )
    assert decision["result"] == "ALLOW", (
        "read_only_os now gates shell -- good, but the README says it does "
        "not. Update the docs."
    )


# ── the documented bypass stays documented ──────────────────────────────────


def test_blog_writer_still_holds_the_documented_bypass() -> None:
    """The Codex writer keeps `os_env`; the docs say so, so assert it.

    Left in place deliberately: the Codex harness launch is sensitive to the
    sandbox configuration that failed in the observed run, and that is machine
    configuration, out of scope here. If this case fails because the bypass
    closed, that is good news -- remove the bypass section from README.md and
    README_YAML_CONFIG.md in the same change.
    """
    assert _declares_os_env(_config("blog_writer")), (
        "blog_writer no longer declares os_env. The remaining-bypass note in "
        "README.md and README_YAML_CONFIG.md is now wrong -- update it."
    )


# ── plain-python runner ────────────────────────────────────────────────────


def main() -> int:
    tests = [(n, o) for n, o in sorted(globals().items()) if n.startswith("test_") and callable(o)]
    failures: list[str] = []
    skipped = 0
    print(f"self_edit_guard: {len(tests)} cases\n")
    for name, test in tests:
        try:
            test()
        except _skip_exceptions() as reason:
            skipped += 1
            print(f"  skip  {name}  ({reason})")
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
    tail = f" ({skipped} skipped: Omnigent not installed)" if skipped else ""
    print(f"all {len(tests) - skipped} self_edit_guard cases passed{tail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
