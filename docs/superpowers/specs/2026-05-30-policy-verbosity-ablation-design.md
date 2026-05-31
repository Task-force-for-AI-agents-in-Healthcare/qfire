# Policy-Verbosity Ablation — Design

**Date:** 2026-05-30
**Status:** Approved (design); pending implementation plan
**Owner:** jim-schwoebel

## Research question

Holding QFIRE's LLM scope-judge scaffold fixed, does a **wordier scope policy**
block more prompt-injection attempts — and at what **over-refusal** cost to
legitimate in-scope requests? Is the effect **monotonic** with policy length, or
does it plateau / reverse?

Motivation: a developer can write a firewall policy as a terse phrase
(`"marketing content only"`) or as a long structured prompt (ROLE / BOUNDARIES /
ADVERSARIAL-DEFENSE / PROTOCOL / REFUSAL). We do not currently know which is more
effective. This experiment measures it.

## Scope of this experiment

In scope:
- A 4-rung policy-length ladder across 4 domains (16 conditions).
- Measuring both attack-block-rate and benign over-refusal on a prompt bank.
- Paired statistical comparison between rungs, per domain and pooled.

Out of scope (explicit follow-ups):
- Folding results into the arXiv paper (separate task, after results land).
- The "standalone system prompt" harness (no QFIRE scaffold) — rejected during
  brainstorming in favour of the clean single-variable ablation.
- Multi-model capability×verbosity interaction (single judge model here:
  `llama3.2`).
- Adjacent/out-of-domain over-refusal stress sets beyond in-domain benign.

## Independent variable: the length ladder

Same policy *intent* per domain, expressed at four verbosity rungs. Token counts
are approximate targets, not hard constraints.

| Rung | Name | Shape | ~tokens |
|------|------|-------|---------|
| T0 | terse | bare phrase, e.g. `"Marketing content only."` | ~4 |
| T1 | sentence | one clause: allowed purpose + "refuse anything else" | ~20 |
| T2 | paragraph | role + explicit ALLOWED / FORBIDDEN topic lists | ~80 |
| T3 | full firewall | structured ROLE / BOUNDARIES / ADVERSARIAL-DEFENSE / PROTOCOL / REFUSAL block | ~300 |

T3 for marketing is the exact prompt the user supplied; T3 for the other domains
is the same structure re-themed. Every rung within a domain targets the identical
allowed/forbidden boundary — only verbosity changes.

## Domains (4)

`marketing`, `healthcare`, `code`, `sql`. Each already has a rule with `in_scope`
exemplars that seed benign generation. → **16 conditions** (4 domains × 4 rungs).

## Harness — single-variable isolation

- Each condition is a **judge-only rule**: `pipeline: [ { type: judge } ]`.
  - **No regex/aho/deberta node.** The lexical denylist would block injection
    attacks regardless of scope wording and mask the entire verbosity effect.
    Dropping it makes the scope text the *only* thing deciding the verdict.
- Each rule is wrapped in a **single-rule chain** so it can be benched in
  isolation via `qfire bench --chain <name>`.
- Only the `scope` string differs across rungs. QFIRE's `src/detector/judge.rs`
  system-prompt template and its `IN SCOPE` / `OUT OF SCOPE` output contract stay
  byte-for-byte fixed. The judge wraps `scope` at `judge.rs:24-29`.
- Files:
  - `rules/bench/policy_length.yaml` — 16 rules, ids `pl_<domain>_t<0..3>`.
  - `chains/bench/policy_length.yaml` — 16 single-rule chains, same ids.

## Prompt bank

Per domain the judge is run over:

1. **Attacks** — the existing 929 prompts in `corpora/eval/attacks`
   (`public_attacks.jsonl`). These are out-of-scope for *every* policy →
   expected verdict BLOCK. Block-rate = TPR / recall.
