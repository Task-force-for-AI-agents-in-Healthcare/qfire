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
prompts, QFIRE's deterministic hybrid attains **F1 0.86**, edging the open-SOTA
DeBERTa-v3 detector (F1 0.84) while the lexical-only baselines lag (F1
0.16–0.50). We report precision/recall/F1 with 95% Wilson intervals, ROC–AUC,
and latency percentiles; everything regenerates from `make paper`.

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
  Meta `Llama-Prompt-Guard-2-86M` (gated; reported by citation).
- **Metrics:** attack = positive class; precision, recall, F1, FPR, accuracy
  with 95% Wilson intervals, ROC–AUC (continuous detector score), and latency.

## 3. Results

### 3.1 Head-to-head detection (clean public corpus, 929 atk / 1,039 ben)

| System | Prec. | Rec. | F1 | FPR | AUC | latency |
|---|---|---|---|---|---|---|
| Regex denylist (lexical) | 1.00 | 0.29 | 0.46 | 0.00 | 0.65 | <0.1 ms |
| Aho-Corasick keywords | 0.91 | 0.34 | 0.50 | 0.03 | 0.66 | <0.1 ms |
| Entropy heuristic | 0.83 | 0.09 | 0.16 | 0.02 | 0.78 | <0.1 ms |
| **DeBERTa-v3 (real ONNX, ours)** | 0.98 | 0.74 | 0.84 | 0.02 | **0.925** | 255 ms (p95) |
| **QFIRE hybrid** | 0.97 | 0.77 | **0.86** | 0.02 | — † | short-circuited ‡ |
| Hybrid + de-obf (forced, clean traffic) | 0.73 | 0.83 | 0.78 | 0.27 | — † | 279 ms (p95) |

† AUC is only meaningful for the single-score DeBERTa chain; for multi-detector
chains the terminal "score" mixes 0/1 lexical signals with the classifier
probability and is not a calibrated ranking, so we omit it.
‡ See §3.4 on latency and the cross-chain cache caveat.

**Finding.** The QFIRE deterministic hybrid (Aho-Corasick → regex → entropy →
DeBERTa, stop-on-first-block) attains the best F1 (**0.86**), narrowly above the
open-SOTA DeBERTa-v3 detector alone (0.84), by letting cheap detectors raise
recall before the classifier; lexical-only filters are precise but low-recall
(F1 0.16–0.50), confirming the "fast-but-blind" gap.

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
- **PromptGuard-2 (Meta)** weights are gated; we did not obtain a local run and
  report it by citation rather than fabricate numbers.
- **Python DeBERTa baseline** could not be loaded in this environment due to a
  `torch`/`torchvision` operator clash unrelated to the model; the Rust ONNX run
  uses the identical weights, so detector accuracy is unaffected.
- **Positive-security over-blocking** is real (§3.3) and must be calibrated.

## 5. Conclusion

A Rust, parallel, positive-security firewall can combine low-latency local
inference, de-obfuscation, and scope constraining in one reproducible toolchain.
QFIRE's hybrid matches/edges the open-SOTA detector while the lexical baselines
lag, and the de-obfuscation and healthcare results give actionable, honest
guidance on when each control helps or hurts. All artifacts and the
`make paper` pipeline are released.

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
