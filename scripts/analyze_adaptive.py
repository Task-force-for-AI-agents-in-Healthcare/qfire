#!/usr/bin/env python3
"""Aggregate the E1 adaptive-attack panel into bench-out/adaptive/results.md
(+ summary.json). Recall (= block_rate on the all-attack set) per (set x detector),
the QFIRE-scope-vs-classifier gap, and the Phase-2 evasion rate / median iterations.
"""
import glob
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(BASE, "bench-out/adaptive")
SETS = ["impersonation_healthcare",
        "paraphrase_evaded", "encoded_healthcare", "encoded_injection"]
SCOPE_CHAIN = {"impersonation_healthcare": "hipaa_phi",
               "paraphrase_evaded": "hipaa_phi",
               "encoded_healthcare": "hipaa_phi",
               "encoded_injection": "default"}


def recall_of(bench_json):
    return bench_json["reports"][0]["overall"]["block_rate"]


def gap(scope, classifier):
    return round(scope - classifier, 4)


def pct(x):
    return f"{x*100:.1f}%"


def _recall(set_name, chain):
    p = os.path.join(ROOT, f"{set_name}__{chain}", "bench.json")
    return recall_of(json.load(open(p))) if os.path.exists(p) else None


def _promptguard(set_name):
    p = os.path.join(ROOT, f"{set_name}__promptguard.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p))
    # baselines.py nests per-model metrics under "results"; fall back to top-level.
    res = d.get("results", d)
    for k, v in res.items():
        if isinstance(v, dict) and "recall" in v and "promptguard" in k.lower():
            return v["recall"]
    return None


def _sentinel(set_name):
    p = os.path.join(ROOT, f"{set_name}__sentinel.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p))
    res = d.get("results", d)
    for k, v in res.items():
        if isinstance(v, dict) and "recall" in v and "sentinel" in k.lower():
            return v["recall"]
    return None


def main():
    rows, summary = [], {}
    for s in SETS:
        deb = _recall(s, "bench_deberta")
        scope = _recall(s, SCOPE_CHAIN[s])
        phi = _recall(s, "bench_phi")
        judge = _recall(s, "judge_scope")
        pg = _promptguard(s)
        sent = _sentinel(s)
        summary[s] = {"deberta": deb, "promptguard2": pg, "sentinel": sent,
                      "scope": scope, "phi": phi, "judge": judge}
        rows.append((s, deb, pg, sent, scope, phi, judge))

    ev = None
    elog = os.path.join(BASE, "corpora/adaptive/paraphrase_evaded/evade_log.json")
    if os.path.exists(elog):
        d = json.load(open(elog))
        ev = {"n": d["n"], "evasion_rate": d["evasion_rate"],
              "median_iters": d["median_iters_to_evade"]}
        summary["paraphrase_evade_stats"] = ev

    def cell(x):
        return pct(x) if isinstance(x, (int, float)) else "—"

    lines = ["# E1 — Adaptive Attacks vs the Scope Firewall — Results", "",
             "Recall = fraction of adaptive attacks BLOCKed (higher = more robust). "
             "'—' = detector not run. scope = QFIRE scope+PHI chain.", "",
             "| adaptive set | DeBERTa | PromptGuard-2 | Sentinel | QFIRE scope+PHI | PHI-only | judge-only | scope−classifier gap |",
             "|---|---|---|---|---|---|---|---|"]
    for (s, deb, pg, sent, scope, phi, judge) in rows:
        cls = max([x for x in (deb, pg, sent) if isinstance(x, (int, float))], default=None)
        g = gap(scope, cls) if isinstance(scope, (int, float)) and isinstance(cls, (int, float)) else None
        lines.append(f"| {s} | {cell(deb)} | {cell(pg)} | {cell(sent)} | {cell(scope)} | {cell(phi)} | "
                     f"{cell(judge)} | {('+' if (g or 0) >= 0 else '')+pct(g) if g is not None else '—'} |")
    if ev:
        lines += ["", "## Phase 2 — paraphrase-to-evade (vs DeBERTa)", "",
                  f"- seeds: {ev['n']}; **DeBERTa evasion rate: {pct(ev['evasion_rate'])}**; "
                  f"median iterations-to-evade: {ev['median_iters']}",
                  "- (Recall of QFIRE scope+PHI on the DeBERTa-evading set is the "
                  "`paraphrase_evaded` row above.)"]
    os.makedirs(ROOT, exist_ok=True)
    with open(os.path.join(ROOT, "results.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(ROOT, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print("wrote", os.path.join(ROOT, "results.md"))
    print("ANALYZE_ADAPTIVE_DONE")


if __name__ == "__main__":
    main()
