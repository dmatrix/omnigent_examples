"""Executable spec for ``read_backlog(include_artifacts=True)``.

Run it either way::

    python examples/content_factory/tests/test_read_dashboard.py
    pytest examples/content_factory/tests/

Stdlib only. The tool is imported by path without changing ``sys.path`` so this
test exercises the same single-module import shape as the real tool loader.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import types
from pathlib import Path

EXAMPLE_ROOT = Path(__file__).resolve().parent.parent
TOOL_PATH = EXAMPLE_ROOT / "tools" / "python" / "read_backlog.py"


def _load_tool():
    """Import the tool by path, stubbing the ``@tool`` decorator if needed."""
    try:  # pragma: no cover - depends on the environment, not the tool
        import omnigent_client.tools  # noqa: F401
    except ImportError:
        tools = types.ModuleType("omnigent_client.tools")
        tools.tool = lambda fn: fn  # type: ignore[attr-defined]
        client = types.ModuleType("omnigent_client")
        client.tools = tools  # type: ignore[attr-defined]
        sys.modules.setdefault("omnigent_client", client)
        sys.modules.setdefault("omnigent_client.tools", tools)

    spec = importlib.util.spec_from_file_location("read_backlog_under_test", TOOL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.read_backlog


read_backlog = _load_tool()


def _article_ceiling_of_shipped_config() -> int | None:
    """Run the tool's own ceiling parser against the repo's real config.yaml.

    Every other ceiling case uses a fixture. This one closes the loop: if a
    future config edit breaks the key path the parser walks, the dashboard
    loses its ceiling silently, and only reading the shipped file catches it.
    """
    module_spec = importlib.util.spec_from_file_location("read_backlog_shipped", TOOL_PATH)
    assert module_spec and module_spec.loader
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    previous = os.getcwd()
    os.chdir(EXAMPLE_ROOT.parent.parent)
    try:
        return module._article_ceiling()
    finally:
        os.chdir(previous)


class sandbox:
    """Run one case in a throwaway CWD with an independent factory tree."""

    def __enter__(self) -> Path:
        self.previous = os.getcwd()
        self.directory = tempfile.mkdtemp(prefix="content-factory-dashboard-test-")
        os.chdir(self.directory)
        root = Path(self.directory) / "examples" / "content_factory"
        root.mkdir(parents=True)
        return root

    def __exit__(self, *_exc) -> None:
        os.chdir(self.previous)


def _config(root: Path, ceiling: str = "3") -> None:
    root.joinpath("config.yaml").write_text(
        f"""guardrails:
  policies:
    publish_gate:
      function:
        arguments:
          max_articles_per_cycle: {ceiling}
""",
        encoding="utf-8",
    )


def _backlog(root: Path) -> None:
    root.joinpath("backlog.md").write_text(
        """# Content backlog

## empty
- title: Empty artifact tree
- summary: none
- status: READY
- sources:

## partial
- title: Partially produced
- summary: none
- status: DRAFTED
- sources:

## one-social
- title: One social variant
- summary: none
- status: APPROVED
- sources:

## shipped
- title: Fully shipped
- summary: none
- status: PUBLISHED
- sources:

