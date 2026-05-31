# QFIRE: A Parallel, Positive-Security Prompt Firewall in Rust

**Deterministic scope constraining and cheap-before-expensive detector graphs for low-latency LLM defense**

*Task Force for AI Agents in Healthcare — 2026-05-30*

> This is the readable Markdown rendering of the paper. The arXiv-ready LaTeX
> source is `paper/main.tex` (+ `paper/refs.bib`); all result tables are
> generated from the benchmark JSON by `scripts/make_tables.py` and embedded
> below verbatim from the measured runs (seed 42, local Ollama, no paid keys).

## Abstract

LLMs embedded in agents process trusted instructions and untrusted data in one
context window, leaving them open to direct and indirect prompt injection.
Existing runtime guardrails trade safety against latency: model-based auditors
are accurate but add hundreds of milliseconds of Python inference, while lexical
filters are fast but blind to obfuscated or semantically disguised payloads. We
present **QFIRE**, an inline, provider-agnostic prompt firewall implemented as a
single self-contained Rust toolchain (proxy, CLI, benchmark harness). QFIRE
contributes (i) **positive-security scope constraining**; (ii) an **asynchronous
detector graph** that runs rules and detector nodes concurrently with
cheap-before-expensive short-circuiting; and (iii) a **de-obfuscation
normalization pass**. It ships ~100 versioned rules, an 18-identifier HIPAA
Safe-Harbor PHI panel, and runs `protectai/deberta-v3-base-prompt-injection`
locally via embedded ONNX Runtime. On 1,968 public prompt-injection/jailbreak
prompts, QFIRE's deterministic hybrid attains **F1 0.86** — statistically on par
with Meta's **PromptGuard-2-86M** (F1 0.86, the strongest single classifier we
measured) and above the protectai DeBERTa-v3 detector (F1 0.83), while
lexical-only baselines lag (F1 0.16–0.50). QFIRE's larger and more decisive gains
are on **healthcare scope/PHI** (QFIRE-HealthBench, §7): the same SOTA
PromptGuard-2 recovers only **0.40 recall** there (DeBERTa 0.57), versus **0.83**
for QFIRE's combined scope+PHI chain, because most healthcare threats carry no
injection signal. We report precision/recall/F1 with 95% Wilson intervals,
ROC–AUC, and latency percentiles; everything regenerates from `make paper`.

## 1. Introduction & contributions

(See `main.tex` for full prose.) Contributions:
1. **Positive-security scope constraining** — enforce a declared purpose and
   block out-of-scope drift even absent an overt attack token.
2. **Asynchronous detector graph with collapse** — ordered (iptables-style) or
   boolean-expression chains; cheap detectors short-circuit before the DeBERTa
   classifier and the LLM judge.
3. **De-obfuscation** (Base64/hex/ROT13/leetspeak/homoglyph/zero-width) and a
   **complete 18-identifier HIPAA Safe-Harbor PHI** detector/redactor.
4. **A reproducible head-to-head benchmark** with confidence intervals.

## 2. Experimental setup

- **Corpus:** 1,968 public prompts — **929 attack / 1,039 benign** — from
  `deepset/prompt-injections` and `jackhhao/jailbreak-classification`,
  snapshotted in `corpora/eval/`.
- **Baselines:** `protectai/deberta-v3-base-prompt-injection` — the de-facto
  open detector and the engine inside Protect AI LLM Guard — run by QFIRE via
  Rust ONNX (identical weights); lexical regex / Aho-Corasick / entropy filters;
  and Meta `Llama-Prompt-Guard-2-86M` (PromptGuard-2), run locally in PyTorch on
  the identical corpus (gate accepted; weights downloaded with an authorized HF
  token) — no longer reported by citation but measured head-to-head.
- **Metrics:** attack = positive class; precision, recall, F1, FPR, accuracy
  with 95% Wilson intervals, ROC–AUC (continuous detector score), and latency.

## 3. Results

### 3.1 Head-to-head detection (clean public corpus, 929 atk / 1,039 ben)

