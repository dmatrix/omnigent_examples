"""Executable spec for the supervisor's inability to edit its own bundle.

A real smoke run of this example hit a machine-level sandbox failure launching
the Codex sub-agent and responded by rewriting
``agents/blog_writer/config.yaml`` to ``harness: codex-native`` with
``yolo: true`` -- turning a sandbox off, unprompted, in an example whose whole
subject is that irreversible actions need a human. It could do that because the
supervisor declared ``os_env: {type: caller_process, sandbox: {type: none}}``,
which is what makes the loader hand an agent ``sys_os_write`` /
``sys_os_edit`` / ``sys_os_shell``.

The fix is the absence of a capability, and absences are easy to re-add by
accident -- ``os_env`` is the boilerplate CLAUDE.md documents. So the invariant
is pinned here, at three strengths:

1. **YAML shape** -- no agent declares ``os_env``. A fast first signal, and all
   it is: a framework registration change would sail straight past it.
2. **Resolved behaviour** -- a real :class:`ToolManager` is built against each
   of the four configs and asked for its tool names. This is the assertion that
   matters; the YAML one is a convenience.
3. **Documentation** -- the residual Codex bypass (below) is real, so the cases
   that pin it OPEN the README files and fail if the disclosure is deleted.

The residual bypass, stated here because the tests below encode it:
``agents/blog_writer`` runs ``harness: codex``, and Codex's own ``apply_patch``
is not an Omnigent tool. Removing ``os_env`` narrows its sandbox from
``danger-full-access`` to ``workspace-write``, but the bundle is in the
workspace, so Codex can still edit it. ``disable_native_tools: true`` removes
the shell half; no feature flag removes ``apply_patch``. No policy can gate it
either -- native Codex calls arrive already executed. That is a harness-level
limit, not something this bundle can configure away.

Run it either way::

    python examples/content_factory/tests/test_self_edit_guard.py
    pytest examples/content_factory/tests/

Stdlib only for the YAML-shape and documentation cases, which is the part that
must hold on a bare checkout. The resolved-toolset cases need Omnigent and skip
without it -- they assert framework behaviour, and stubbing the framework would
only test the stub.

This directory is NOT ``tools/python/``, so nothing here is auto-discovered as
an agent tool -- keep it that way.
"""

from __future__ import annotations

import re
from pathlib import Path

EXAMPLE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = EXAMPLE_ROOT.parent.parent

SUPERVISOR = EXAMPLE_ROOT / "config.yaml"
AGENTS = EXAMPLE_ROOT / "agents"
README = EXAMPLE_ROOT / "README.md"
README_YAML = EXAMPLE_ROOT / "README_YAML_CONFIG.md"
DEMO = EXAMPLE_ROOT / "demo.md"
PUBLISH_GATE = EXAMPLE_ROOT / "policies" / "publish_gate.py"

# Every file in the bundle that carries prose about the guard. The honesty
# cases sweep all of them, not just the two READMEs: the files that went stale
# last round were the two that nobody was looking at.
PROSE_FILES = (
    SUPERVISOR,
    AGENTS / "blog_writer" / "config.yaml",
    AGENTS / "editor" / "config.yaml",
    AGENTS / "social_writer" / "config.yaml",
    README,
    README_YAML,
    DEMO,
    PUBLISH_GATE,
    EXAMPLE_ROOT / "tests" / "README.md",
)

# Every agent in the bundle. "<supervisor>" is the root config.yaml.
ALL_AGENTS = ("<supervisor>", "blog_writer", "editor", "social_writer")

# The OS tools an `os_env` block would grant. None may appear in any resolved
# toolset.
SYS_OS_TOOLS = frozenset({"sys_os_read", "sys_os_write", "sys_os_edit", "sys_os_shell"})

# The five staging tools. The supervisor must keep all of them: the guard is
# supposed to cost the example nothing.
FACTORY_TOOLS = frozenset(
    {"read_backlog", "update_backlog", "save_artifact", "publish_content", "post_social"}
)

# The backstop handler. A registry builtin on purpose -- a custom handler would
# make the supervisor unloadable against a remote server, which this bundle
# already struggles with (see CLAUDE.md "Custom policies do not run against a
# remote server"); no reason to deepen that.
BACKSTOP_HANDLER = "omnigent.policies.builtins.cel.cel_policy"

