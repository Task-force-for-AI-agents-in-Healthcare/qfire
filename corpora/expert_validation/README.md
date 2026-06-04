# Item C — Clinician & HIM/Privacy-Officer Validation of QFIRE-HealthBench

Turnkey package for the expert-validation study (paper §4 methods + new results subsection).
Everything except the human ratings is built and reproducible. **No expert numbers are
fabricated**: the analysis emits a placeholder table (`XX` cells) until real reviewer forms
are filled, then computes the real numbers.

## Pipeline (deterministic, seed 42)

```bash
python3 scripts/item_c_sample.py    # 1. freeze the seeded 200-prompt stratified sample
python3 scripts/item_c_gold.py      # 2. materialize the 40 expert-authored gold-seed prompts
python3 scripts/item_c_score.py     # 3. score gold + sample through QFIRE (bench_combined)
python3 scripts/item_c_forms.py     # 4. build blinded per-reviewer forms + sealed master key
python3 scripts/item_c_analyze.py   # 5. analyze filled forms -> stats + LaTeX Table 6
python3 scripts/item_c_analyze.py --selftest   # verify the κ/AC1/agreement math (synthetic)
```

## Artifacts

| File | What it is |
|---|---|
| `sample.jsonl` | 200 prompts: 25 plaintext per attack category × 6 + 50 benign. Obfuscated (base64/rot13/…) variants excluded — not human-readable; de-obfuscation is validated separately. |
| `manifest.json` | Seed, per-category counts, source line indices in `dataset.jsonl` — full reproducibility/audit. |
| `gold.jsonl` | 40 expert-authored prompts (24 attack + 16 benign; clinician + HIM/privacy personas), §5. |
| `forms/instructions.md` | The §3 rubric handed to every reviewer, verbatim. |
| `forms/reviewer_R1..R5.csv` | Blinded forms (prompt text only, per-reviewer randomized order). Reviewers fill `Q1_realism` (1–5), `Q2_should_refuse` (Yes/No/Unsure), `Q3_notes`. |
| `forms/master_key.csv` | **SEALED.** display_id → true id, set (gold/sample), benchmark label, category, persona, hidden QFIRE verdict. Do NOT give to reviewers. |
| `../../bench-out/expert_validation/gold_scored.jsonl` | Per-gold-prompt QFIRE verdict + correctness. |
| `../../bench-out/expert_validation/gold_summary.json` | QFIRE gold-seed sanity-check summary. |
| `../../bench-out/expert_validation/sample_verdicts.jsonl` | Hidden QFIRE verdicts on the 200 sample. |
| `../../bench-out/expert_validation/table_expertval.tex` | LaTeX for `tab:expertval` (placeholder until forms filled). |

## To run the actual study

1. Recruit 3 clinicians + 2 HIM/privacy officers (confirm IRB/QI exemption — identifiers are
   synthetic, no real PHI).
2. Send each reviewer their `reviewer_R{n}.csv` + `instructions.md`. Collect filled CSVs back
   into the same paths.
3. `python3 scripts/item_c_analyze.py` → fills `table_expertval.tex`, prints agreement, κ, AC1,
   realism, the disagreement audit, and the equity cross-tab.
4. Adjudicate disagreements; correct/annotate the corpus; paste the filled table into §6 of
   `paper/main.tex`.

## Pre-registered success criteria (§4)

Benchmark "passes" if expert–label agreement ≥ 90% overall, no category < 80%, and ≥ 80% of
prompts rated plausible-or-better (realism ≥ 3). Report whatever the numbers are, including
misses.
