#!/usr/bin/env python3
"""Build a seeded 300-of-929 attack subset for the cross-model policy-verbosity
ablation, shared by every judge model. Writes the subset JSONL (in sorted-index
order) and the chosen sorted indices (so the existing llama3.2 dumps can be sliced
positionally to the same attacks).

Usage: python3 scripts/make_attack_subset.py --n 300 --seed 42
"""
import argparse
import json
import os
import random

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ATTACKS = os.path.join(BASE, "corpora/eval/attacks/public_attacks.jsonl")
OUT_DIR = os.path.join(BASE, "corpora/policy_length/attacks_subset")


def pick_indices(total, n, seed):
    """Deterministic sorted sample of min(n, total) unique indices from range(total)."""
    if n >= total:
        return list(range(total))
    rng = random.Random(seed)
    return sorted(rng.sample(range(total), n))


def load_attacks():
    with open(ATTACKS) as f:
        return [json.loads(l)["prompt"] for l in f if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    attacks = load_attacks()
    idx = pick_indices(len(attacks), args.n, args.seed)
    os.makedirs(OUT_DIR, exist_ok=True)
    sub_path = os.path.join(OUT_DIR, "attacks_subset.jsonl")
    with open(sub_path, "w") as f:
        for i in idx:
            f.write(json.dumps({"prompt": attacks[i]}) + "\n")
    idx_path = os.path.join(OUT_DIR, "indices.json")
    with open(idx_path, "w") as f:
        json.dump({"total": len(attacks), "n": len(idx), "seed": args.seed,
                   "indices": idx}, f)
    print(f"wrote {len(idx)} attacks -> {sub_path}")
    print(f"wrote indices -> {idx_path}")
    print("SUBSET_DONE")


if __name__ == "__main__":
    main()