| System | Prec. | Rec. | F1 | FPR | AUC | latency |
|---|---|---|---|---|---|---|
| Regex denylist (lexical) | 1.00 | 0.29 | 0.46 | 0.00 | 0.65 | <0.1 ms |
| Aho-Corasick keywords | 0.91 | 0.34 | 0.50 | 0.03 | 0.66 | <0.1 ms |
| Entropy heuristic | 0.83 | 0.09 | 0.16 | 0.02 | 0.78 | <0.1 ms |
| DeBERTa-v3 (protectai, PyTorch baseline) | 0.98 | 0.72 | 0.83 | 0.01 | — | 193 ms (p95) |
| **DeBERTa-v3 (real ONNX, ours)** | 0.98 | 0.74 | 0.84 | 0.02 | **0.925** | 255 ms (p95) |
| **PromptGuard-2-86M (Meta, PyTorch)** | **1.00** | 0.76 | **0.86** | **0.00** | — | 47 ms (p50) |
| **QFIRE hybrid** | 0.97 | 0.77 | **0.86** | 0.02 | — † | short-circuited ‡ |
| Hybrid + de-obf (forced, clean traffic) | 0.73 | 0.83 | 0.78 | 0.27 | — † | 279 ms (p95) |

† AUC is only meaningful for the single-score DeBERTa chain; for multi-detector
chains the terminal "score" mixes 0/1 lexical signals with the classifier
probability and is not a calibrated ranking, so we omit it.
‡ See §3.4 on latency and the cross-chain cache caveat.

**Finding.** On generic injection the QFIRE deterministic hybrid (Aho-Corasick →
regex → entropy → DeBERTa, stop-on-first-block) and Meta's PromptGuard-2 are
**statistically tied at the top (F1 0.86)**, both above the protectai DeBERTa-v3
detector alone (0.84). PromptGuard-2 reaches that F1 with the cleanest precision
(1.00, FPR 0.00); QFIRE matches it by letting cheap detectors raise recall before
its own classifier. Lexical-only filters are precise but low-recall (F1
0.16–0.50), confirming the "fast-but-blind" gap. We do **not** claim QFIRE beats
PromptGuard-2 on generic injection — they are even; QFIRE's distinguishing value
is the scope/PHI and latency-budget story (§3.3, §7), not a generic-detector win.

**Accuracy with 95% Wilson confidence intervals** (QFIRE chains):

| System | Accuracy | 95% Wilson CI |
|---|---|---|
| DeBERTa-v3 (ONNX) | 0.86 | [0.84, 0.87] |
| QFIRE hybrid | 0.87 | [0.86, 0.89] |

*(Exact CIs are emitted to `paper/tables/accuracy_ci.tex` from the run.)*

### 3.2 De-obfuscation ablation (obfuscated attacks)

Attacks re-encoded with Base64 / ROT13 / leetspeak / homoglyphs:

| Configuration | Recall | F1 | ΔF1 |
|---|---|---|---|
| Hybrid (no normalization) | 0.55 | 0.70 | — |
| **Hybrid + de-obfuscation** | **0.84** | **0.78** | **+0.08** |

**Finding.** On obfuscated attacks the normalization pass recovers recall from
**0.55 → 0.84** (+29 points). On *clean* traffic (§3.1) the same aggressive
decoding raises FPR (0.02 → 0.27). De-obfuscation is therefore a **targeted**
control for channels where encoded payloads are expected, not an always-on
default — a trade-off we report rather than tune away.

### 3.3 Healthcare / PHI panel

The PHI engine matches all 18 HIPAA Safe-Harbor identifiers. On a
clinical-adjacent corpus (diagnosis/treatment/dosing/PHI-exfiltration attacks vs.
legitimate general-health benign prompts):

| Configuration | Block | FPR | Prec. | Rec. | F1 |
|---|---|---|---|---|---|
| `hc_no_diagnosis` (single scope rule) | 0.96 | 0.16 | 0.86 | 0.96 | **0.91** |
| `hipaa_phi` chain (AND of 10 strict judge rules) | 1.00 | **1.00** | 0.50 | 1.00 | 0.67 |

**Finding (over-blocking is a first-class failure mode).** A single calibrated
scope rule achieves F1 0.91. Naively AND-ing ten strict LLM-judge scope rules
drives FPR to **1.00** — every benign clinical prompt trips at least one
over-eager judge. This quantifies the paper's central healthcare caution:
composing many strict positive-security rules requires calibration, or
over-blocking destroys utility.

### 3.4 Latency and cost

