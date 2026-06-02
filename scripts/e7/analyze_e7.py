#!/usr/bin/env python3
"""E7 aggregator: merge the AgentDojo + InjecAgent parsers (and the E4 mock-EHR
result for side-by-side) into ``bench-out/e7/summary.json`` and a human-readable
``bench-out/e7/results.md``.

Pure ``build_summary`` (returns the dict) is separated from the file-writing
``main`` so it can be unit-tested. Timestamps are stamped in ``main``, not in
``build_summary`` (keeps the builder deterministic).

Run::

    .venv-e7/bin/python scripts/e7/analyze_e7.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

E7_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(E7_DIR))
REPO_ROOT = E7_DIR.parents[1]

import parse_agentdojo  # noqa: E402
import parse_injecagent  # noqa: E402


def _read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def build_summary(runs_dir: str = "runs/e7",
                  injecagent_dir: str = "bench-out/e7/injecagent",
                  e4_summary: str = "bench-out/e4/summary.json",
                  agentdojo_manifest: str = "bench-out/e7/agentdojo_manifest.json",
                  injecagent_manifest: str = "bench-out/e7/injecagent_manifest.json") -> dict:
    """Assemble the E7 summary dict (no timestamps; deterministic)."""
    agentdojo = parse_agentdojo.aggregate(runs_dir)
    injecagent = parse_injecagent.aggregate(injecagent_dir)

    ad_manifest = _read_json(REPO_ROOT / agentdojo_manifest) or {}
    ia_manifest = _read_json(REPO_ROOT / injecagent_manifest) or {}
    e4 = _read_json(REPO_ROOT / e4_summary)

    model = ad_manifest.get("model") or ia_manifest.get("model")

    e4_ref = None
    if e4:
        e4_ref = {
            "harm_off": e4.get("harm_off"), "harm_on": e4.get("harm_on"),
            "harm_ci_off": e4.get("harm_ci_off"), "harm_ci_on": e4.get("harm_ci_on"),
            "benign_off": e4.get("benign_off"), "benign_on": e4.get("benign_on"),
            "n_attack": e4.get("n_attack"), "n_benign": e4.get("n_benign"),
            "note": "E4 mock-EHR ReAct agent (llama3.1:8b); harmful-action rate with/without QFIRE.",
        }

    return {
        "experiment": "E7",
        "meta": {
            "model": model,
            "agentdojo": {
                "attack": ad_manifest.get("attack"),
                "chains": ad_manifest.get("chains"),
                "subset": ad_manifest.get("subset"),
                "benchmark_version": (agentdojo.get("off") or agentdojo.get("on") or {}).get("benchmark_version"),
            },
            "injecagent": {
                "chain": ia_manifest.get("chain", "e7_injecagent"),
                "n_per_split_kept": ia_manifest.get("n_per_split_kept"),
                "splits": ["dh", "ds"],
            },
            "judge_model": "gemma2:9b",
            "guard_on_note": ("per-suite domain-scope chains e7_<suite> / e7_injecagent "
                              "(injection default + fixed-domain positive-security scope); "
                              "E7-local injection variants fix shared-rule FPs that only "
                              "surface on agent transcripts. See E7 findings for disclosed deviations."),
        },
        "agentdojo": agentdojo,
        "injecagent": injecagent,
        "e4_reference": e4_ref,
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------
def _pct(x):
    return "—" if x is None else f"{x*100:.1f}%"


def _ci(c):
    return "" if not c else f" [{c[0]*100:.0f}–{c[1]*100:.0f}]"


def render_md(s: dict) -> str:
    L = ["# E7 — Standard agent benchmarks (AgentDojo + InjecAgent)", ""]
    m = s["meta"]
    L += [f"**Agent model:** `{m.get('model')}` · **Judge:** `{m.get('judge_model')}`  ",
          f"**AgentDojo attack:** `{m['agentdojo'].get('attack')}` · "
          f"benchmark_version `{m['agentdojo'].get('benchmark_version')}`  ",
          f"**Guard ON:** {m.get('guard_on_note')}", ""]

    # AgentDojo table
    L += ["## AgentDojo (per-suite + pooled)", "",
          "Targeted ASR = fraction of security cases where the attacker goal was achieved "
          "(lower is better). Benign Utility / Utility-Under-Attack higher is better. "
          "Wilson 95% CIs in brackets (percent).", "",
          "| suite | guard | Benign Utility | Utility-Under-Attack | Targeted ASR | n(benign/sec) |",
          "|---|---|---|---|---|---|"]
    ad = s["agentdojo"]
    suites = sorted({su for g in ("off", "on") if g in ad for su in ad[g]["per_suite"]})
    for su in suites + ["POOLED"]:
        for g in ("off", "on"):
            if g not in ad:
                continue
            b = ad[g]["pooled"] if su == "POOLED" else ad[g]["per_suite"].get(su)
            if not b:
                continue
            L.append(f"| {su} | {g} | {_pct(b['benign_utility'])}{_ci(b['benign_utility_ci'])} "
                     f"| {_pct(b['utility_under_attack'])}{_ci(b['uua_ci'])} "
                     f"| {_pct(b['targeted_asr'])}{_ci(b['targeted_asr_ci'])} "
                     f"| {b['n_benign']}/{b['n_security']} |")
    L.append("")

    # InjecAgent table
    L += ["## InjecAgent (dh / ds / total)", "",
          "ASR = attack success rate (lower is better). Valid Rate = fraction of agent "
          "responses parseable as a tool action.", "",
          "| split | guard | ASR-valid | ASR-all | Valid Rate | n(breach/valid/all) |",
          "|---|---|---|---|---|---|"]
    ia = s["injecagent"]
    for split in ("dh", "ds", "total"):
        for g in ("off", "on"):
            if g not in ia:
                continue
            b = ia[g]["total"] if split == "total" else ia[g]["per_split"].get(split)
            if not b:
                continue
            L.append(f"| {split} | {g} | {_pct(b['asr_valid'])}{_ci(b['asr_valid_ci'])} "
                     f"| {_pct(b['asr_all'])} | {_pct(b['valid_rate'])} "
                     f"| {b['n_breach']}/{b['n_valid']}/{b['n_all']} |")
    L.append("")

    # E4 side-by-side
    if s.get("e4_reference"):
        e4 = s["e4_reference"]
        L += ["## Side-by-side with E4 (healthcare mock-EHR)", "",
              "| metric | guard off | guard on |",
              "|---|---|---|",
              f"| E4 harmful-action rate | {_pct(e4['harm_off'])} | {_pct(e4['harm_on'])} |",
              f"| E4 benign completion | {_pct(e4['benign_off'])} | {_pct(e4['benign_on'])} |",
              "",
              f"_{e4['note']}_", ""]
    return "\n".join(L)


def main() -> int:
    from datetime import datetime, timezone
    s = build_summary()
    s["meta"]["timestamp"] = datetime.now(timezone.utc).isoformat()
    out_dir = REPO_ROOT / "bench-out" / "e7"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(s, indent=2))
    (out_dir / "results.md").write_text(render_md(s))
    print(render_md(s))
    print(f"\n-> {out_dir/'summary.json'}\n-> {out_dir/'results.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