# Tool names the backstop must DENY. The shell entries are the point: the
# `read_only_os` builtin this replaced allows them, and a shell redirect
# rewrites YAML just as well as an edit does.
BACKSTOP_DENIES = (
    "sys_os_write", "sys_os_edit", "sys_os_shell",
    "Write", "Edit", "MultiEdit", "NotebookEdit", "Bash",
    "write", "edit", "bash", "shell", "apply_patch",
)

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

# Every argument key a write tool names its target with.
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

# The supervisor's own calls. None is a file tool, so the backstop must abstain
# on all of them -- that is what keeps staging free.
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
    ("blog_writer", {"prompt": "draft"}),
    ("editor", {"prompt": "review"}),
    ("social_writer", {"prompt": "derive"}),
    ("sys_os_read", {"path": "backlog.md"}),
    ("web_search", {"query": "omnigent"}),
    ("ui_open_file", {"path": "artifacts/dashboard.md"}),
    ("sys_scheduled_task_create", {"agent_id": "x"}),
    ("sys_scheduled_task_list", {}),
)

# Documentation that must survive, phrase by phrase, because the thing it
# describes is still true. A previous round of this PR claimed a test pinned
# the docs when none opened a file; both READMEs were then falsified without a
# single failure. These cases open the files.
REQUIRED_DISCLOSURES = {
    README: (
        "What this does not close",
        "apply_patch",
        "workspace-write",
        "internally_executed",
        "disable_native_tools",
    ),
    README_YAML: (
        "apply_patch",
        "workspace-write",
    ),
    # demo.md and publish_gate.py both carried the pre-change claim that the
    # supervisor holds `os_env`, and neither was in the first fix's diff --
    # which is exactly how a half-applied honesty fix hides. They are pinned
    # here so the next one cannot.
    DEMO: ("apply_patch",),
    PUBLISH_GATE: ("apply_patch",),
}

# The schedule proposal has not yet been demonstrated as an actual tool call.
# These prose files must keep saying so until a durable transcript proves it.
SCHEDULE_CAVEAT_FILES = (README, DEMO)
SCHEDULE_CAVEAT_REQUIRED = "not yet reliably reproduced"
SCHEDULE_CAVEAT_OVERCLAIMS = (
    "schedule proposal is verified",
    "schedule proposal has been verified",
    "schedule proposal is reliable",
    "schedule proposal works reliably",
    "the schedule now reliably works",
)

# Wording that is false about this bundle. Each of these was actually written
# down at some point in this change's history, which is why they are named
# individually rather than gestured at.
FORBIDDEN_CLAIMS = (
    # Round-2 overclaim: true of sys_os_*, false of blog_writer's apply_patch,
    # which IS in the backstop's tool list.
    "no agent holds such a tool",
    "none holds such a tool",
    "no agent holds the tools",
    "none holds the tools",
    "so none holds",
    "there is no such tool to gate",
    # Claims the residual bypass does not exist.
    "no bypass remains",
    "no bypass exists",
    "the bypass is closed",
    "all four agents are fully",
    "structurally impossible for every agent",
)

# Claims that the supervisor still has the capability this change removed.
# Matched as a regex because the prose varies; negated forms are excluded so
# the historical explanations ("it used to declare os_env") stay legal.
STALE_OS_ENV_CLAIM = re.compile(
    r"(?:supervisor|agent)[^.\n]{0,90}(?:declares|has)\s+[`\s]*os_env",
    re.IGNORECASE,
)
STALE_EXEMPT = re.compile(
    r"no agent|none declares|none of them|used to|no longer|cannot|does not|"
    r"not declare|never declared",
    re.IGNORECASE,
)

# Clause boundaries, applied before the exemption. Exempting a whole LINE on
# one negating phrase left a one-clause bypass:
#
#     "No agent declares `os_env`, but the supervisor has `os_env`."
#
# -- where the leading negation excused the false second half. Splitting first
# means a negation can only excuse the clause it actually appears in. Sentence
# punctuation plus the coordinating conjunctions that join two independent
# claims; `and`/`or` are included because "X and Y" carries two assertions.
CLAUSE_BOUNDARY = re.compile(
    r"[.;,:]|\s(?:but|and|or|while|whereas|though|although|yet|however|"
    r"nevertheless|whilst)\s",
    re.IGNORECASE,
)


def _clauses(line: str) -> list[str]:
    """Split *line* into clauses for independent exemption checks.

    :param line: One line of prose.
    :returns: Non-empty clause strings.
    """
    return [part for part in CLAUSE_BOUNDARY.split(line) if part and part.strip()]


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


