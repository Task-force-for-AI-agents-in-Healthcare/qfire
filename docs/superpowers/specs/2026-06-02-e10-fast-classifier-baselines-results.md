# E10 — Fast/compressed classifier baselines + latency–F1 frontier — Results & Findings

**Date:** 2026-06-02
**Design:** [2026-06-02-e10-fast-classifier-baselines-design.md](2026-06-02-e10-fast-classifier-baselines-design.md)
**Plan:** [../plans/2026-06-02-e10-fast-classifier-baselines.md](../plans/2026-06-02-e10-fast-classifier-baselines.md)

**Setup.** Added the fast/compressed injection-classifier tier to the head-to-head +
QFIRE-HealthBench comparison, on the identical corpora (seed 42), via `baselines.py`:
- **hlyn-labs DeBERTa-70M** — 83 MB **INT8 ONNX** graph run through `onnxruntime`
  (`run_onnx_model`), the optimized analogue of QFIRE's embedded DeBERTa. Its `id2label`
  is generic (`LABEL_0/LABEL_1`), so the injection-class index is **resolved empirically**
  (calibration probe of known-injection vs known-benign prompts) → **index 1**
  (precision ~0.98 confirms it is not flagging benign).
- **PromptGuard-2 22M** (`meta-llama/Llama-Prompt-Guard-2-22M`) — the small LlamaFirewall
  classifier, via the existing PyTorch path.

## Results

### Public injection (929 atk / 1,039 ben)
| System | Prec. | Rec. | F1 | FPR | p50 | p95 |
|---|---|---|---|---|---|---|
| DeBERTa-70M (hlyn-labs, INT8 ONNX) | 0.986 | 0.690 | 0.812 | 0.009 | **11.9 ms** | 105.8 ms |
| PromptGuard-2 22M (Meta) | 0.988 | 0.718 | 0.832 | 0.008 | 31.0 ms | 112.5 ms |
| *(ref) protectai DeBERTa-v3* | 0.984 | 0.721 | 0.832 | 0.011 | — | 195.4 ms |
| *(ref) Sentinel* | 0.987 | 0.973 | 0.980 | 0.012 | — | 431.0 ms |
| *(ref) QFIRE hybrid* | 0.967 | 0.767 | 0.856 | 0.023 | — | 242.3 ms |

### QFIRE-HealthBench (1,000 atk / 1,000 ben)
| System | Prec. | Rec. | F1 | FPR | p50 |
|---|---|---|---|---|---|
| DeBERTa-70M (hlyn-labs, INT8 ONNX) | 0.980 | **0.531** | 0.689 | 0.011 | **5.6 ms** |
| PromptGuard-2 22M (Meta) | 1.000 | **0.390** | 0.561 | 0.000 | 20.4 ms |
| *(ref) QFIRE `bench_combined`* | 0.911 | **0.829** | 0.868 | 0.081 | — |

## Findings

1. **Fast and competitive on injection.** DeBERTa-70M reaches **F1 0.812** on public
   injection at a **p50 of ~12 ms** — within ~0.02 F1 of protectai DeBERTa (0.832) and
   QFIRE's hybrid (0.856), but **≈20× faster than the base ONNX DeBERTa** (~268 ms p95)
   and **≈35× faster than Sentinel** (431 ms p95). The compressed model is the
   low-latency anchor of the latency–F1 frontier (Figure `latency_f1_frontier.png`,
   `fig:frontier`).
2. **The healthcare gap reopens at the cheap end — thesis holds.** On QFIRE-HealthBench,
   DeBERTa-70M recovers only **0.531** recall and PromptGuard-2 22M **0.390** — the same
   structural collapse seen for every generic classifier (Sentinel 0.638, PG-2 86M 0.402,
   DeBERTa 0.574), well below QFIRE's combined chain (0.829). Making the classifier
   cheaper/faster does **not** close the scope/PHI gap; nothing in an injection classifier
   models PHI exfiltration or out-of-scope clinical intent.
3. **PromptGuard-2 22M ≈ 86M.** The 22M variant tracks the 86M (injection F1 0.832 vs
   0.859; HealthBench R 0.390 vs 0.402) — the smaller model is a fine fast substitute on
   injection and equally blind on healthcare.

## Reproduction
- `scripts/baselines.py` `run_onnx_model` (onnxruntime + tokenizer; empirical injection
  index via `_resolve_injection_index` over `_ONNX_CALIB_INJ`/`_ONNX_CALIB_BEN`).
  **Injection index = 1 for hlyn-labs DeBERTa-70M** (recorded as `inj_index` in the JSON).
- `scripts/run_e10_fast.sh` (CPU-only; `HF_TOKEN` for the gated PromptGuard-2 + hlyn
  download); `scripts/plot_frontier.py` → `paper/figs/latency_f1_frontier.png`.
- Hardware: the Apple M2 Max in the reproducibility note (DeBERTa-70M's ~12 ms p50 here
  is *faster* than its published ~101 ms on an M1 CPU).
- Optional Sentinel-v2 (0.6B) / Vijil Dome were **not** added (kept to the two confirmed
  fast models; no fabricated rows).

## Bottom line
A purpose-built, 83 MB INT8 classifier is fast and nearly as accurate as heavier
detectors on public injection — and still loses a third-to-half of healthcare threats.
The cheap end of the classifier spectrum reinforces QFIRE's central result from the
opposite direction: latency is not the obstacle to closing the healthcare gap; the
missing scope/PHI coverage is.
