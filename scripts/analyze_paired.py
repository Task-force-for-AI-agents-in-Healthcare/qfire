#!/usr/bin/env python3
"""Paired statistical analysis of two chains' per-prompt predictions (from
`qfire bench --dump`): McNemar's test on correctness, and bootstrap 95% CIs on
F1 and on the F1 difference. Treats attack as the positive class.

Usage: analyze_paired.py <dumpdir> <chainA> <chainB>
  e.g. analyze_paired.py bench-out/dump1 bench_deberta bench_hybrid
"""
import json, math, os, random, sys

random.seed(42)
DUMP = sys.argv[1] if len(sys.argv) > 1 else "/Users/jim/Desktop/qfire/bench-out/dump1"
A = sys.argv[2] if len(sys.argv) > 2 else "bench_deberta"
B = sys.argv[3] if len(sys.argv) > 3 else "bench_hybrid"


def load(name):
    rows = []
    with open(os.path.join(DUMP, name + ".jsonl")) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def f1(rows, idx=None):
    tp = fp = fn = 0
    it = rows if idx is None else (rows[i] for i in idx)
    for r in it:
        atk, blk = r["is_attack"], r["blocked"]
        if blk and atk:
            tp += 1
        elif blk and not atk:
            fp += 1
        elif (not blk) and atk:
            fn += 1
    p = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    return 2 * p * rec / (p + rec) if (p + rec) else 0.0


def pct(xs, q):
    s = sorted(xs)
    i = q * (len(s) - 1)
    lo, hi = int(math.floor(i)), int(math.ceil(i))
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


def main():
    ra, rb = load(A), load(B)
    assert len(ra) == len(rb), f"length mismatch {len(ra)} vs {len(rb)}"
    n = len(ra)
    # McNemar on correctness (correct = blocked iff attack)
    def correct(r):
        return r["blocked"] == r["is_attack"]
    b = sum(1 for x, y in zip(ra, rb) if correct(x) and not correct(y))   # A right, B wrong
    c = sum(1 for x, y in zip(ra, rb) if (not correct(x)) and correct(y)) # B right, A wrong
    if b + c > 0:
        chi2 = (abs(b - c) - 1) ** 2 / (b + c)
        # p-value from chi2 with 1 dof (survival), via erfc approximation
        p_mc = math.erfc(math.sqrt(chi2 / 2.0))
    else:
        chi2, p_mc = 0.0, 1.0

    f1a, f1b = f1(ra), f1(rb)
    # paired bootstrap over prompt indices
    diffs, fa_bs, fb_bs = [], [], []
    for _ in range(2000):
        idx = [random.randrange(n) for _ in range(n)]
        x, y = f1(ra, idx), f1(rb, idx)
        fa_bs.append(x); fb_bs.append(y); diffs.append(y - x)
    print(f"N={n}  A={A}  B={B}")
    print(f"F1[{A}] = {f1a:.3f}  95% CI [{pct(fa_bs,0.025):.3f}, {pct(fa_bs,0.975):.3f}]")
    print(f"F1[{B}] = {f1b:.3f}  95% CI [{pct(fb_bs,0.025):.3f}, {pct(fb_bs,0.975):.3f}]")
    print(f"ΔF1 (B-A) = {f1b-f1a:+.3f}  95% CI [{pct(diffs,0.025):+.3f}, {pct(diffs,0.975):+.3f}]")
    frac_pos = sum(1 for d in diffs if d > 0) / len(diffs)
    print(f"bootstrap P(ΔF1>0) = {frac_pos:.3f}")
    print(f"McNemar: b(A-right,B-wrong)={b}  c(B-right,A-wrong)={c}  chi2={chi2:.2f}  p={p_mc:.2e}")
    print("PAIRED_DONE")


if __name__ == "__main__":
    main()
