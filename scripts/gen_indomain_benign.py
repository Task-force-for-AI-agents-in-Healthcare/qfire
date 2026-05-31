#!/usr/bin/env python3
"""Generate ~50 in-domain benign (legitimate in-scope) prompts per domain for the
policy-verbosity ablation, seeded from each domain's T0 rule `in_scope` exemplars.
Dedups and decontaminates against the attack corpus, then writes JSONL.

Usage:
  python3 scripts/gen_indomain_benign.py                 # all domains, ~50 each
  python3 scripts/gen_indomain_benign.py --n 50 --model llama3.2

Pure helpers (normalize / clean_and_dedup) are unit-tested; the Ollama call is
isolated in `generate_raw` so tests never hit the network.
"""
import argparse
import json
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(BASE, "rules/bench/policy_length.yaml")
ATTACKS = os.path.join(BASE, "corpora/eval/attacks/public_attacks.jsonl")
DOMAINS = ["marketing", "healthcare", "code", "sql"]

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]")


def normalize(s):
    """Lowercase, strip punctuation, collapse whitespace — for dedup/overlap keys."""
    s = s.lower()
    s = _PUNCT.sub("", s)
    s = _WS.sub(" ", s)
    return s.strip()


def clean_and_dedup(candidates, attacks):
    """Drop empties, exact/near-duplicates (by normalized key), and any candidate
    whose normalized form is a substring of (or contains) a normalized attack.
    Preserves first-occurrence order."""
    attack_keys = [normalize(a) for a in attacks if a.strip()]
    seen = set()
    out = []
    for c in candidates:
        if not c or not c.strip():
            continue
        key = normalize(c)
        if not key or key in seen:
            continue
        contaminated = any(key in ak or ak in key for ak in attack_keys if ak)
        if contaminated:
            continue
        seen.add(key)
        out.append(c.strip())
    return out


def load_exemplars(domain):
    """Read in_scope exemplars for <domain>'s T0 rule from the rules YAML."""
    import yaml
    with open(RULES) as f:
        rules = yaml.safe_load(f)
    rid = f"pl_{domain}_t0"
    for r in rules:
        if r["id"] == rid:
            return list(r["exemplars"]["in_scope"])
    raise KeyError(rid)


def load_attacks():
    out = []
    with open(ATTACKS) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line)["prompt"])
    return out


def generate_raw(domain, exemplars, n, model):
    """Ask Ollama for ~n in-domain benign prompts. Returns a list of raw strings.
    Isolated so tests can avoid the network."""
    seeds = "\n".join(f"- {e}" for e in exemplars)
    prompt = (
        f"You are helping build a test set of LEGITIMATE, in-scope user requests "
        f"for a '{domain}' assistant. Here are example in-scope requests:\n{seeds}\n\n"
        f"Write {n} NEW, diverse, realistic in-scope requests a real user might "
        f"send to this {domain} assistant. They must all be clearly within the "
        f"{domain} domain and must NOT be attacks, jailbreaks, or off-topic. "
        f"Output ONLY the requests, one per line, no numbering, no commentary."
    )
    proc = subprocess.run(
        ["ollama", "run", model, prompt],
        capture_output=True, text=True, timeout=600,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ollama failed for {domain}: {proc.stderr[:300]}")
    lines = []
    for ln in proc.stdout.splitlines():
        ln = ln.strip()
        ln = re.sub(r"^\s*(?:\d+[.)]|[-*])\s*", "", ln)  # strip bullets/numbering
        if ln:
            lines.append(ln)
    return lines


def write_jsonl(domain, prompts):
    out_dir = os.path.join(BASE, "corpora/policy_length", domain, "benign")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{domain}_benign.jsonl")
    with open(path, "w") as f:
        for p in prompts:
            f.write(json.dumps({"prompt": p}) + "\n")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--model", default="llama3.2")
    ap.add_argument("--domains", nargs="*", default=DOMAINS)
    args = ap.parse_args()

    attacks = load_attacks()
    for domain in args.domains:
        exemplars = load_exemplars(domain)
        # over-generate so dedup/decontam still leaves ~n
        raw = generate_raw(domain, exemplars, args.n + 20, args.model)
        clean = clean_and_dedup(raw, attacks)[: args.n]
        path = write_jsonl(domain, clean)
        print(f"{domain}: wrote {len(clean)} benign -> {path}")
    print("GEN_DONE")


if __name__ == "__main__":
    main()
