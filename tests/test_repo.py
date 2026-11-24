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


def test_claude_md_matches_spec_block():
    spec = (ROOT / "SPEC.md").read_text(encoding="utf-8")
    block = spec.split("## Hard rules for the repo", 1)[1].split("```markdown\n", 1)[1].split("\n```", 1)[0]
    assert (ROOT / "CLAUDE.md").read_text(encoding="utf-8").strip() == block.strip()
