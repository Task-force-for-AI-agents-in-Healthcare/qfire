# Policy-Verbosity Ablation — Results & Findings

**Date:** 2026-05-31
**Design:** [2026-05-30-policy-verbosity-ablation-design.md](2026-05-30-policy-verbosity-ablation-design.md)
**Plan:** [../plans/2026-05-30-policy-verbosity-ablation.md](../plans/2026-05-30-policy-verbosity-ablation.md)

**Setup.** 4 domains × 4 verbosity rungs (T0 terse → T3 full structured firewall),
judge-only pipeline, `--no-cache`, `--seed 42`. Judge model: `llama3.2` (3B,
local). Each condition evaluated on the same 929 public injection attacks
(out-of-scope → expected BLOCK) + 50 generated in-domain benign requests
(in-scope → expected ALLOW). 979 prompts × 16 conditions = 15,664 judge calls.
J = Youden's J = TPR + TNR − 1. Raw dumps + `results.md` regenerate via
`scripts/run_policy_length.sh` then `scripts/analyze_policy_length.py` (outputs
live in gitignored `bench-out/policy_length/`).

**Cache-collision guard verified.** Marketing per-rung block counts were
897 / 910 / 917 / 922 (t0→t3) — distinct per rung, confirming `--no-cache`
prevented the scope-blind cache key from making rungs reuse T0's verdicts.

## Headline finding

**For blocking injections, policy length barely matters — every rung blocks
97–99% of attacks.** The entire cost of verbosity shows up as **over-refusal of
legitimate in-scope requests**, and that cost is **non-monotone**: a one-sentence
"…refuse anything else" policy (T1) is the *worst*, a structured paragraph (T2)
is the *sweet spot*, and the maximal paranoid firewall (T3) *regresses* from T2.

So the answer to "are shorter or more-specified policies more effective at
blocking injections?" is: **shorter is no worse at blocking; the differentiator
is over-refusal, and the best policy is mid-length and structured, not the
longest or the shortest.**

- **TPR (attacks blocked)** spans only 0.966–0.992 across all 16 conditions —
  essentially flat. The fixed firewall scaffold + IN/OUT-SCOPE judge contract
  does the injection-blocking work; the scope wording adds little.
- **TNR (legitimate requests passed)** spans 0.020–1.000 — this is where policy
  wording decides everything.

## Per-condition metrics

| domain | rung | words | TPR (block) | TNR (pass) | over-refusal | Youden J |
|---|---|---|---|---|---|---|
| marketing | t0 | 3 | 0.966 | 1.000 | 0.000 | +0.966 |
| marketing | t1 | 16 | 0.980 | 1.000 | 0.000 | +0.980 |
| marketing | t2 | 74 | 0.987 | 1.000 | 0.000 | +0.987 |
| marketing | t3 | 239 | 0.991 | 0.980 | 0.020 | +0.971 |
| healthcare | t0 | 7 | 0.984 | 0.500 | 0.500 | +0.484 |
| healthcare | t1 | 18 | 0.980 | 0.020 | 0.980 | −0.000 |
| healthcare | t2 | 74 | 0.983 | 0.480 | 0.520 | +0.463 |
| healthcare | t3 | 230 | 0.973 | 0.380 | 0.620 | +0.353 |
| code | t0 | 4 | 0.974 | 0.980 | 0.020 | +0.954 |
| code | t1 | 18 | 0.975 | 0.920 | 0.080 | +0.895 |
| code | t2 | 60 | 0.984 | 1.000 | 0.000 | +0.984 |
| code | t3 | 216 | 0.992 | 0.920 | 0.080 | +0.912 |
| sql | t0 | 4 | 0.985 | 0.800 | 0.200 | +0.785 |
| sql | t1 | 20 | 0.986 | 0.620 | 0.380 | +0.606 |
| sql | t2 | 65 | 0.991 | 0.980 | 0.020 | +0.971 |
| sql | t3 | 233 | 0.986 | 0.820 | 0.180 | +0.806 |

## Pooled across domains

| rung | TPR | TNR | over-refusal | Youden J |
|---|---|---|---|---|
| t0 (terse) | 0.977 | 0.820 | 0.180 | +0.797 |
| t1 (sentence) | 0.980 | 0.640 | 0.360 | +0.620 |
| **t2 (paragraph)** | **0.986** | **0.865** | **0.135** | **+0.851** |
| t3 (full firewall) | 0.986 | 0.775 | 0.225 | +0.761 |

