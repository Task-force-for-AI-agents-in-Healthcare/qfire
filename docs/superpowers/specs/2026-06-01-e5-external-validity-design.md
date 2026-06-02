# E5 — External Validity (transfer, larger benign FPR, threshold transfer) — Design (DRAFT)

**Date:** 2026-06-01
**Backlog:** [paper-strengthening E5](2026-06-01-paper-strengthening-experiments-backlog.md)
**Status:** DRAFT — written ahead during the E1 run. Resolve *Open questions* and get
approval before the implementation plan.

## Research question

The paper notes (as a caveat) that cross-dataset numbers drop. E5 turns that into a
measured strength and answers the reviewer's three external-validity questions:
1. **Transfer:** does QFIRE generalize to a *fresh* benchmark not used for any
   calibration or threshold-setting?
2. **Over-refusal at scale:** is the calibrated FPR real on a *larger, realistic*
   benign corpus (vs the small generated benign sets)?
3. **Operating-point transfer:** does a threshold calibrated on corpus A hold its
   target FPR on held-out corpus B?

## What's reused

- `corpora/eval_heldout/{attacks,benign}` already exists (the deepset-decontaminated
  held-out split — protectai DeBERTa never trained on it), a ready transfer set for
  the *classifier* generalization story.
- `qfire bench` metrics (recall/FPR/AUC + Wilson CIs), `scripts/analyze_*` patterns,
  the ROC/threshold tooling behind the existing ROC–AUC figure.

## Components

**(a) Transfer.** Evaluate QFIRE (combined/default) and the classifier baselines on a
**fresh external benchmark** distinct from anything used to pick thresholds. Two
sources: (i) the existing `eval_heldout` split (zero-cost, already decontaminated);
(ii) a NEW public injection/jailbreak dataset pulled at eval time (e.g. a recent HF
set not in the training/calibration mix). Report recall/F1 on the fresh set vs the
in-distribution numbers — the honest drop, and that scope/PHI still helps.

**(b) Larger realistic benign.** The over-refusal claim currently rests on small
generated benign sets. Assemble a **larger, realistic clinical-adjacent benign
corpus** (target ~1–2k) — e.g. real medical-QA / patient-portal-style prompts from a
public dataset — and measure QFIRE's FPR (over-refusal) on it, tightening the CI on
the headline 0.08 FPR claim.

**(c) Threshold transfer.** Calibrate the deberta/score threshold for a target FPR
(e.g. 0.08) on corpus A, then apply that *fixed* threshold to held-out corpus B and
report the realized FPR + a calibration curve. Shows the operating point isn't
overfit to one corpus.

## Method

- New `scripts/fetch_external.py` to pull + normalize the fresh benchmark and the
  larger benign corpus into `corpora/external/…` (decontaminated against training/
  calibration corpora; documented provenance).
- Reuse `qfire bench` across (A,B) corpora; a `scripts/analyze_transfer.py` builds the
  calibrate-on-A / test-on-B table and the threshold-transfer + calibration curves.
- Figure: a transfer table + a calibration/threshold-transfer plot
  (`paper/figs/external_validity.png`).

## Deliverables

- `scripts/fetch_external.py` (+ test for the normalizer/decontaminator),
  `corpora/external/…`.
- `scripts/analyze_transfer.py` (+ test), a calibration/transfer figure.
- Findings doc + paper subsection (Limitations→strength / external validity);
  backlog E5 ticked.

## Success criterion

A transfer table (calibrate-on-A, test-on-B) with the honest generalization gap, a
tighter FPR estimate on a realistic larger benign set, and a threshold-transfer
result showing the calibrated operating point roughly holds — converting the
"cross-dataset numbers drop" caveat into a measured, bounded statement.

## Resolved decisions (user, 2026-06-01)
1. **Transfer set:** **offline** — use the already-local, deepset-decontaminated
   `corpora/eval_heldout` split as the held-out transfer benchmark. No network/keys.
   (Drops the fresh-HF-pull option; transfer story is bounded to that split, stated.)
2. **Larger benign:** **synthetic, generated offline** — ~1–2k realistic
   clinical-adjacent benign prompts via gemma2:9b (like the in-domain benign
   generator), deduped + scope-filtered; model-generated caveat documented.
3. **Network/keys:** none — E5 is fully offline/reproducible.
4. **Threshold metric:** transfer **both** the deberta probability threshold and the
   chain score threshold (report each).

## Caveats
- "Fresh" is only as fresh as our knowledge of each detector's training data; document
  the provenance and any residual contamination risk (as the existing decontaminate.py
  does for deepset).
- A larger benign corpus shifts the FPR denominator; report it with CIs, not as a point
  claim.