## shipped-extra
- title: Prefix-slug guard
- summary: none
- status: READY
- sources:
""",
        encoding="utf-8",
    )


def _write(root: Path, relative_path: str, body: str = "artifact\n") -> None:
    path = root / "artifacts" / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _snapshot() -> dict:
    return read_backlog(include_artifacts=True)


def _entry(snapshot: dict, slug: str) -> dict:
    return next(entry for entry in snapshot["entries"] if entry["slug"] == slug)


def test_empty_artifacts_tree_reports_every_backlog_entry_in_file_order():
    with sandbox() as root:
        _config(root)
        _backlog(root)
        (root / "artifacts").mkdir()
        snapshot = _snapshot()

    assert [entry["slug"] for entry in snapshot["entries"]] == [
        "empty",
        "partial",
        "one-social",
        "shipped",
        "shipped-extra",
    ]
    assert snapshot["published_article_count"] == 0
    assert snapshot["article_ceiling"] == 3
    assert len(snapshot["utc_date"]) == 10
    assert _entry(snapshot, "empty")["artifacts"] == {
        "outline": False,
        "draft": False,
        "social_variants": [],
        "published_files": [],
        "posted_channels": [],
    }


def test_existing_read_backlog_calls_keep_their_original_shape():
    with sandbox() as root:
        _backlog(root)
        result = read_backlog(status="READY", limit=1)

    assert result == {
        "items": [
            {
                "slug": "empty",
                "title": "Empty artifact tree",
                "summary": "none",
                "status": "READY",
                "sources": [],
            }
        ],
        "counts": {"READY": 2, "DRAFTED": 1, "APPROVED": 1, "PUBLISHED": 1},
    }


def test_partially_produced_slug_reports_only_real_staged_artifacts():
    with sandbox() as root:
        _config(root)
        _backlog(root)
        _write(root, "outlines/partial.md")
        _write(root, "drafts/partial.md")
        snapshot = _snapshot()

    assert _entry(snapshot, "partial")["artifacts"] == {
        "outline": True,
        "draft": True,
        "social_variants": [],
        "published_files": [],
        "posted_channels": [],
    }


def test_social_variants_match_exact_slug_filenames_not_prefixes():
    with sandbox() as root:
        _config(root)
        _backlog(root)
        _write(root, "social/shipped-extra-x.md")
        snapshot = _snapshot()

    assert _entry(snapshot, "shipped")["artifacts"]["social_variants"] == []
    assert _entry(snapshot, "shipped-extra")["artifacts"]["social_variants"] == ["x"]


def test_published_article_counts_durable_draft_and_records_zero_or_malformed_posts():
    with sandbox() as root:
        _config(root)
        _backlog(root)
        _write(root, "published/shipped/shipped.md")
        _write(root, "published/shipped/nested/ignored.md")
        no_posts = _snapshot()
        _write(root, "published/shipped/posted-x.json", "{")
        malformed_post = _snapshot()

    assert no_posts["published_article_count"] == 1
    assert _entry(no_posts, "shipped")["artifacts"]["posted_channels"] == []
    assert _entry(no_posts, "shipped")["artifacts"]["published_files"] == ["shipped.md"]
    assert _entry(malformed_post, "shipped")["artifacts"]["posted_channels"] == ["x"]


def test_unreadable_or_nonmatching_config_omits_the_ceiling_without_guessing():
    with sandbox() as root:
        _backlog(root)
        absent = _snapshot()
        root.joinpath("config.yaml").write_text(
            "guardrails:\n  policies:\n    renamed_gate:\n      function:\n        arguments:\n          max_articles_per_cycle: 7\n",
            encoding="utf-8",
        )
        renamed = _snapshot()
        _config(root, '"3"')
        quoted = _snapshot()
        _config(root, "3 # comment")
        commented = _snapshot()
        root.joinpath("config.yaml").unlink()
        root.joinpath("config.yaml").mkdir()
        unreadable = _snapshot()

    for snapshot in (absent, renamed, quoted, commented, unreadable):
        assert "article_ceiling" not in snapshot


def test_ceiling_parser_ignores_prompt_text_and_accepts_commented_real_argument():
    with sandbox() as root:
        _backlog(root)
        root.joinpath("config.yaml").write_text(
            """prompt: |
  max_articles_per_cycle: 9
guardrails:
  policies:
    publish_gate:
      type: function
      function:
        arguments:
          # This is the actual policy setting.
          max_articles_per_cycle: 3
""",
            encoding="utf-8",
        )
        snapshot = _snapshot()

    assert snapshot["article_ceiling"] == 3


def test_ceiling_survives_policies_declared_before_and_after_publish_gate():
    """The parser must not depend on publish_gate coming first.

    `_article_ceiling` used to scan config.yaml as an ordered line sequence, so
    any policy inserted before `publish_gate` silently removed the ceiling from
    the dashboard. It now descends the key path by indentation instead.
    """
    with sandbox() as root:
        _backlog(root)
        root.joinpath("config.yaml").write_text(
            """guardrails:
  policies:
    no_self_modification:
      type: function
      function:
        path: omnigent.policies.builtins.orchestration.read_only_os
        arguments:
          deny_reason: |
            Not a ceiling: max_articles_per_cycle: 99
    publish_gate:
      type: function
      function:
        path: examples.content_factory.policies.publish_gate.publish_gate
        arguments:
          max_articles_per_cycle: 3
    user_daily_cost_budget:
      type: function
      function:
        arguments:
          max_cost_usd: 5.0
