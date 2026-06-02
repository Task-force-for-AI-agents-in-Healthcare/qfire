# E5 — External Validity — Results

Threshold target FPR = 0.08. Transfer set = corpora/eval_heldout (deepset-decontaminated). Larger benign = synthetic clinical-adjacent.

## Transfer (in-distribution vs held-out)

| detector | corpus | recall | F1 | FPR |
|---|---|---|---|---|
| DeBERTa | in-dist | 0.744 | 0.844 | 0.016 |
| DeBERTa | held-out | 0.839 | 0.905 | 0.017 |
| QFIRE (default) | in-dist | 0.823 | 0.856 | 0.090 |
| QFIRE (default) | held-out | 0.935 | 0.905 | 0.138 |

## Larger-benign over-refusal (calibrated operating point, bench_combined: injection+PHI, deterministic)

- benign n=1294; **FPR (over-refusal) = 0.023** (95% Wilson [0.016, 0.033]); 30 blocked.
- Tightens the paper's calibrated 0.08-FPR operating point on a larger, independent benign corpus (fully offline, no LLM judge).

## Strict-conjunction cross-check (hipaa_phi, 10 LLM-judge rules)

- benign n=1294; FPR = 1.000 — the naive conjunction over-blocks at scale, corroborating the paper's calibration-necessity finding (Sec. 3.7). This is NOT the deployed operating point.

## Threshold transfer (DeBERTa score)

- threshold calibrated for FPR=0.08 on in-dist benign: t=0.000
- realized FPR on **held-out** benign at that fixed t: **0.052**

## Threshold transfer (QFIRE chain score)

- threshold calibrated for FPR=0.08 on in-dist benign: t=0.394
- realized FPR on **held-out** benign at that fixed t: **0.120**