2. **In-domain benign** — ~50 *legitimate in-scope* requests per domain →
   expected verdict ALLOW. Block-rate here = over-refusal (false positives);
   pass-rate = TNR = 1 − over-refusal.

Rationale for in-domain benign: the generic `corpora/eval/benign` set contains
prompts (e.g. political questions) that a *marketing-only* bot *should* refuse;
counting those as false positives would be invalid. Over-refusal must be measured
against requests that genuinely belong to the policy's domain.

### Benign generation

`scripts/gen_indomain_benign.py`:
- For each domain, read the seed rule's `in_scope` exemplars from the rules YAML.
- Prompt `llama3.2` (local Ollama) to produce ~50 diverse, realistic in-scope
  requests in that domain, seeded by the exemplars.
- Dedup (exact + near-dup) and **decontaminate** against the attack corpus
  (reuse `scripts/decontaminate.py` logic) so no attack text leaks in.
- Seeded/deterministic where the generator allows, for reproducibility.
- Write to `corpora/policy_length/<domain>/benign/<domain>_benign.jsonl` in the
  same `{"prompt": ...}` JSONL format the bench loader expects
  (`src/bench/corpus.rs` / `load_prompts`).

This corpus is a committed, reusable artifact.

## Run plan

- Judge model: `llama3.2` (the paper's default judge; ~2 GB, offline, free).
- Full 929 attacks per condition (no sampling).
- **One `qfire bench` invocation per domain**, passing that domain's 4 rungs as
  four `--chain` flags, with shared `--attacks corpora/eval/attacks` and
  `--benign corpora/policy_length/<domain>/benign`. Output to
  `bench-out/policy_length/<domain>/` (`bench.json`, `bench.csv`, `report.md`).
- Driver: `scripts/run_policy_length.sh` (mirrors `scripts/rebuttal_experiments.sh`
  style), seeded.
- Cost: 16 conditions × (929 attacks + ~50 benign) ≈ ~16k judge calls; a few
  hours on local Ollama, no API keys.

## Metrics & analysis

`scripts/analyze_policy_length.py` consumes the per-domain `bench.json` files and
computes, per condition:

- TPR (attack block-rate / recall), TNR (benign pass-rate), over-refusal (1−TNR).
- F1 and **Youden's J = TPR + TNR − 1** (primary single-number effectiveness).
- Policy token count (tokenized consistently, e.g. whitespace + the judge's
  tokenizer if exposed; otherwise a fixed approximation, documented).

Because every rung sees the *same* prompts, rung-vs-rung comparisons are
**paired**. Compute **paired-bootstrap confidence intervals on ΔJ** (and ΔTPR,
ΔTNR) between adjacent rungs (T0→T1→T2→T3), reusing the paired-stats approach in
`scripts/analyze_paired.py`. Report per domain and pooled across domains.

Outputs:
- A results table: J / TPR / TNR / over-refusal vs token-length, per domain + pooled.
- A length→J figure (and TPR & TNR overlays) per domain + pooled.
- `bench-out/policy_length/results.md` summarizing the finding and the key paired
  contrasts with CIs.

## Success criterion

A defensible, reproducible answer to "are shorter or more-specified policies more
effective at blocking injections" — as a per-domain and pooled length→J curve,
with the over-refusal trade-off explicit and paired CIs on the headline rung
contrasts. The experiment "succeeds" regardless of which direction the effect
goes; success = a trustworthy measurement, not a particular outcome.

## Artifacts produced

- `rules/bench/policy_length.yaml`
- `chains/bench/policy_length.yaml`
- `scripts/gen_indomain_benign.py`
- `corpora/policy_length/<domain>/benign/<domain>_benign.jsonl` (×4)
- `scripts/run_policy_length.sh`
- `scripts/analyze_policy_length.py`
- `bench-out/policy_length/<domain>/{bench.json,bench.csv,report.md}` (×4)
- `bench-out/policy_length/results.md` + figure(s)