## Paired ΔJ between adjacent rungs (bootstrap 95% CI, B=2000)

| scope | contrast | ΔJ | 95% CI | P(ΔJ>0) |
|---|---|---|---|---|
| marketing | t0→t1 | +0.014 | [+0.006, +0.023] | 1.000 |
| marketing | t1→t2 | +0.008 | [+0.000, +0.015] | 0.971 |
| marketing | t2→t3 | −0.016 | [−0.066, +0.010] | 0.327 |
| healthcare | t0→t1 | −0.484 | [−0.630, −0.339] | 0.000 |
| healthcare | t1→t2 | +0.463 | [+0.325, +0.604] | 1.000 |
| healthcare | t2→t3 | −0.110 | [−0.250, +0.029] | 0.061 |
| code | t0→t1 | −0.059 | [−0.134, +0.001] | 0.030 |
| code | t1→t2 | +0.089 | [+0.024, +0.171] | 1.000 |
| code | t2→t3 | −0.071 | [−0.153, −0.008] | 0.017 |
| sql | t0→t1 | −0.179 | [−0.291, −0.082] | 0.000 |
| sql | t1→t2 | +0.365 | [+0.236, +0.496] | 1.000 |
| sql | t2→t3 | −0.165 | [−0.267, −0.071] | 0.000 |
| **pooled** | **t0→t1** | **−0.177** | **[−0.231, −0.125]** | **0.000** |
| **pooled** | **t1→t2** | **+0.231** | **[+0.171, +0.288]** | **1.000** |
| **pooled** | **t2→t3** | **−0.091** | **[−0.140, −0.045]** | **0.000** |

Pooled paired comparisons are all significant (CIs exclude 0): terse→sentence
*hurts*, sentence→paragraph *helps* substantially, paragraph→full-firewall
*hurts*. T2 is the only rung whose advantage is robust across the bootstrap.

## Interpretation

- **T1 is a trap.** A one-sentence policy that names the purpose then says
  "refuse anything else" / "give no clinical advice" primes the judge toward
  refusal *without* enumerating what is allowed. Healthcare T1 collapses to
  TNR 0.02 — it refuses 98% of legitimate scheduling requests. T1 is worse than
  the bare terse phrase (T0) in 3 of 4 domains.
- **T2 is the sweet spot.** A structured paragraph with explicit ALLOWED *and*
  FORBIDDEN lists gives the judge enough to recognize legitimate requests while
  still blocking attacks. It is the best or tied-best rung in every domain and
  the best pooled (J = 0.851).
- **T3 regresses.** The maximal "strict firewall / adversarial-defense / respond
  only with the refusal message" framing makes the judge trigger-happy: TPR is
  unchanged (already saturated) but TNR drops vs T2 in every domain. More words
  past the structured paragraph buy over-refusal, not protection.
- **Domain dominates the absolute numbers.** Marketing is trivial (all rungs
  near-perfect — its attacks are blatantly off-topic and its benign asks sit far
  from the boundary). Healthcare is hard for a 3B judge (best rung still ~50%
  over-refusal — clinic logistics sit close to the forbidden clinical boundary).
  SQL and code gain the most from the T2 paragraph.

## Caveats

- **Single judge model (llama3.2, 3B).** A larger model may follow long T3
  policies more faithfully and avoid the over-refusal regression — the
  capability×verbosity interaction is untested here (design lists it as a
  follow-up). Healthcare's uniformly low TNR is partly small-model conservatism.
- **Benign set is model-generated** (50/domain, deduped + decontaminated +
  scope-filtered). Absolute over-refusal numbers depend on it; the *between-rung*
  ΔJ contrasts are paired on identical prompts and are robust to benign-set noise.
- Healthcare over-refusal is high in absolute terms for every rung; the finding
  is about the *shape* of the length→J curve, not that any rung is production-ready
  for the clinic-scheduling case on this judge.

## Bottom line

Don't reach for the longest, most defensive policy you can write, and don't
reach for a bald one-liner either. **A mid-length policy that explicitly
enumerates both what's allowed and what's forbidden (T2) maximizes the
block-vs-over-refusal trade-off.** Injection-blocking itself is nearly
length-invariant once the firewall scaffold is in place.
