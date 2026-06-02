"""Tests for scripts/e7/parse_agentdojo.py.

The PURE metric helper ``summarize`` is tested without any AgentDojo logs.
``aggregate`` is exercised with a real-runs integration test that skips when
no runs are present yet.
"""
import os
import sys
from pathlib import Path

import pytest

# Make the e7 scripts dir importable regardless of pytest rootdir.
E7_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E7_DIR))
REPO_ROOT = E7_DIR.parents[1]

import parse_agentdojo as p  # noqa: E402


# ---------------------------------------------------------------------------
# Pure helper: summarize
# ---------------------------------------------------------------------------
def _is_ci(ci, rate):
    assert isinstance(ci, list) and len(ci) == 2
    lo, hi = ci
    assert 0.0 <= lo <= rate <= hi <= 1.0
    return True


def test_summarize_basic():
    d = p.summarize(n_benign_solved=1, n_benign=2,
                    n_attack_solved=0, n_sec_contained=1, n_security=2)
    assert d["benign_utility"] == 0.5
    assert d["utility_under_attack"] == 0.0
    # 1 of 2 security results NOT contained -> ASR 0.5
    assert d["targeted_asr"] == 0.5
    assert d["n_benign"] == 2
    assert d["n_security"] == 2
    assert _is_ci(d["benign_utility_ci"], d["benign_utility"])
    assert _is_ci(d["uua_ci"], d["utility_under_attack"])
    assert _is_ci(d["targeted_asr_ci"], d["targeted_asr"])


def test_summarize_all_contained():
    d = p.summarize(n_benign_solved=2, n_benign=2,
                    n_attack_solved=3, n_sec_contained=3, n_security=3)
    assert d["targeted_asr"] == 0.0
    assert d["benign_utility"] == 1.0
    assert d["utility_under_attack"] == 1.0
    assert _is_ci(d["targeted_asr_ci"], 0.0)


def test_summarize_none_contained():
    # 0 of 4 contained -> all attacks succeeded -> ASR 1.0
    d = p.summarize(n_benign_solved=0, n_benign=4,
                    n_attack_solved=0, n_sec_contained=0, n_security=4)
    assert d["targeted_asr"] == 1.0
    assert _is_ci(d["targeted_asr_ci"], 1.0)


def test_summarize_zero_security_no_div_by_zero():
    d = p.summarize(n_benign_solved=1, n_benign=3,
                    n_attack_solved=0, n_sec_contained=0, n_security=0)
    assert d["targeted_asr"] == 0.0
    assert d["targeted_asr_ci"] == [0.0, 0.0]
    assert d["n_security"] == 0


def test_summarize_zero_benign_no_div_by_zero():
    d = p.summarize(n_benign_solved=0, n_benign=0,
                    n_attack_solved=0, n_sec_contained=0, n_security=0)
    assert d["benign_utility"] == 0.0
    assert d["benign_utility_ci"] == [0.0, 0.0]
    assert d["utility_under_attack"] == 0.0
    assert d["uua_ci"] == [0.0, 0.0]


# ---------------------------------------------------------------------------
# Integration: aggregate over whatever real runs exist on disk
# ---------------------------------------------------------------------------
def test_aggregate_on_real_runs():
    runs_dir = REPO_ROOT / "runs" / "e7"
    if not (runs_dir / "off").exists():
        pytest.skip("runs/e7/off not present yet (background smoke may be running)")

    out = p.aggregate(str(runs_dir))
    assert isinstance(out, dict)

    for guard in ("off", "on"):
        if not (runs_dir / guard).exists():
            continue
        assert guard in out, f"{guard} dir exists but missing from output"
        g = out[guard]
        assert "per_suite" in g and "pooled" in g
        blocks = list(g["per_suite"].values()) + [g["pooled"]]
        for b in blocks:
            for rate_key in ("benign_utility", "utility_under_attack", "targeted_asr"):
                assert 0.0 <= b[rate_key] <= 1.0, f"{guard} {rate_key} out of range"
            for ci_key in ("benign_utility_ci", "uua_ci", "targeted_asr_ci"):
                lo, hi = b[ci_key]
                assert 0.0 <= lo <= hi <= 1.0
