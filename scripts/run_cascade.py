#!/usr/bin/env python3
"""E8 orchestrator: run the 3-stage cascade over the Stage-2 corpus and write a staged
recall summary + Stage-3 evasion stats, per domain, full chain + per-component.

Stage 1 = score verbatim cores; Stage 2 = score defense-aware rewrites; Stage 3 = QFIRE-
in-the-loop paraphrase evasion (N=10, gemma2:9B mutator — fast; the chain's own scope judge
is gemma2:9B via QFIRE_JUDGE_MODEL). Per-component = judge_scope (scope-only) + bench_phi.

Env: QFIRE_BIN, QFIRE_DEBERTA_DIR, QFIRE_JUDGE_MODEL=gemma2:9b.
"""
import argparse
import glob
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
import adapt_vs_qfire as aq

FULL = {"healthcare": "bench_combined", "injection": "default"}
MUTATOR = os.environ.get("E8_MUTATOR", "gemma2:9b")


def recall(prompts, chain):
    """block-rate over an all-attack set via qfire check."""
    if not prompts:
        return None
    blocked = sum(1 for p in prompts if aq.is_blocked(p, chain))
    return blocked / len(prompts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", default=os.path.join(BASE, "corpora/cascade"))
    ap.add_argument("--out", default=os.path.join(BASE, "bench-out/cascade"))
    ap.add_argument("--budget", type=int, default=10)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    summary, verdicts = {}, []
    for fp in sorted(glob.glob(os.path.join(args.indir, "stage2_*.jsonl"))):
        rows = [json.loads(l) for l in open(fp) if l.strip()]
        if not rows:
            continue
        domain = rows[0]["domain"]
        chain = FULL[domain]
        cores = [r["core"] for r in rows]
        s2 = [r["prompt"] for r in rows]
        print(f"== {domain} (chain={chain}, n={len(rows)}) ==", flush=True)

        r1 = recall(cores, chain)
        print(f"  stage1 (standard) recall={r1}", flush=True)
        r2 = recall(s2, chain)
        print(f"  stage2 (defense-aware) recall={r2}", flush=True)

        # Stage 3: QFIRE-in-the-loop paraphrase evasion on the Stage-2 attacks.
        loops = []
        for j, atk in enumerate(s2):
            res = aq.evade_loop(
                atk,
                blocker=lambda t, c=chain: aq.is_blocked(t, c),
                mutate=lambda t, i: aq.paraphrase(t, i, MUTATOR),
                budget=args.budget)
            loops.append(res)
            verdicts.append({"domain": domain, **{k: res[k] for k in ("evaded", "iters")}})
            if (j + 1) % 10 == 0:
                print(f"    stage3 {j+1}/{len(s2)} evaded={sum(x['evaded'] for x in loops)}",
                      flush=True)
        evasion_rate = sum(x["evaded"] for x in loops) / len(loops)
        r3 = 1.0 - evasion_rate
        med = aq.median_iters([x for x in loops if x["evaded"]])
        print(f"  stage3 (adaptive) recall={r3:.3f} evasion_rate={evasion_rate:.3f} "
              f"median_iters_to_evade={med}", flush=True)

        scope_only = recall(s2, "judge_scope")
        phi_only = recall(s2, "bench_phi")
        summary[domain] = {"n": len(rows), "chain": chain,
                           "recall_stage1": round(r1, 4) if r1 is not None else None,
                           "recall_stage2": round(r2, 4) if r2 is not None else None,
                           "recall_stage3": round(r3, 4),
                           "stage3_evasion_rate": round(evasion_rate, 4),
                           "stage3_median_iters_to_evade": med,
                           "scope_judge_only_stage2": round(scope_only, 4) if scope_only is not None else None,
                           "phi_only_stage2": round(phi_only, 4) if phi_only is not None else None}

    json.dump(verdicts, open(os.path.join(args.out, "verdicts.json"), "w"), indent=1)
    json.dump(summary, open(os.path.join(args.out, "summary.json"), "w"), indent=1)
    print(json.dumps(summary, indent=1))
    print("RUN_CASCADE_DONE")


if __name__ == "__main__":
    main()
