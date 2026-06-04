#!/usr/bin/env python3
"""Per-category recall on HealthBench for each chain, by aligning the bench
--dump (attacks first, in dataset order) with the labeled malicious categories.
Shows which detector catches which healthcare threat class.
"""
import json, os, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUMP = os.path.join(BASE, "bench-out/hb_dump")
DS = os.path.join(BASE, "corpora/healthcare_bench/dataset.jsonl")

CHAINS = ["bench_deberta", "bench_phi", "bench_hybrid", "bench_combined", "bench_combined_trig"]


def main():
    cats, techs = [], []
    for line in open(DS):
        o = json.loads(line)
        if o["label"] == "malicious":
            cats.append(o["category"]); techs.append(o["technique"])
    n = len(cats)
    cat_set = sorted(set(cats))
    print(f"HealthBench malicious N={n}")
    # header
    hdr = "category".ljust(18) + "n".rjust(5) + "".join(c.replace("bench_", "").rjust(12) for c in CHAINS)
    print(hdr)
    # load dumps (attacks are the first n rows)
    blocked = {}
    for c in CHAINS:
        p = os.path.join(DUMP, c + ".jsonl")
        if not os.path.exists(p):
            continue
        rows = [json.loads(l) for l in open(p) if l.strip()][:n]
        blocked[c] = [r["blocked"] for r in rows]
    # per category
    for cat in cat_set:
        idx = [i for i in range(n) if cats[i] == cat]
        row = cat.ljust(18) + str(len(idx)).rjust(5)
        for c in CHAINS:
            if c in blocked:
                rec = sum(1 for i in idx if blocked[c][i]) / max(len(idx), 1)
                row += f"{rec:.2f}".rjust(12)
            else:
                row += "--".rjust(12)
        print(row)
    # overall recall + obfuscated-only recall
    print("-" * len(hdr))
    overall = "OVERALL".ljust(18) + str(n).rjust(5)
    for c in CHAINS:
        overall += (f"{sum(blocked[c])/n:.2f}".rjust(12)) if c in blocked else "--".rjust(12)
    print(overall)
    obf_idx = [i for i in range(n) if techs[i] != "none"]
    line = "obfuscated-only".ljust(18) + str(len(obf_idx)).rjust(5)
    for c in CHAINS:
        line += (f"{sum(1 for i in obf_idx if blocked[c][i])/max(len(obf_idx),1):.2f}".rjust(12)) if c in blocked else "--".rjust(12)
    print(line)
    print("PERCAT_DONE")


if __name__ == "__main__":
    main()
