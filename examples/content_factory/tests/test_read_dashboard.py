"""Executable spec for ``tools/python/read_dashboard.py``.

Run it either way::

    python examples/content_factory/tests/test_read_dashboard.py
    pytest examples/content_factory/tests/

Stdlib only. Every case builds the disk state under a temporary CWD because the
tool resolves the content-factory paths from ``os.getcwd()``.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import types
from pathlib import Path

EXAMPLE_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIRECTORY = EXAMPLE_ROOT / "tools" / "python"
TOOL_PATH = TOOLS_DIRECTORY / "read_dashboard.py"


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

    sys.path.insert(0, str(TOOLS_DIRECTORY))
    try:
        spec = importlib.util.spec_from_file_location("read_dashboard_under_test", TOOL_PATH)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.read_dashboard
    finally:
        sys.path.pop(0)


read_dashboard = _load_tool()


class sandbox:
    """Run one case in a throwaway CWD with an independent factory tree."""

    def __enter__(self) -> Path:
        self.previous = os.getcwd()
        self.directory = tempfile.mkdtemp(prefix="content-factory-dashboard-test-")
        os.chdir(self.directory)
        root = Path(self.directory) / "examples" / "content_factory"
        root.mkdir(parents=True)
        (root / "config.yaml").write_text(
            "guardrails:\n  max_articles_per_cycle: 3\n", encoding="utf-8"
        )
        return root

    def __exit__(self, *_exc) -> None:
        os.chdir(self.previous)


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
""",
        encoding="utf-8",
    )


def _write(root: Path, relative_path: str, body: str = "artifact\n") -> None:
    path = root / "artifacts" / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _entry(snapshot: dict, slug: str) -> dict:
    return next(entry for entry in snapshot["entries"] if entry["slug"] == slug)


def test_empty_artifacts_tree_reports_every_backlog_entry_in_file_order():
    with sandbox() as root:
        _backlog(root)
        (root / "artifacts").mkdir()
        snapshot = read_dashboard()

    assert [entry["slug"] for entry in snapshot["entries"]] == ["empty", "partial", "one-social", "shipped"]
    assert snapshot["shipped_article_count"] == 0
    assert snapshot["article_ceiling"] == 3
    assert len(snapshot["utc_date"]) == 10
    assert _entry(snapshot, "empty")["artifacts"] == {
        "outline": False,
        "draft": False,
        "social_variants": [],
        "published_files": [],
        "posted_channels": [],
    }


def test_partially_produced_slug_reports_only_real_staged_artifacts():
    with sandbox() as root:
        _backlog(root)
        _write(root, "outlines/partial.md")
        _write(root, "drafts/partial.md")
        snapshot = read_dashboard()

    assert _entry(snapshot, "partial")["artifacts"] == {
        "outline": True,
        "draft": True,
        "social_variants": [],
        "published_files": [],
        "posted_channels": [],
    }


def test_one_social_variant_is_reported_without_implying_the_other_exists():
    with sandbox() as root:
        _backlog(root)
        _write(root, "social/one-social-linkedin.md")
        snapshot = read_dashboard()

    assert _entry(snapshot, "one-social")["artifacts"]["social_variants"] == ["linkedin"]
    assert _entry(snapshot, "one-social")["artifacts"]["posted_channels"] == []


def test_fully_shipped_slug_counts_only_the_published_draft_as_an_article():
    with sandbox() as root:
        _backlog(root)
        _write(root, "outlines/shipped.md")
        _write(root, "drafts/shipped.md")
        _write(root, "social/shipped-x.md")
        _write(root, "social/shipped-linkedin.md")
        _write(root, "published/shipped/shipped.md")
        _write(root, "published/shipped/shipped-x.md")
        _write(root, "published/shipped/shipped-linkedin.md")
        _write(root, "published/shipped/posted-x.json", "{}\n")
        _write(root, "published/shipped/posted-linkedin.json", "{}\n")
        _write(root, "published/partial/posted-x.json", "{}\n")
        snapshot = read_dashboard()

    assert snapshot["shipped_article_count"] == 1
    assert _entry(snapshot, "shipped")["artifacts"] == {
        "outline": True,
        "draft": True,
        "social_variants": ["x", "linkedin"],
        "published_files": [
            "posted-linkedin.json",
            "posted-x.json",
            "shipped-linkedin.md",
            "shipped-x.md",
            "shipped.md",
        ],
        "posted_channels": ["x", "linkedin"],
    }


def test_read_dashboard_never_writes_to_the_factory_tree():
    with sandbox() as root:
        _backlog(root)
        _write(root, "drafts/partial.md")
        before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
        read_dashboard()
        after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

    assert after == before


def main() -> int:
    tests = [(name, test) for name, test in sorted(globals().items()) if name.startswith("test_") and callable(test)]
    failures: list[str] = []
    print(f"read_dashboard: {len(tests)} cases\n")
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
    print(f"all {len(tests)} read_dashboard cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
