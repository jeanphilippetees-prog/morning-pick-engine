"""Repo-level guards that keep the hard rules in CLAUDE.md true."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANNED = re.compile(r"wealthsimple|questrade|ibkr|ib_insync|alpaca|place_order|submit_order", re.I)


def test_required_docs_exist():
    for rel in ["CLAUDE.md", "SPEC.md", "docs/rules.md", "docs/factors.md", "docs/outputs.md"]:
        assert (ROOT / rel).is_file(), rel


def test_no_broker_code_in_engine():
    for path in (ROOT / "engine").rglob("*.py"):
        assert not BANNED.search(path.read_text(encoding="utf-8")), path


def test_claude_md_keeps_every_spec_rule():
    """CLAUDE.md starts as the spec's block word for word; later PM rules are added after it."""
    spec = (ROOT / "SPEC.md").read_text(encoding="utf-8")
    block = spec.split("## Hard rules for the repo", 1)[1].split("```markdown\n", 1)[1].split("\n```", 1)[0]
    assert (ROOT / "CLAUDE.md").read_text(encoding="utf-8").strip().startswith(block.strip())


def test_no_committed_file_over_10_mb():
    import subprocess

    import pytest

    from engine.files import MAX_BYTES

    try:
        tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    big = [p for p in tracked.decode().split("\0") if p and (ROOT / p).is_file()
           and (ROOT / p).stat().st_size > MAX_BYTES]
    assert big == []
