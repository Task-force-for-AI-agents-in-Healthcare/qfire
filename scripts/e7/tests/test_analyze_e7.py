"""Tests for scripts/e7/analyze_e7.py (structure + markdown; pure builder)."""
import sys
from pathlib import Path

import pytest

E7_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E7_DIR))
REPO_ROOT = E7_DIR.parents[1]

import analyze_e7 as a  # noqa: E402


def test_build_summary_structure():
    s = a.build_summary()
    assert s["experiment"] == "E7"
    assert "meta" in s and "agentdojo" in s and "injecagent" in s
    assert "judge_model" in s["meta"]
    # render must not crash and must contain both benchmark headers
    md = a.render_md(s)
    assert "AgentDojo" in md and "InjecAgent" in md


def test_render_md_handles_empty():
    empty = {
        "experiment": "E7",
        "meta": {"model": None, "judge_model": "gemma2:9b",
                 "agentdojo": {"attack": None, "benchmark_version": None},
                 "guard_on_note": "x"},
        "agentdojo": {}, "injecagent": {}, "e4_reference": None,
    }
    md = a.render_md(empty)
    assert "AgentDojo" in md and "InjecAgent" in md  # tables render even with no rows


def test_e4_reference_present_if_summary_exists():
    if not (REPO_ROOT / "bench-out" / "e4" / "summary.json").exists():
        pytest.skip("no E4 summary")
    s = a.build_summary()
    assert s["e4_reference"] is not None
    assert s["e4_reference"]["harm_on"] is not None
