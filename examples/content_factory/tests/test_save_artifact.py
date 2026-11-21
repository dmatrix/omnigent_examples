"""Executable spec for ``tools/python/save_artifact.py``.

The ``cycle`` kind appends and every other kind truncates, which is easy to
regress in opposite directions. Run it either way::

    python examples/content_factory/tests/test_save_artifact.py
    pytest examples/content_factory/tests/

Stdlib only. ``save_artifact`` is decorated with ``@tool``; if the Omnigent
client is not installed, an identity decorator stands in. Every case runs in a
temporary directory, because the tool resolves ``artifacts/`` from
``os.getcwd()``.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import types
from datetime import UTC, datetime
from pathlib import Path

EXAMPLE_ROOT = Path(__file__).resolve().parent.parent
TOOL_PATH = EXAMPLE_ROOT / "tools" / "python" / "save_artifact.py"


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

    spec = importlib.util.spec_from_file_location("save_artifact_under_test", TOOL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.save_artifact


save_artifact = _load_tool()

RETURN_KEYS = ["bytes", "kind", "path"]


class sandbox:
    """Run one case in a throwaway CWD, since the tool resolves paths from it."""

    def __enter__(self) -> Path:
        self.previous = os.getcwd()
        self.directory = tempfile.mkdtemp(prefix="content-factory-test-")
        os.chdir(self.directory)
        return Path(self.directory)

    def __exit__(self, *_exc) -> None:
        os.chdir(self.previous)


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


# ══ the cycle kind APPENDS ═════════════════════════════════════════════════


def test_two_cycles_on_the_same_utc_day_retain_both_entries():
    with sandbox():
        first = save_artifact(kind="cycle", slug="alpha", content="alpha shipped.\n")
        second = save_artifact(kind="cycle", slug="bravo", content="bravo shipped.\n")
        assert first["path"] == second["path"]  # one log per UTC day
        assert Path(first["path"]).name == f"{datetime.now(UTC):%Y-%m-%d}-cycle.md"
        body = _read(first["path"])
        assert "alpha shipped." in body  # this is what mode "w" destroyed
        assert "bravo shipped." in body
        assert body.index("alpha shipped.") < body.index("bravo shipped.")


def test_appended_entries_are_separated_and_attributed():
    with sandbox():
        log = save_artifact(kind="cycle", slug="alpha", content="alpha shipped.\n")
        save_artifact(kind="cycle", slug="bravo", content="bravo shipped.\n")
        save_artifact(kind="cycle", slug="charlie", content="charlie shipped.\n")
        body = _read(log["path"])
        assert body.count("\n---\n") == 2  # one rule between each pair
        assert "*Cycle entry: `bravo`" in body
        assert "*Cycle entry: `charlie`" in body
        assert "*Cycle entry: `alpha`" not in body  # the first entry opens the file


def test_a_cycle_entry_without_a_trailing_newline_still_separates():
    with sandbox():
        log = save_artifact(kind="cycle", slug="alpha", content="no trailing newline")
        save_artifact(kind="cycle", slug="bravo", content="bravo shipped.\n")
        body = _read(log["path"])
        assert "no trailing newline\n\n---\n" in body


def test_cycle_bytes_is_the_resulting_file_size():
    with sandbox():
        first = save_artifact(kind="cycle", slug="alpha", content="alpha.\n")
        second = save_artifact(kind="cycle", slug="bravo", content="bravo.\n")
        # Documented contract: bytes is the size of the file AFTER the call.
        assert second["bytes"] == os.path.getsize(second["path"])
        assert second["bytes"] > first["bytes"]


# ══ every other kind still OVERWRITES ══════════════════════════════════════

OVERWRITE_KINDS = [
    ("outline", {}, "outlines/alpha.md"),
    ("draft", {}, "drafts/alpha.md"),
    ("social", {"variant": "x"}, "social/alpha-x.md"),
    ("social", {"variant": "linkedin"}, "social/alpha-linkedin.md"),
    ("dashboard", {}, "dashboard.md"),
]


def test_non_cycle_kinds_are_truncated_on_rewrite():
    for kind, extra, tail in OVERWRITE_KINDS:
        with sandbox():
            save_artifact(kind=kind, slug="alpha", content="FIRST VERSION\n", **extra)
            revised = save_artifact(kind=kind, slug="alpha", content="REVISED\n", **extra)
            # A bounced draft is replaced, not accumulated.
            assert _read(revised["path"]) == "REVISED\n", (kind, extra)
            assert revised["path"].endswith(tail.replace("/", os.sep))
            assert revised["bytes"] == len(b"REVISED\n")


def test_every_kind_returns_the_same_three_keys():
    with sandbox():
        results = [save_artifact(kind="cycle", slug="alpha", content="x\n")]
        results += [
            save_artifact(kind=kind, slug="alpha", content="x\n", **extra)
            for kind, extra, _tail in OVERWRITE_KINDS
        ]
        for result in results:
            assert sorted(result) == RETURN_KEYS, result
            assert result["bytes"] == os.path.getsize(result["path"])


def test_each_kind_keeps_its_destination():
    with sandbox() as root:
        save_artifact(kind="cycle", slug="alpha", content="x\n")
        for kind, extra, _tail in OVERWRITE_KINDS:
            save_artifact(kind=kind, slug="alpha", content="x\n", **extra)
        artifacts = root / "examples" / "content_factory" / "artifacts"
        staged = sorted(p.relative_to(artifacts).as_posix() for p in artifacts.rglob("*.md"))
        assert staged == [
            f"cycles/{datetime.now(UTC):%Y-%m-%d}-cycle.md",
            "dashboard.md",
            "drafts/alpha.md",
            "outlines/alpha.md",
            "social/alpha-linkedin.md",
            "social/alpha-x.md",
        ]


# ══ the error path is unchanged ════════════════════════════════════════════

BAD_KIND = {
    "error": "kind must be cycle, outline, draft, dashboard, or social with variant x or linkedin"
}


def test_unknown_kind_and_bad_variant_are_rejected():
    with sandbox() as root:
        assert save_artifact(kind="nope", slug="a", content="x") == BAD_KIND
        assert save_artifact(kind="social", slug="a", content="x", variant="mastodon") == BAD_KIND
        assert save_artifact(kind="social", slug="a", content="x") == BAD_KIND
        # A rejected call writes nothing at all.
        assert not (root / "examples").exists()


# ── plain-python runner ────────────────────────────────────────────────────


def main() -> int:
    tests = [(n, o) for n, o in sorted(globals().items()) if n.startswith("test_") and callable(o)]
    failures: list[str] = []
    print(f"save_artifact: {len(tests)} cases\n")
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
    print(f"all {len(tests)} save_artifact cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
