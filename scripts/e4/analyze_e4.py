#!/usr/bin/env python3
"""E4 analysis: harmful-action rate (attack episodes) and benign-completion rate, each
split by guard on/off, with Wilson 95% CIs and deltas. Reads bench-out/e4/runs.jsonl ->
results.md + summary.json."""
import json, math, os
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(BASE, "bench-out/e4")


def rate(rows, key):
    return sum(1 for r in rows if r[key]) / len(rows) if rows else 0.0


def wilson(succ, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = succ / n; d = 1 + z*z/n; c = p + z*z/(2*n)
    m = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return (max(0.0, (c - m)/d), min(1.0, (c + m)/d))


def _block(rows, key):
    n = len(rows); s = sum(1 for r in rows if r[key]); r = rate(rows, key)
    lo, hi = wilson(s, n)
    return n, s, r, lo, hi


def main():
    rows = [json.loads(l) for l in open(os.path.join(OUT, "runs.jsonl"))]
    atk = [r for r in rows if r["kind"] == "attack"]
    ben = [r for r in rows if r["kind"] == "benign"]
    a_off, a_on = [r for r in atk if not r["guard"]], [r for r in atk if r["guard"]]
    b_off, b_on = [r for r in ben if not r["guard"]], [r for r in ben if r["guard"]]
    L = ["# E4 — End-to-End Agent Harm Reduction — Results", "",
         f"Agent llama3.1:8b (temp 0, seed 42), guard chain bench_combined. "
         f"{len(atk)//2} attack + {len(ben)//2} benign episodes x guard on/off.", ""]

    no, ns, hr_off, lo0, hi0 = _block(a_off, "harm")
    _,  _,  hr_on,  lo1, hi1 = _block(a_on, "harm")
    L += ["## Harmful-action rate (attack episodes)", "",
          "| guard | n | harmful | rate | 95% Wilson |", "|---|---|---|---|---|",
          f"| OFF | {no} | {ns} | {hr_off:.3f} | [{lo0:.3f}, {hi0:.3f}] |",
          f"| ON | {len(a_on)} | {sum(r['harm'] for r in a_on)} | {hr_on:.3f} | [{lo1:.3f}, {hi1:.3f}] |",
          "", f"**Harm reduction: {hr_off:.3f} -> {hr_on:.3f} (delta -{hr_off-hr_on:.3f}).**"]
    for vec in ("direct", "indirect"):
        vo = [r for r in a_off if r.get("vector") == vec]
        vn = [r for r in a_on if r.get("vector") == vec]
        L.append(f"- {vec}: OFF {rate(vo,'harm'):.3f} -> ON {rate(vn,'harm'):.3f} "
                 f"(n={len(vo)} each)")

    bo, bs, bc_off, blo0, bhi0 = _block(b_off, "benign_complete")
    _,  _,  bc_on,  blo1, bhi1 = _block(b_on, "benign_complete")
    L += ["", "## Benign task-completion rate", "",
          "| guard | n | completed | rate | 95% Wilson |", "|---|---|---|---|---|",
          f"| OFF | {bo} | {bs} | {bc_off:.3f} | [{blo0:.3f}, {bhi0:.3f}] |",
          f"| ON | {len(b_on)} | {sum(r['benign_complete'] for r in b_on)} | {bc_on:.3f} | [{blo1:.3f}, {bhi1:.3f}] |",
          "", f"**Utility cost: {bc_off:.3f} -> {bc_on:.3f} (delta -{bc_off-bc_on:.3f}).**"]

    with open(os.path.join(OUT, "results.md"), "w") as f:
        f.write("\n".join(L) + "\n")
    json.dump({"harm_off": hr_off, "harm_on": hr_on, "harm_ci_off": [lo0, hi0],
               "harm_ci_on": [lo1, hi1], "benign_off": bc_off, "benign_on": bc_on,
               "benign_ci_off": [blo0, bhi0], "benign_ci_on": [blo1, bhi1],
               "n_attack": len(a_off), "n_benign": len(b_off),
               "harm_off_direct": rate([r for r in a_off if r.get('vector')=='direct'], 'harm'),
               "harm_on_direct": rate([r for r in a_on if r.get('vector')=='direct'], 'harm'),
               "harm_off_indirect": rate([r for r in a_off if r.get('vector')=='indirect'], 'harm'),
               "harm_on_indirect": rate([r for r in a_on if r.get('vector')=='indirect'], 'harm')},
              open(os.path.join(OUT, "summary.json"), "w"))
    print("wrote", os.path.join(OUT, "results.md")); print("ANALYZE_E4_DONE")


if __name__ == "__main__":
    main()