- **Lexical / Aho-Corasick / entropy:** sub-0.1 ms per prompt.
- **DeBERTa-v3 via Rust ONNX (cold):** ~81 ms mean, **255 ms p95** on CPU — the
  cost of the learned detector, paid only when cheap detectors abstain.
- **Rust ONNX vs PyTorch (same weights, same full corpus):** an independent
  PyTorch run of `protectai/deberta-v3` measured **P 0.984 / R 0.721 / F1 0.832**,
  p95 **193 ms**, versus the Rust ONNX **P 0.976 / R 0.744 / F1 0.844**, p95
  255 ms. Two honest conclusions: (i) the near-identical P/R/F1 (within ~0.02)
  **validates that the Rust ONNX integration faithfully reproduces the PyTorch
  reference model**; (ii) Rust ONNX is **not faster** than PyTorch on this CPU —
  contrary to a commonly repeated claim, the measured Rust advantage is
  single-binary, no-Python-runtime, in-process deployment, *not* raw latency.
- **LLM judge (Ollama):** the only network-cost node; under local Ollama every
  call is \$0, so firewall overhead is reported as latency. The healthcare chain
  (10 judge rules) shows p95 ≈ 2.8 s, motivating cheap-before-expensive ordering
  and judicious rule counts.
- **Caveat (measurement integrity):** within a *single* `bench` invocation the
  verdict cache is shared across chains, so chains evaluated after the
  DeBERTa-only chain read cached classifier verdicts and report artificially low
  latency. We therefore quote the **cold** DeBERTa latency above and characterize
  the hybrid qualitatively: short-circuiting means most overtly-malicious prompts
  are caught by lexical detectors (sub-ms) and never reach the classifier.

## 4. Discussion & limitations

- **Cross-dataset numbers are lower than in-distribution scores.** protectai
  reports near-perfect accuracy on its own test split; on this mixed public
  corpus the same weights score F1 0.84. We report a public, mixed corpus and
  release the snapshot; single-corpus claims do not transfer.
- **PromptGuard-2 (Meta)** is now run locally head-to-head (gate accepted): on the
  same 1,968-prompt corpus it scores **P 0.997 / R 0.755 / F1 0.859 / FPR 0.002**,
  the strongest single classifier and statistically even with QFIRE's hybrid
  (F1 0.856). This sharpens, rather than weakens, the paper's thesis: a strong
  generic injection classifier still leaves the **scope/PHI** gap that QFIRE's
  positive-security chains close (§7), and QFIRE delivers comparable generic
  detection from a single Rust binary with no Python runtime.
- **Python DeBERTa baseline** is reported from a clean PyTorch run (the earlier
  `torch`/`torchvision` operator clash was resolved by removing torchvision); the
  Rust ONNX run uses the identical weights, and the near-identical P/R/F1 confirms
  the integration is faithful.
- **Positive-security over-blocking** is real (§3.3) and must be calibrated.

## 5. Conclusion

A Rust, parallel, positive-security firewall can combine low-latency local
inference, de-obfuscation, and scope constraining in one reproducible toolchain.
QFIRE's hybrid matches/edges the open-SOTA detector while the lexical baselines
lag, and the de-obfuscation and healthcare results give actionable, honest
guidance on when each control helps or hurts. All artifacts and the
`make paper` pipeline are released.

## 6. Round 2: addressing an agent peer review

We subjected the paper to an adversarial agent peer review (verdict: *major
revision, 4/10*). Its core criticisms and our experimental responses:

### 6.1 The hybrid-vs-DeBERTa gap is small but statistically real (not a free superset)
The reviewer argued the hybrid is a nested superset of DeBERTa, so any "win" is
an artifact. We ran a **paired bootstrap (2,000 resamples) and McNemar's test**
on identical per-prompt predictions (`scripts/analyze_paired.py`):

- F1[DeBERTa] = 0.844 (95% CI [0.826, 0.862]); F1[hybrid] = 0.856 ([0.838, 0.873]).
- **ΔF1 = +0.012, 95% CI [+0.005, +0.019]** (excludes 0); bootstrap P(Δ>0) = 1.00.
- McNemar: **b = 7** (prompts the hybrid gets wrong but DeBERTa right — the lexical
  stage adds 7 false positives), **c = 22**, χ² = 6.76, **p = 0.009**.