""",
            encoding="utf-8",
        )
        before_and_after = _snapshot()

        root.joinpath("config.yaml").write_text(
            """guardrails:
  policies:
    publish_gate:
      type: function
      function:
        arguments:
          max_articles_per_cycle: 3
    guarded_tools:
      type: function
      function:
        arguments:
          threshold: 0
""",
            encoding="utf-8",
        )
        gate_first = _snapshot()

    assert before_and_after["article_ceiling"] == 3
    assert gate_first["article_ceiling"] == 3


def test_ceiling_reads_only_publish_gates_own_argument():
    """A sibling policy's identically named argument must not be picked up."""
    with sandbox() as root:
        _backlog(root)
        root.joinpath("config.yaml").write_text(
            """guardrails:
  policies:
    decoy_gate:
      function:
        arguments:
          max_articles_per_cycle: 99
    publish_gate:
      function:
        arguments:
          max_articles_per_cycle: 2
""",
            encoding="utf-8",
        )
        sibling_decoy = _snapshot()

        # publish_gate present but carrying no ceiling, while a sibling does.
        root.joinpath("config.yaml").write_text(
            """guardrails:
  policies:
    decoy_gate:
      function:
        arguments:
          max_articles_per_cycle: 99
    publish_gate:
      function:
        arguments:
          something_else: 1
""",
            encoding="utf-8",
        )
        gate_without_ceiling = _snapshot()

    assert sibling_decoy["article_ceiling"] == 2
    assert "article_ceiling" not in gate_without_ceiling


def test_ceiling_is_omitted_when_the_key_path_is_broken_at_any_level():
    """Each missing level omits rather than guesses, as before."""
    broken = {
        "no guardrails": "policies:\n  publish_gate:\n    function:\n      arguments:\n        max_articles_per_cycle: 3\n",
        "no policies": "guardrails:\n  publish_gate:\n    function:\n      arguments:\n        max_articles_per_cycle: 3\n",
        "no function": "guardrails:\n  policies:\n    publish_gate:\n      arguments:\n        max_articles_per_cycle: 3\n",
        "no arguments": "guardrails:\n  policies:\n    publish_gate:\n      function:\n        max_articles_per_cycle: 3\n",
        "guardrails nested, not top level": "wrapper:\n  guardrails:\n    policies:\n      publish_gate:\n        function:\n          arguments:\n            max_articles_per_cycle: 3\n",
    }
    results = {}
    for label, text in broken.items():
        with sandbox() as root:
            _backlog(root)
            root.joinpath("config.yaml").write_text(text, encoding="utf-8")
            results[label] = _snapshot()

    for label, snapshot in results.items():
        assert "article_ceiling" not in snapshot, label


def test_ceiling_is_read_from_the_real_shipped_config():
    """The parser and the config this example actually ships must agree."""
    from_disk = _article_ceiling_of_shipped_config()
    assert from_disk == 3, f"shipped config.yaml yields {from_disk!r}, expected 3"


def test_dashboard_backlog_read_error_is_returned():
    with sandbox() as root:
        _config(root)
        result = _snapshot()

    assert result["error"].startswith("Unable to read backlog:")


def test_dashboard_mode_never_writes_to_the_factory_tree():
    with sandbox() as root:
        _config(root)
        _backlog(root)
        _write(root, "drafts/partial.md")
        before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
        _snapshot()
        after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

    assert after == before


def main() -> int:
    tests = [(name, test) for name, test in sorted(globals().items()) if name.startswith("test_") and callable(test)]
    failures: list[str] = []
    print(f"read_backlog dashboard mode: {len(tests)} cases\n")
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
    print(f"all {len(tests)} read_backlog dashboard cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