def _settings(path: Path) -> str:
    """A config's actual settings, with comment lines dropped.

    The configs explain the self-edit incident in prose, quoting the very
    strings these cases search for (`yolo`, `codex-native`, `os_env`), so a raw
    text search would match the explanation instead of a setting.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(line for line in lines if not line.lstrip().startswith("#"))


def _declares_os_env(path: Path) -> bool:
    """Whether a config declares a top-level ``os_env`` block."""
    return re.search(r"(?m)^os_env:", _settings(path)) is not None


def _resolved_tool_names(agent: str) -> list[str]:
    """Build a real ToolManager for *agent* and return its resolved tool names.

    This is the behavioural assertion the YAML-shape cases only approximate: it
    goes through the same parser and the same registration path a live run uses,
    so a framework change that started granting OS tools without an ``os_env``
    block would fail here.

    Skips the calling case when Omnigent is not installed.
    """
    try:
        from omnigent.spec.parser import parse
        from omnigent.tools.manager import ToolManager
    except ImportError:  # pragma: no cover - environment, not bundle
        _skip("Omnigent is not installed")

    root = _config(agent).parent
    # ``os_env_schema_only`` registers the OS tool *schemas* without building a
    # real OS environment -- and, crucially, preserves the ``os_env`` gate
    # (manager.py: "Preserves the ``os_env`` gate"). So if the gate ever
    # regressed, these names would appear here. It is the strictest cheap check:
    # a pass means the tools are absent even in the mode that would surface them.
    manager = ToolManager(parse(root), workdir=root, os_env_schema_only=True)
    return sorted(manager.get_tool_names())


def _backstop():
    """The backstop policy, built from the arguments the config really passes.

    Reads the handler and arguments out of the parsed spec rather than
    hardcoding them, so the test exercises the configuration under review and
    not a hand-made copy of it.

    Skips the calling case when Omnigent is not installed.
    """
    try:
        from omnigent.policies.builtins.cel import cel_policy
        from omnigent.spec.parser import parse
    except ImportError:  # pragma: no cover - environment, not bundle
        _skip("Omnigent is not installed")

    spec = parse(EXAMPLE_ROOT)
    policy = next(p for p in spec.guardrails.policies if p.name == "no_self_modification")
    assert policy.function.path == BACKSTOP_HANDLER, policy.function.path
    return cel_policy(**(policy.function.arguments or {}))


def _call(name: str, **arguments: object) -> dict:
    """A V0 ``tool_call`` policy event."""
    return {"type": "tool_call", "data": {"name": name, "arguments": arguments}}


# ── 1. the capability is absent (YAML shape -- fast first signal) ───────────


def test_no_agent_in_the_bundle_declares_os_env() -> None:
    """The root cause, across every agent: `os_env` is what granted the tools."""
    offenders = [agent for agent in ALL_AGENTS if _declares_os_env(_config(agent))]
    assert not offenders, (
        f"These agents declare os_env: {offenders}. An agent with one is handed "
        f"sys_os_write / sys_os_edit / sys_os_shell and can rewrite the bundle "
        f"-- which is exactly what a real run did."
    )


def test_no_agent_in_the_bundle_enables_yolo() -> None:
    """The exact escape the observed run reached for."""
    for agent in ALL_AGENTS:
        text = _settings(_config(agent))
        assert not re.search(r"(?m)^\s*yolo:", text), f"{agent} sets yolo"
        assert "codex-native" not in text, f"{agent} switches to codex-native"


def test_no_agent_widens_a_sandbox_or_grants_write_paths() -> None:
    """No config may grant more filesystem or network reach than the default."""
    for agent in ALL_AGENTS:
        text = _settings(_config(agent))
        assert "allow_network: true" not in text, f"{agent} widens egress"
        assert "write_paths" not in text, f"{agent} grants host write paths"


def test_blog_writer_disables_codex_native_tools() -> None:
    """The partial narrowing of the residual bypass must stay in place.

    Removes Codex's shell tool. It does not remove `apply_patch`, which is why
    the disclosure cases below exist.
    """
    text = _settings(_config("blog_writer"))
    assert re.search(r"(?m)^\s*disable_native_tools:\s*true\s*$", text), (
        "blog_writer no longer sets disable_native_tools: true, so Codex's "
        "native shell is back alongside apply_patch."
    )


# ── 2. the capability is absent (resolved behaviour -- the real assertion) ──


def test_no_agent_resolves_any_sys_os_tool() -> None:
    """The behavioural invariant: a real ToolManager grants no OS tool.

    The YAML cases above check the input; this checks the output, through the
    same parser and registration path a live run uses.
    """
    granted = {
        agent: sorted(set(_resolved_tool_names(agent)) & SYS_OS_TOOLS)
        for agent in ALL_AGENTS
    }
    offenders = {agent: tools for agent, tools in granted.items() if tools}
    assert not offenders, f"OS tools resolved for: {offenders}"


def test_the_supervisor_still_resolves_all_five_staging_tools() -> None:
    """The guard must cost the example nothing."""
    resolved = set(_resolved_tool_names("<supervisor>"))
    missing = sorted(FACTORY_TOOLS - resolved)
    assert not missing, f"staging tools lost: {missing}"


def test_tool_discovery_still_excludes_the_tests_directory() -> None:
    """`tests/` is a sibling of `tools/`, and nothing in it is a tool."""
    for agent in ALL_AGENTS:
        leaked = [name for name in _resolved_tool_names(agent) if "test" in name.lower()]
        assert not leaked, f"{agent} resolved test-named tools: {leaked}"


# ── 3. the backstop is wired, and behaves ──────────────────────────────────


def test_the_supervisor_carries_the_self_modification_backstop() -> None:
    """Re-adding `os_env` must not silently restore the capability."""
    text = SUPERVISOR.read_text(encoding="utf-8")
    assert "    no_self_modification:" in text, "backstop policy is missing"
    assert BACKSTOP_HANDLER in text, "backstop is not the expected registry builtin"


def test_the_backstop_covers_shell_as_well_as_write() -> None:
    """The gap the cross-review flagged in the previous `read_only_os` wiring."""
    arguments = _backstop_arguments()
    expression = str(arguments.get("expression", ""))
    missing = [name for name in BACKSTOP_DENIES if f'"{name}"' not in expression]
    assert not missing, f"backstop does not name these tools: {missing}"


def _backstop_arguments() -> dict:
    """The backstop's parsed `arguments` mapping.

    Skips the calling case when Omnigent is not installed.
    """
    try:
        from omnigent.spec.parser import parse
    except ImportError:  # pragma: no cover - environment, not bundle
        _skip("Omnigent is not installed")
    spec = parse(EXAMPLE_ROOT)
    policy = next(p for p in spec.guardrails.policies if p.name == "no_self_modification")
    return dict(policy.function.arguments or {})


def test_the_backstop_sits_after_publish_gate_in_the_config() -> None:
    """`read_backlog` descends a key path; keep publish_gate's block intact.

    `_article_ceiling` no longer depends on policy ORDER -- it walks the key
    path by indentation -- but the two still have to agree, and the shipped
    config is the only place that is observable. Asserted via the parser in
    `test_read_dashboard.py`; this case just keeps the declaration order tidy
    and documents why anyone cared.
    """
    text = SUPERVISOR.read_text(encoding="utf-8")
    assert text.index("    publish_gate:") < text.index("    no_self_modification:")


def test_the_four_policies_are_all_still_declared() -> None:
    """The backstop is an addition, not a replacement."""
    text = SUPERVISOR.read_text(encoding="utf-8")
    for name in ("publish_gate", "guarded_tools", "no_self_modification",
                 "user_daily_cost_budget"):
        assert f"    {name}:" in text, f"policy {name} is missing"


def test_the_backstop_denies_a_write_to_every_part_of_the_bundle() -> None:
    """Config, sub-agent configs, policies, tools and skills are all refused."""
    evaluate = _backstop()
    for target in PROTECTED:
        for tool, key in WRITE_CALLS:
            decision = evaluate(_call(tool, **{key: target})) or {}
            assert decision.get("result") == "DENY", f"{tool} -> {target} was {decision}"


def test_the_backstop_denies_every_shell_tool() -> None:
    """A shell redirect rewrites YAML as well as an edit does."""
    evaluate = _backstop()
    redirect = "echo 'yolo: true' >> agents/blog_writer/config.yaml"
    for tool in ("sys_os_shell", "Bash", "bash", "shell"):
        decision = evaluate(_call(tool, command=redirect)) or {}
        assert decision.get("result") == "DENY", f"{tool} was {decision}"


def test_the_backstop_denies_the_self_edit_the_real_run_performed() -> None:
    """The exact call, with the exact payload, from the observed failure."""
    evaluate = _backstop()
    decision = evaluate(
        _call(
            "sys_os_edit",
            path="examples/content_factory/agents/blog_writer/config.yaml",
            old_str="    harness: codex",
            new_str="    harness: codex-native\n    yolo: true",
        )
    ) or {}
    assert decision.get("result") == "DENY"
    assert "may not write files" in decision.get("reason", "")


def test_the_backstop_abstains_on_staging_dispatch_and_reads() -> None:
    """Drafting, staging, shipping and delegation stay exactly as free as before."""
    evaluate = _backstop()
    for name, arguments in STAGING_CALLS:
        decision = evaluate(_call(name, **arguments)) or {}
        result = decision.get("result", "ABSTAIN")
        assert result in ("ALLOW", "ABSTAIN"), f"{name}({arguments}) was {decision}"


def test_the_backstop_abstains_on_non_tool_call_events() -> None:
    """It must compose with the other three policies, not short-circuit them."""
    evaluate = _backstop()
    for event_type in ("llm_request", "tool_result", "turn_start"):
        decision = evaluate({"type": event_type, "data": {}})
        assert decision is None or decision.get("result") != "DENY"


# ── 4. the residual bypass is disclosed (these cases OPEN the files) ───────


def test_both_readmes_disclose_the_residual_codex_bypass() -> None:
    """The bypass is real, so the disclosure describing it must survive.

    Deliberately reads the documentation. The previous round of this change
    reported that a test pinned the docs; none opened a file, and both READMEs
    were subsequently falsified to claim no bypass existed without a single
    test failing. A docs-pinning test opens the file or it does not exist.
    """
    for path, phrases in REQUIRED_DISCLOSURES.items():
        text = path.read_text(encoding="utf-8")
        missing = [phrase for phrase in phrases if phrase not in text]
        assert not missing, (
            f"{path.name} no longer discloses the residual bypass "
            f"(missing: {missing}). blog_writer runs harness: codex, and "
            f"Codex's apply_patch can still write the bundle. Either the "
            f"bypass was genuinely closed -- in which case update this test -- "
            f"or the documentation is now false."
        )


def test_no_file_in_the_bundle_claims_full_protection() -> None:
    """Sweeps every prose file for wording that is false about this bundle.

    Not just the READMEs. The claims this catches were real: "no agent holds
    such a tool" was written in both READMEs while `blog_writer` demonstrably
    held `apply_patch`, which is in the backstop's own tool list.
    """
    offenders = []
    for path in PROSE_FILES:
        lowered = path.read_text(encoding="utf-8").lower()
        offenders += [
            f"{path.name}: {claim!r}" for claim in FORBIDDEN_CLAIMS if claim in lowered
        ]
    assert not offenders, f"false claims found: {offenders}"


def test_no_file_in_the_bundle_still_says_an_agent_declares_os_env() -> None:
    """The claim this whole change falsifies must not survive anywhere.

    `demo.md` and `policies/publish_gate.py` both asserted the supervisor
    declares `os_env` for a full round after it stopped being true, because
    neither was in the diff that made it untrue.
    """
    offenders = []
    for path in PROSE_FILES:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not STALE_OS_ENV_CLAIM.search(line):
                continue
            # Clause by clause, so a negation in one cannot excuse a false
            # assertion in another. The claim regex is re-applied per clause:
            # a match that only spanned a boundary was never one assertion.
            for clause in _clauses(line):
                if STALE_OS_ENV_CLAIM.search(clause) and not STALE_EXEMPT.search(clause):
                    offenders.append(f"{path.name}:{number}: {clause.strip()[:70]}")
    assert not offenders, f"stale 'declares os_env' claims: {offenders}"


def test_schedule_caveats_do_not_claim_an_unconfirmed_proposal() -> None:
    """The live transcript recorded narration, not a schedule-create call.

    This opens both prose files because the inaccurate proposal claim survived
    a passing test suite in the prior round. Keep the explicit caveat until a
    durable conversation transcript contains `sys_scheduled_task_create`.
    """
    offenders = []
    for path in SCHEDULE_CAVEAT_FILES:
        lowered = path.read_text(encoding="utf-8").lower()
        assert SCHEDULE_CAVEAT_REQUIRED in lowered, (
            f"{path.name} no longer says the schedule proposal is unconfirmed"
        )
        offenders += [
            f"{path.name}: {claim!r}"
            for claim in SCHEDULE_CAVEAT_OVERCLAIMS
            if claim in lowered
        ]
    assert not offenders, f"schedule caveats overclaim confirmed behaviour: {offenders}"


def test_blog_writer_config_documents_why_it_keeps_the_codex_harness() -> None:
    """The residual risk must be visible where the harness is chosen."""
    text = _config("blog_writer").read_text(encoding="utf-8")
    for phrase in ("apply_patch", "workspace-write", "internally_executed"):
        assert phrase in text, f"blog_writer config omits {phrase!r}"


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
