"""Tests for scripts/e7/parse_injecagent.py.

Pure helpers (split_counts, summarize) tested without any files; aggregate
exercised against real results on disk with a skip when absent.
"""
import sys
from pathlib import Path

import pytest

E7_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E7_DIR))
REPO_ROOT = E7_DIR.parents[1]

import parse_injecagent as p  # noqa: E402


def test_split_counts_dh():
    rows = [{"eval": "succ"}, {"eval": "unsucc"}, {"eval": "invalid"}]
    c = p.split_counts(rows, "dh")
    assert c["n_all"] == 3 and c["n_invalid"] == 1 and c["n_valid"] == 2
    assert c["n_breach"] == 1  # one succ


def test_split_counts_ds_two_stage():
    rows = [
        {"eval": "invalid"},
        {"eval": "succ", "eval Step 2": "succ"},   # full breach
        {"eval": "succ", "eval Step 2": "unsucc"},  # S1 only, NOT a full breach
        {"eval": "unsucc"},
    ]
    c = p.split_counts(rows, "ds")
    assert c["n_all"] == 4 and c["n_invalid"] == 1 and c["n_valid"] == 3
    assert c["s1"] == 2 and c["s2"] == 1
    assert c["n_breach"] == 1  # only S1&S2 both succ counts as a breach


def test_summarize_rates_and_ci():
    # 1 breach of 5 valid, 6 all -> asr_valid .2, asr_all ~.1667, valid_rate ~.833
    d = p.summarize({"n_all": 6, "n_invalid": 1, "n_valid": 5, "n_breach": 1})
    assert abs(d["asr_valid"] - 0.2) < 1e-9
    assert abs(d["asr_all"] - 1 / 6) < 1e-9
    assert abs(d["valid_rate"] - 5 / 6) < 1e-9
    lo, hi = d["asr_valid_ci"]
    assert 0.0 <= lo <= d["asr_valid"] <= hi <= 1.0


def test_summarize_zero_no_div_by_zero():
    d = p.summarize({"n_all": 0, "n_invalid": 0, "n_valid": 0, "n_breach": 0})
    assert d["asr_valid"] == 0.0 and d["asr_all"] == 0.0 and d["valid_rate"] == 0.0
    assert d["asr_valid_ci"] == [0.0, 0.0]


def test_summarize_all_breached():
    d = p.summarize({"n_all": 4, "n_invalid": 0, "n_valid": 4, "n_breach": 4})
    assert d["asr_valid"] == 1.0 and d["asr_all"] == 1.0


def test_aggregate_on_real_results():
    d = REPO_ROOT / "bench-out" / "e7" / "injecagent"
    if not (d / "off").exists():
        pytest.skip("no InjecAgent results yet")
    out = p.aggregate(str(d))
    for guard in ("off", "on"):
        if not (d / guard).exists():
            continue
        assert guard in out
        g = out[guard]
        assert "per_split" in g and "total" in g
        for b in list(g["per_split"].values()) + [g["total"]]:
            for k in ("asr_valid", "asr_all", "valid_rate"):
                assert 0.0 <= b[k] <= 1.0