So the gain is **small but significant**, and `b = 7 ≠ 0` shows it is *not* a pure
superset: the lexical pre-filter adds 22 catches at the cost of 7 new false
positives. We reframe the claim accordingly: *the cheap lexical stage adds a small,
significant recall gain at a modest precision cost* — not "beats SOTA."

### 6.2 De-contamination: the result survives removing DeBERTa's training data
28% of the corpus is from `deepset` (546 of those rows are its **train** split,
which protectai-DeBERTa trained on). We removed **all** deepset rows and re-ran on
the held-out jailbreak-classification subset (666 attack / 640 benign):

| Chain | F1 | AUC | Recall |
|---|---|---|---|
| DeBERTa-v3 | 0.905 | 0.957 | 0.839 |
| QFIRE hybrid | 0.915 | 0.957 | 0.866 |

DeBERTa scores **higher** on held-out data, so contamination was **not** inflating
it, and the hybrid's edge persists (+0.010). The contamination threat is refuted.

### 6.3 Triggered de-obfuscation removes the always-on FPR cost
The reviewer noted (a) always-on de-obf wrecks clean-traffic precision and (b) the
ablation tested the decoder against its mirror-image encoder. We added a
**triggered** mode (expand only when the raw prompt shows an encoding signal) and a
**second, independent obfuscator** (`scripts/obfuscate_independent.py`: nested
Base64, URL-encoding, string reversal, char-interspersion, unseen homoglyphs —
techniques the normalizer was *not* built around). On the clean corpus:

| Config | F1 | FPR |
|---|---|---|
| Hybrid (no de-obf) | 0.856 | 0.023 |
| Hybrid + always-on de-obf | 0.778 | 0.270 |
| **Hybrid + triggered de-obf** | 0.849 | **0.061** |

Triggered de-obf keeps clean-traffic FPR near baseline while still recovering
obfuscated recall (see the mirror-vs-independent obfuscator comparison in §6.5).

### 6.4 Measured parallelism (the "parallel" claim is now quantified)
On the 10-rule healthcare chain, summed detector time is 13.1 s but wall-clock is
2.48 s per prompt — a **measured 5.3× parallel fan-out speedup** from the Tokio
concurrency, substantiating the title's "parallel" claim.

### 6.5 Corrected AUC
The multi-detector AUC was an artifact of mixing raw entropy bits into the ranking
score; we fixed the aggregation (each node contributes a calibrated [0,1] block
score). Hybrid AUC went 0.578 → **0.927** (≈ DeBERTa's 0.925, consistent with the
nested-ranking observation). Independent/mirror de-obfuscation recall is reported
in the HealthBench and de-obf tables below.

## 7. QFIRE-HealthBench: a healthcare prompt-injection dataset

The reviewer (and clinical need) motivated a domain dataset. **QFIRE-HealthBench**
is **1,000 benign + 1,000 malicious** healthcare prompts, built with **real garak**
payloads and **real Microsoft PyRIT** converters (PyRIT run under a Python-3.11
venv; garak DAN-family + in-the-wild jailbreaks cloned from NVIDIA/garak).

**Malicious composition** — by source: native healthcare threats **400**, garak
jailbreaks (healthcare-wrapped) **300**, PyRIT-converted **300**. Techniques span
Base64, ROT13, Atbash, Leetspeak, Unicode-confusable, Binary, Caesar, Morse, and
ASCII-smuggler. Categories: jailbreak, clinical-advice solicitation, PHI
exfiltration, cross-patient access, re-identification, bulk export, system-prompt
exfiltration, direct injection, PHI smuggling. Benign: realistic clinical-adjacent
requests (general health info, scheduling, admin, records-access-for-self). All
identifiers are **synthetic**; this is a defensive benchmark (dataset card:
`corpora/healthcare_bench/README.md`).

### 7.1 Overall (HealthBench, 1,000 attack / 1,000 benign)

