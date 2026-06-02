# E8 — Cascade adaptive attack (3-stage) — Results & Findings

**Date:** 2026-06-02
**Design:** [2026-06-02-e8-cascade-adaptive-attack-design.md](2026-06-02-e8-cascade-adaptive-attack-design.md)
**Plan:** [../plans/2026-06-02-e8-cascade-adaptive-attack.md](../plans/2026-06-02-e8-cascade-adaptive-attack.md)

**Setup.** The 3-stage cascade of [firewallsbench2026] applied to QFIRE's **calibrated
deployable** chains (`bench_combined` healthcare / `default` injection, the 0.08-FPR
operating point — *not* the strict `hipaa_phi` E1 used), 60 seed attacks (30 hc / 30 inj),
seed 42:
- **Stage 1 — standard:** verbatim seed attacks.
- **Stage 2 — defense-aware:** qwen3:8B rewrites the attack to fit a plausible scope / drop
  injection markers, **intent-gated** (rewrites that dilute the goal fall back to a
  deterministic verbatim-core wrapper; 21/60 genuine qwen rewrites, 39 wrapped). qwen3:8B
  complies with the red-team rewrite where gpt-oss:20B/gemma2:9B refuse or dilute.
- **Stage 3 — adaptive (QFIRE-in-the-loop):** paraphrase each Stage-2 attack and re-query
  QFIRE's real chain (`qfire check`, fresh process = no cache) up to N=10 times until it
  ALLOWs; gemma2:9B mutator (fast; the chain's own scope judge is also gemma2:9B).

## Results

| domain | Stage 1 | Stage 2 | Stage 3 | Stage-3 evasion (median iters) | scope-judge-only (S2) | PHI-only (S2) |
|---|---|---|---|---|---|---|
| healthcare (`bench_combined`) | 0.80 | 0.83 | **0.37** | 0.63 (2) | **1.00** | 0.40 |
| injection (`default`) | 0.67 | 0.60 | **0.13** | 0.87 (2) | 0.97 | 0.10 |

## Findings

1. **Stage 2 does not help the attacker.** Defense-aware rewrites leave recall flat
   (0.80→0.83 hc, 0.67→0.60 inj) — scope-fitting framing still trips the scope/PHI rules.
2. **Stage 3 is a genuine honest-negative.** A sustained firewall-in-the-loop paraphrase
   loop drops recall to **0.37 / 0.13** at a **median of 2 iterations** — the calibrated
   operating point is materially evadable under adaptive pressure. (Contrast E1, which used
   the strict `hipaa_phi` and single-shot families and held 100%.)
3. **Component decomposition explains it — and points to the fix.** The **scope judge
   alone blocks ≈1.0** of the Stage-2 attacks, far above the calibrated blend (0.83/0.60).
   So it is the *calibration* — lowering the scope judge's weight to hit 0.08 FPR — that is
   evaded, not the scope mechanism. A deployment expecting adaptive adversaries should
   weight the scope judge harder, trading FPR for robustness; the strict `hipaa_phi` chain
   holds where the calibrated one bends. Robustness here is a **tunable FPR trade-off**, not
   a solved property. (PHI-only is weak — 0.40/0.10 — as expected; it only catches
   identifier-bearing attacks.)

## Caveats (important)
- **Black-box paraphrase loop → intent drift.** Some Stage-3 "evasions" are likely the
  paraphrase *weakening* the attack into something QFIRE rightly allows, not a true bypass.
  We did not adjudicate each final paraphrase (final texts were not persisted), so the
  evasion rate is an **upper bound**. (Same caveat as E1's paraphrase loop; a follow-up
  could persist + human-rate the finals to separate true bypass from dilution.)
- **Chain choice dominates the headline.** `bench_combined` (calibrated) vs `hipaa_phi`
  (strict) give very different robustness; we deliberately stress the *deployable* point.
- gemma2:9B mutator/judge; qwen3:8B Stage-2 generator (the one local model that complies
  with the rewrite); seed 42; 60 seeds — a lower bound on a determined human adversary.

## Reproduction
- `scripts/gen_cascade_attacks.py --n 60 --seed 42 --model qwen3:8b` (Stage-2, intent-gated,
  `/no_think`) → `corpora/cascade/stage2_*.jsonl`.
- `scripts/run_cascade.py --budget 10` (env `QFIRE_BIN`, `QFIRE_DEBERTA_DIR`,
  `QFIRE_JUDGE_MODEL=gemma2:9b`, `E8_MUTATOR=gemma2:9b`) → `bench-out/cascade/{summary,verdicts}.json`;
  `scripts/plot_cascade.py` → `paper/figs/cascade.png`. Unit tests:
  `scripts/test_gen_cascade.py`, `scripts/test_adapt_vs_qfire.py`.

## Bottom line
QFIRE's positive-security scope is robust to *defense-aware rewrites* (Stage 2 flat; scope
judge alone ≈1.0), but a *sustained firewall-in-the-loop adaptive attacker* evades the
**calibrated** chain (recall 0.37/0.13, median 2 iters). This is a candid limitation with a
concrete mitigation — weight the scope judge harder for adversarial deployments — and a
measurement caveat (black-box paraphrase may include intent drift, so the evasion rate is
an upper bound). It reframes E1's "100%" as a property of the *strict* chain, not the
deployable one.
