#!/usr/bin/env python3
"""Slice the existing full llama3.2 policy-length dumps down to the shared
300-attack subset (+ all 50 benign), so llama3.2 is comparable to the run models
without re-running. Dumps are corpus-ordered: attacks[0..A-1] then benign[0..B-1]
(src/bench/mod.rs:141-165).

Usage: python3 scripts/slice_llama32_dumps.py
"""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_ROOT = os.path.join(BASE, "bench-out/policy_length")
DST_ROOT = os.path.join(BASE, "bench-out/policy_length_llama3.2")
IDX_PATH = os.path.join(BASE, "corpora/policy_length/attacks_subset/indices.json")
DOMAINS = ["marketing", "healthcare", "code", "sql"]
RUNGS = ["t0", "t1", "t2", "t3"]


def slice_rows(rows, n_attacks_total, indices):
    """Return chosen attack rows (by index, in given order) + all benign rows.
    Validates that the dump's attack-row count matches n_attacks_total."""
    attacks = [r for r in rows if r["is_attack"]]
    benign = [r for r in rows if not r["is_attack"]]
    if len(attacks) != n_attacks_total:
        raise ValueError(f"expected {n_attacks_total} attack rows, got {len(attacks)}")
    return [attacks[i] for i in indices] + benign


def main():
    meta = json.load(open(IDX_PATH))
    indices, total = meta["indices"], meta["total"]
    for d in DOMAINS:
        out_dir = os.path.join(DST_ROOT, d, "dump")
        os.makedirs(out_dir, exist_ok=True)
        for r in RUNGS:
            src = os.path.join(SRC_ROOT, d, "dump", f"pl_{d}_{r}.jsonl")
            rows = [json.loads(l) for l in open(src) if l.strip()]
            sliced = slice_rows(rows, total, indices)
            dst = os.path.join(out_dir, f"pl_{d}_{r}.jsonl")
            with open(dst, "w") as f:
                for row in sliced:
                    f.write(json.dumps(row) + "\n")
            print(f"{d}/{r}: {len(rows)} -> {len(sliced)} rows")
    print("SLICE_DONE")


if __name__ == "__main__":
    main()