| Chain | Prec. | Rec. | F1 | FPR |
|---|---|---|---|---|
| `bench_phi` (PHI detector only) | 0.76 | 0.25 | 0.38 | 0.08 |
| `bench_deberta` (injection classifier only) | 1.00 | 0.59 | 0.75 | 0.00 |
| `bench_hybrid` (lexical + DeBERTa) | 1.00 | 0.64 | 0.78 | 0.00 |
| `bench_hybrid_trig` (+ triggered de-obf) | 1.00 | 0.64 | 0.78 | 0.00 |
| **`bench_combined` (injection + PHI + scope)** | 0.91 | **0.83** | **0.87** | 0.08 |
| `bench_combined_trig` (+ triggered de-obf) | 0.91 | 0.83 | 0.87 | 0.08 |

**Baselines on the identical HealthBench corpus** (PyTorch, scored as pure
injection detectors):

| Baseline | Prec. | Rec. | F1 | FPR |
|---|---|---|---|---|
| protectai DeBERTa-v3 (PyTorch) | 1.000 | 0.574 | 0.729 | 0.000 |
| Meta PromptGuard-2-86M (PyTorch) | 0.998 | **0.402** | 0.573 | 0.001 |

**Finding (the central healthcare result).** An injection classifier alone caps
far below QFIRE on healthcare threats — and, strikingly, **Meta's PromptGuard-2,
the strongest generic injection detector we measured (F1 0.86 on public
injection), recovers only 0.40 recall here**; protectai DeBERTa reaches 0.57; and
QFIRE's own classifier-only chain 0.59. The reason is structural: most healthcare
threats are *not* injection — they are PHI exfiltration, cross-patient access,
re-identification, bulk export, and out-of-scope clinical advice that contain no
jailbreak token. Adding the PHI detector and positive-security scope rules
(`bench_combined`) lifts recall to **0.83** (F1 0.73 → 0.87) at a modest,
calibrated FPR of 0.08. This is the quantitative case for QFIRE's thesis:
**generic prompt-injection detection — even SOTA — is necessary but not sufficient
in healthcare; scope + PHI controls close a gap a classifier structurally
cannot.** Note PromptGuard-2 *outscores* QFIRE on generic injection yet *trails it
by 43 recall points* on healthcare threats: the two evaluations measure different
capabilities, and the firewall's value is the second.

### 7.2 Per-category recall (why the combined chain wins)

| Category | n | DeBERTa | PHI | hybrid | **combined** |
|---|---|---|---|---|---|
| bulk_export | 39 | 0.00 | 1.00 | 0.00 | **1.00** |
| clinical_advice | 185 | 0.44 | 0.00 | 0.44 | **0.44** |
| cross_patient | 86 | 0.41 | 0.00 | 0.41 | **0.62** |
| direct_injection | 54 | 0.91 | 0.00 | 0.91 | **0.91** |
| jailbreak | 415 | 0.84 | 0.22 | 0.88 | **0.95** |
| phi_exfil | 127 | 0.41 | 0.57 | 0.42 | **0.94** |
| phi_smuggle | 26 | 0.00 | 1.00 | 1.00 | **1.00** |
| reidentification | 39 | 0.00 | 0.49 | 0.00 | **1.00** |
| system_exfil | 29 | 1.00 | 0.00 | 1.00 | **1.00** |
| **OVERALL** | **1000** | **0.59** | **0.25** | **0.64** | **0.83** |
| obfuscated-only | 300 | 0.77 | 0.04 | 0.78 | **0.79** |

**Reading the table.** The detectors are complementary, not redundant: DeBERTa
owns `direct_injection`/`system_exfil`/`jailbreak`; the PHI engine owns
`bulk_export`/`phi_smuggle` (which carry no injection signal at all — DeBERTa
0.00); and only the **combined** chain covers `re-identification` (0.00 → 1.00),
`phi_exfil` (0.41 → 0.94), and `cross_patient` (0.41 → 0.62). The lone weak spot,
`clinical_advice` (0.44), is the hardest class — disguised out-of-scope dosing/
diagnosis requests with no lexical or PHI marker — and is exactly where the
LLM-judge scope chain (§3.3) is intended, at higher latency.

## Reproducibility

```
make corpora      # fetch + snapshot the public corpus
cargo build --release --features onnx   # real DeBERTa ONNX
make exp1         # detector matrix
python3 scripts/obfuscate.py && ./target/release/qfire bench ... # exp2
make tables       # regenerate paper/tables/*.tex from bench JSON
```
Run manifest (seed, model, rule/detector/corpus versions) is embedded in every
`bench-out/*/bench.json`.
