#!/usr/bin/env python3
"""Generate chains for the throughput/scaling experiment (E2):
- Part A: expression chains over K distinct DETERMINISTIC rules (no judge node),
  K from a ladder capped at the number of deterministic rules available, written
  to chains/bench/scaling/scale_k<K>.yaml (expression "r1 AND r2 AND ... AND rK").
- Part C: two fixed chains for the short-circuit comparison
  (sc_gated = regex THEN deberta with stop_on_first_block via a small rule;
   sc_always = deberta-only), reusing existing rules.

Usage: python3 scripts/gen_scaling_chains.py
"""
import glob
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_GLOB = os.path.join(BASE, "rules", "**", "*.yaml")
OUT_DIR = os.path.join(BASE, "chains", "bench", "scaling")
LADDER = [1, 2, 4, 8, 16, 32, 64, 96]


def deterministic_rule_ids(rules):
    """Rule ids whose pipeline is entirely deterministic (no 'judge' node)."""
    out = []
    for r in rules:
        types = [n.get("type") for n in r.get("pipeline", [])]
        if types and "judge" not in types:
            out.append(r["id"])
    return sorted(out)


def expression_for(ids):
    return " AND ".join(ids)


def k_values(available, ladder=LADDER):
    """Ladder values <= available, plus `available` itself if the ladder steps
    past it (so the largest chain uses every rule we have)."""
    vals = [k for k in ladder if k < available]
    vals.append(min(available, ladder[-1]) if available >= ladder[-1] else available)
    # dedupe preserve order
    seen, out = set(), []
    for v in vals:
        if v not in seen and v > 0:
            seen.add(v); out.append(v)
    return out


def load_rules():
    import yaml
    rules = []
    for path in glob.glob(RULES_GLOB, recursive=True):
        doc = yaml.safe_load(open(path))
        if isinstance(doc, list):
            rules.extend(x for x in doc if isinstance(x, dict) and "id" in x)
    return rules


def write_chain(cid, expression, normalize=False):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{cid}.yaml")
    lines = [f"id: {cid}", "mode: expression", "fail_policy: fail_closed"]
    lines.append(f'expression: "{expression}"')
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


def main():
    rules = load_rules()
    det = deterministic_rule_ids(rules)
    print(f"deterministic rules available: {len(det)}")
    ks = k_values(len(det))
    for k in ks:
        write_chain(f"scale_k{k}", expression_for(det[:k]))
    print(f"Part A: wrote scaling chains for K={ks}")
    # Part C: short-circuit is a WITHIN-RULE pipeline property, so each chain wraps
    # one rule (defined in rules/bench/shortcircuit.yaml, authored in Task 4 Step 4):
    #   sc_gated  -> sc_gated_rule  : pipeline [regex, deberta] stop_on_first_block
    #                (deberta runs only when the regex abstains)
    #   sc_always -> sc_always_rule : pipeline [deberta]  (expensive node always runs)
    write_chain("sc_gated", "sc_gated_rule")
    write_chain("sc_always", "sc_always_rule")
    print("Part C: wrote sc_gated, sc_always")
    print("GEN_CHAINS_DONE")


if __name__ == "__main__":
    main()
