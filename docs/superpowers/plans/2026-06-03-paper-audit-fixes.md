# Paper audit fixes — Implementation Plan

> **For agentic workers:** This is a documentation-edit plan (no code, no tests). Steps use checkbox (`- [ ]`) syntax. Verification = `latexmk` clean compile + grep that the specific warning/text changed.

**Goal:** Land all writing + layout + citation fixes from the 2026-06-03 audit as one PR off `master`. No new experiments, no central-thesis rewrite. One sentence added to the abstract acknowledging the bare-judge tie; the rest is mechanical.

**Branch:** `paper/audit-fixes-2026-06-03`

**Scope of changes by file:**
| Path | Purpose |
|------|---------|
| `paper/main.tex` | Most edits live here: typo, abstract sentence, citations inline, table column types, figure caption updates, prose softening |
| `paper/refs.bib` | Add Sentinel + Protect AI LLM Guard entries; remove unused `deberta2021`; fix `firewallsbench2026` year |
| `paper/numbers.tex` | Delete (currently dead — no macros referenced anywhere) |
| `paper/main.pdf` | Regenerate as the final commit |

**Out of scope (deferred):**
- §5.1 / §5.7 prose restructure (buried lede, 100% vs 0.13 reconciliation)
- New experiments (paired McNemar, matched-FPR PR-curve)
- Limitations rewrite (HealthBench construction bias, etc.)
- Chain-naming glossary

These were the audit's Tier-4/5 items; user chose Tier-1/2/3 only.

---

## Pre-flight

- [ ] **Step 0a: Create branch off latest master**

```bash
cd /Users/ingrida/qfire
git checkout master
git pull
git checkout -b paper/audit-fixes-2026-06-03
```

- [ ] **Step 0b: Baseline compile (record warnings to compare against)**

```bash
cd /Users/ingrida/qfire/paper
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex 2>&1 | tail -5
grep -cE "(Overfull|Underfull|Float too large)" main.log
```

Expected: PDF builds (36 pp); count of overfull/underfull/float warnings ≈ baseline (we'll compare after each layout fix).

---

## Group 1: Mechanical text fixes

### Task 1: Fix `Claude Opus 4.8` → `Claude Opus 4.7`

**Why:** Opus 4.8 does not exist. Latest Claude Opus model ID is `claude-opus-4-7`. Same error appears in commit `9f1557d`'s Co-Authored-By trailer — that one we can't fix (already pushed) but the manuscript declaration should be correct.

**Files:** `paper/main.tex:1350-1352`

- [ ] **Step 1: Inspect current text**

```bash
sed -n '1349,1357p' paper/main.tex
```

- [ ] **Step 2: Edit**

Replace at `paper/main.tex:1351`:
```
the Claude Opus~4.8 model (\texttt{claude-opus-4-8}) via the Claude Code CLI---to
```
with:
```
the Claude Opus~4.7 model (\texttt{claude-opus-4-7}) via the Claude Code CLI---to
```

- [ ] **Step 3: Verify**

```bash
grep -n "Opus" paper/main.tex
```
Expected: shows `Opus~4.7`, no `4.8`.

- [ ] **Step 4: Commit**

```bash
git add paper/main.tex
git commit -m "paper: fix Claude model name in AI-use declaration (4.8 → 4.7)"
```

---

### Task 2: Fix `~100 rules` → `106 rules` in abstract

**Why:** Abstract L131 says "ships ${\sim}100$ versioned firewall rules"; `tab:library` (L328 caption, "106 rules") gives the exact count. Pick the precise number.

**Files:** `paper/main.tex:131`

- [ ] **Step 1: Inspect**

```bash
sed -n '130,133p' paper/main.tex
```

- [ ] **Step 2: Edit** — change `${\sim}100$ versioned firewall rules` to `$106$ versioned firewall rules`

- [ ] **Step 3: Verify**

```bash
grep -n "versioned firewall rules" paper/main.tex
```
Expected: one match showing `$106$`.

- [ ] **Step 4: Commit**

```bash
git add paper/main.tex
git commit -m "paper: abstract rule count ~100 → 106 (match tab:library)"
```

---

### Task 3: Soften `AgentDojo targeted-ASR → 0` claims to match Wilson upper

**Why:** Wilson 95% upper bound for the AgentDojo guard-on result is `0.051` (L1150). The text says `→ 0` in three places. Soften to `→ 0` with the upper bound called out, OR rewrite as "contained, 95% Wilson upper 0.05."

**Files:** `paper/main.tex:233-234` (Contribution 4), `paper/main.tex:1150-1151` (already discloses Wilson)

- [ ] **Step 1: Inspect**

```bash
sed -n '232,236p' paper/main.tex
```

Current:
```
front of tool-using agents cuts the harmful-action rate to ${\approx}0$ (mock-EHR
$0.38\rightarrow0.00$; AgentDojo targeted-ASR\,$\rightarrow0$, InjecAgent
${\sim}4\times$)
```

- [ ] **Step 2: Edit** — change `AgentDojo targeted-ASR\,$\rightarrow0$` to `AgentDojo targeted-ASR\,$\rightarrow0$ (Wilson upper $0.05$)`

- [ ] **Step 3: Verify**

```bash
grep -n "Wilson upper" paper/main.tex
```
Expected: at least one match in the Contributions block.

- [ ] **Step 4: Commit**

```bash
git add paper/main.tex
git commit -m "paper: surface AgentDojo Wilson upper bound in intro contribution"
```

---

### Task 4: Investigate and fix `F1 0.73 → 0.87` at L675

**Why:** Auditor flagged this as a typo. Closer look: `protectai DeBERTa-v3 on HealthBench F1 = 0.729 ≈ 0.73` matches exactly, while QFIRE's own classifier-only chain (`bench_deberta` F1 0.746) and QFIRE hybrid (`bench_hybrid` F1 0.778) don't. So `0.73` may be intentional reference to **the baseline classifier**, but the sentence reads as if the antecedent is **QFIRE's classifier-only chain** ("0.59" in the prior sentence). Either change the number or rewrite for clarity.

**Decision needed from author** — pick one before editing:
- **Option A (clarify intent):** keep `0.73`, but rewrite the sentence: "Adding the PHI detector and positive-security scope rules (`bench_combined`) lifts recall from the baseline classifier's `0.57` to `0.83` (F1 `0.73 → 0.87`) at a calibrated FPR of `0.08`."
- **Option B (use QFIRE's hybrid baseline):** change `0.73 → 0.78` so the antecedent matches the preceding sentence about QFIRE's chain.
- **Option C (use QFIRE's classifier-only):** change `0.73 → 0.75` (bench_deberta F1 0.746).

**Files:** `paper/main.tex:672-676`

- [ ] **Step 1: Inspect**

```bash
sed -n '672,678p' paper/main.tex
```

- [ ] **Step 2: Apply chosen option's edit at L675**

- [ ] **Step 3: Verify**

```bash
grep -n "F1 \$0\." paper/main.tex | head -5
```

- [ ] **Step 4: Commit**

```bash
git add paper/main.tex
git commit -m "paper: clarify F1 transition at §5.2 (resolve 0.73 ambiguity)"
```

---

### Task 5: Add one sentence to abstract acknowledging the bare-judge tie

**Why:** User decision. Body §5.2 (L679–695) is honest about a bare `llama3.1:8B` judge reaching recall 0.82 / F1 0.90 on HealthBench, but the abstract still says "scope+PHI controls close a gap a classifier structurally cannot." Add one sentence so the reader is not misled before they reach §5.2.

**Files:** `paper/main.tex:146-149`

- [ ] **Step 1: Inspect**

```bash
sed -n '143,150p' paper/main.tex
```

Current (L143–146):
```
... scope+PHI chain reaches $0.83$ recall (F1~$0.87$) at a calibrated $0.08$
false-positive rate. Generic prompt-injection detection, even SOTA, is therefore
necessary but not sufficient for healthcare LLM agents; positive-security scope
and PHI controls close a gap a classifier structurally cannot.
```

- [ ] **Step 2: Edit** — append after `close a gap a classifier structurally cannot.`:

```
A bare LLM judge also closes most of this static-corpus gap (F1~$0.90$);
QFIRE's distinctive contribution beyond accuracy is auditable determinism,
bounded latency, and adaptive robustness, where the bare judge falls to
$34$--$59\%$ recall (\S\ref{sec:adaptive}).
```

- [ ] **Step 3: Verify abstract still fits in its box**

```bash
cd paper && latexmk -pdf -interaction=nonstopmode main.tex 2>&1 | tail -5
```
Expected: build succeeds; the abstract box on page 1 still fits. Visually check `main.pdf` page 1.

- [ ] **Step 4: Commit**

```bash
git add paper/main.tex
git commit -m "paper: abstract acknowledges bare-judge tie on static HealthBench"
```

---

### Task 6: Update Figure 12 caption to describe the new schematic top panel

**Why:** Commit `9f1557d` redesigned `agent_benchmarks.png` to include an indirect-injection schematic on top of the (a)/(b) panels. The caption at L1186–1192 still only describes (a) and (b).

**Files:** `paper/main.tex:1186-1192`

- [ ] **Step 1: Inspect**

```bash
sed -n '1183,1193p' paper/main.tex
```

- [ ] **Step 2: Edit caption** — replace the current caption body with one that leads with the schematic:

```
\caption{QFIRE on standard agent benchmarks (\texttt{qwen3-coder:30b} agent,
\texttt{important\_instructions} attack, $95\%$ Wilson CIs). The top schematic
shows the indirect prompt-injection threat: an attacker plants instructions in
content the agent later reads via a tool, and QFIRE blocks at the prompt
boundary before the agent acts. Below: (a)~Attack success---Targeted ASR per
AgentDojo suite and pooled, InjecAgent attack-success, and the E4 mock-EHR
harmful-action rate---as no-firewall$\rightarrow$QFIRE dumbbells with Wilson
bands; QFIRE drives AgentDojo ASR to $0$ (Wilson upper $0.05$) and cuts
InjecAgent ASR ${\sim}4{\times}$. (b)~Benign utility (AgentDojo): the
over-refusal cost of a broad per-suite domain scope.}
```

- [ ] **Step 3: Verify**

```bash
cd paper && latexmk -pdf -interaction=nonstopmode main.tex 2>&1 | tail -3
```
Then open `main.pdf` to confirm the caption describes the figure.

- [ ] **Step 4: Commit**

```bash
git add paper/main.tex
git commit -m "paper: update Figure 12 caption for new schematic+dumbbells layout"
```

---

## Group 2: Bibliography fixes

### Task 7: Add `\cite{pyrit}` at mentions of PyRIT

**Why:** `refs.bib:103-108` defines `@misc{pyrit, ...}` but nothing cites it. PyRIT is mentioned in prose three times without a citation.

**Files:** `paper/main.tex:139, 228-229, 519-521`

- [ ] **Step 1: Locate**

```bash
grep -n "PyRIT" paper/main.tex
```

- [ ] **Step 2: Edit each** — change `Microsoft PyRIT` to `Microsoft PyRIT~\cite{pyrit}` on each line (at first mention in the paper at L139 it's `Microsoft PyRIT`; at L228 `Microsoft PyRIT converters`; at L520 `Microsoft PyRIT converters (PyRIT under a Python-3.11 venv`). Add the cite only at the **first** mention (L139) so we don't double-cite — once is enough for academic style.

- [ ] **Step 3: Verify cite resolves after compile**

```bash
cd paper && latexmk -pdf -interaction=nonstopmode main.tex 2>&1 | grep -i "citation" | tail -5
```
Expected: no "Citation `pyrit' undefined" warning.

- [ ] **Step 4: Commit**

```bash
git add paper/main.tex
git commit -m "paper: cite Microsoft PyRIT at first mention"
```

---

### Task 8: Add bibtex entry for qualifire Sentinel + cite at first mention

**Why:** Sentinel (the ModernBERT detector) is benchmarked as the strongest classifier on public injection (`tables/main.tex`, L624 prose) but has no bib entry.

**Files:** `paper/refs.bib`, `paper/main.tex:531`

- [ ] **Step 1: Add to `paper/refs.bib`** (append at end):

```bibtex
@misc{qualifire_sentinel,
  title        = {prompt-injection-sentinel},
  author       = {{Qualifire}},
  howpublished = {Hugging Face model card},
  year         = {2025},
  url          = {https://huggingface.co/qualifire/prompt-injection-sentinel}
}
```

**Verify URL exists before committing:** open the URL in a browser; if the model card is under a different slug (e.g. `qualifire/prompt-injection-sentinel-v2`), adjust the entry. If no public model card exists, change `@misc` to cite the company page instead.

- [ ] **Step 2: Cite at first mention** — at `paper/main.tex:531` change `qualifire \texttt{prompt-injection-sentinel}` to `qualifire \texttt{prompt-injection-sentinel}~\cite{qualifire_sentinel}`.

- [ ] **Step 3: Verify**

```bash
cd paper && latexmk -pdf -interaction=nonstopmode main.tex 2>&1 | grep -i "qualifire_sentinel"
```
Expected: no undefined-citation warning.

- [ ] **Step 4: Commit**

```bash
git add paper/refs.bib paper/main.tex
git commit -m "paper: add bibtex entry and citation for qualifire Sentinel"
```

---

### Task 9: Add cite for Protect AI LLM Guard

**Why:** L529 says protectai DeBERTa-v3 is "the engine inside Protect AI LLM Guard" without citing the product.

**Files:** `paper/refs.bib`, `paper/main.tex:529`

- [ ] **Step 1: Add to `paper/refs.bib`** (append):

```bibtex
@misc{protectai_llmguard,
  title        = {{LLM Guard}: The Security Toolkit for {LLM} Interactions},
  author       = {{Protect AI}},
  howpublished = {\url{https://github.com/protectai/llm-guard}},
  year         = {2024}
}
```

- [ ] **Step 2: Cite at L529** — change `Protect~AI LLM Guard` to `Protect~AI LLM Guard~\cite{protectai_llmguard}`.

- [ ] **Step 3: Verify** → compile, grep for undefined citations.

- [ ] **Step 4: Commit**

```bash
git add paper/refs.bib paper/main.tex
git commit -m "paper: cite Protect AI LLM Guard at its first mention"
```

---

### Task 10: Fix `firewallsbench2026` year → 2025

**Why:** arXiv ID `2510.05244` = October 2025. Bib `year = {2026}` is wrong.

**Files:** `paper/refs.bib:178-187`

- [ ] **Step 1: Edit** — at the `firewallsbench2026` entry change `year = {2026},` to `year = {2025},`. Leave the key name `firewallsbench2026` alone (renaming would cascade through every `\cite{}`); only the field changes.

- [ ] **Step 2: Verify**

```bash
grep -A1 "firewallsbench2026" paper/refs.bib | head -3
cd paper && latexmk -pdf -interaction=nonstopmode main.tex 2>&1 | tail -3
```
Open `main.pdf` to the bibliography page; check the entry now shows `2025`.

- [ ] **Step 3: Commit**

```bash
git add paper/refs.bib
git commit -m "paper: correct firewallsbench bib year (2026 → 2025; arxiv 2510.05244)"
```

---

### Task 11: Verify `haarf2026` DOI resolves; decide whether to fix

**Why:** Audit flagged `doi = {10.64898/2026.04.09.26350519}` — the `10.64898` prefix is not the standard medRxiv prefix (`10.1101/`). If the DOI doesn't resolve, the bib entry needs the real DOI or should drop to `howpublished = {medRxiv preprint}` with the URL.

**Files:** `paper/refs.bib:156-166`

- [ ] **Step 1: Verify resolution**

```bash
curl -sI "https://doi.org/10.64898/2026.04.09.26350519" | head -5
```
Expected: HTTP 302/301 to a real page, or 404 if the prefix is bogus.

- [ ] **Step 2 (conditional): if DOI is bad**, edit the bib entry to:
```bibtex
@misc{haarf2026,
  title        = {{HAARF}: Healthcare {AI} Agents Regulatory Framework --- ...},
  author       = {Schwoebel, Jim and others},
  howpublished = {medRxiv preprint},
  year         = {2026},
  url          = {https://www.medrxiv.org/content/...v1}
}
```
(use the actual medRxiv URL James can supply; remove `doi`).

- [ ] **Step 3: Verify compile**

```bash
cd paper && latexmk -pdf -interaction=nonstopmode main.tex 2>&1 | tail -3
```

- [ ] **Step 4: Commit** (skip if DOI was fine)

```bash
git add paper/refs.bib
git commit -m "paper: fix haarf2026 bib entry (DOI did not resolve)"
```

---

### Task 12: Delete unused `deberta2021` bibtex entry

**Why:** Audit flagged it as defined but never cited. The architecture is mentioned in prose ("DeBERTa-v3") but the original DeBERTa paper is not referenced — and `protectai_deberta` already cites the trained checkpoint we use.

**Files:** `paper/refs.bib:77-83`

- [ ] **Step 1: Confirm no usage**

```bash
grep -n "deberta2021" paper/main.tex paper/PAPER.md
```
Expected: no results. (If any result appears, do not delete — cite it instead.)

- [ ] **Step 2: Delete the entry** at `paper/refs.bib:77-83` (the entire `@article{deberta2021, ...}` block).

- [ ] **Step 3: Verify**

```bash
cd paper && latexmk -pdf -interaction=nonstopmode main.tex 2>&1 | grep -i "deberta2021"
```
Expected: no output (no undefined-citation warning).

- [ ] **Step 4: Commit**

```bash
git add paper/refs.bib
git commit -m "paper: drop unused deberta2021 bib entry"
```

---

### Task 13: Delete dead `numbers.tex` (or wire the macros in — pick one)

**Why:** `numbers.tex` defines `\qfiref`, `\qfirerecall`, `\qfireprec`, `\debertaf`, `\debertap`, `\pyp` — none of these macros are used anywhere in `main.tex`. The abstract claim "every table regenerates from a single `make paper` target" (L150) is technically true for tables, but readers expecting macro-driven numbers will be misled. Easiest fix: delete the file.

**Files:** `paper/numbers.tex`, `paper/main.tex:94`

- [ ] **Step 1: Confirm macros are unused**

```bash
grep -nE "\\\\(qfiref|qfirerecall|qfireprec|debertaf|debertap|pyp)\\b" paper/main.tex
```
Expected: no output.

- [ ] **Step 2: Decide**
- If you want to wire macros in later: skip this task and leave `numbers.tex` alone.
- Otherwise: delete `paper/numbers.tex` and remove the `\IfFileExists{numbers.tex}{\input{numbers.tex}}{}` line at `paper/main.tex:94`.

- [ ] **Step 3: Verify**

```bash
cd paper && latexmk -pdf -interaction=nonstopmode main.tex 2>&1 | tail -3
```

- [ ] **Step 4: Commit**

```bash
git rm paper/numbers.tex
git add paper/main.tex
git commit -m "paper: remove dead numbers.tex (macros unused in main.tex)"
```

---

## Group 3: Table caption + content improvements

### Task 14: `tab:main` (L1364) — flag cold/warm and sample asymmetry

**Files:** `paper/main.tex:1366-1370`

- [ ] **Step 1: Inspect** — `sed -n '1364,1372p' paper/main.tex`

- [ ] **Step 2: Edit caption** — add at end of caption:
```
QFIRE DeBERTa latencies are \emph{cold} (uncached first call);
PyTorch baselines are similarly uncached. Lexical detectors are warm.
```

- [ ] **Step 3: Verify** → compile.

- [ ] **Step 4: Commit**

```bash
git add paper/main.tex
git commit -m "paper: tab:main caption — disclose cold-vs-warm latency convention"
```

---

### Task 15: `tab:ci` (L1374) — clarify paired comparisons

**Files:** `paper/main.tex:1376-1384`

- [ ] **Step 1: Edit** — change the parenthetical:
```
a narrower interval means more certainty, and non-overlapping intervals indicate a real difference.
```
to:
```
a narrower interval means more certainty. Non-overlapping intervals here are
indicative rather than a paired test; we report them on the same prompts.
```

- [ ] **Step 2: Verify** → compile.

- [ ] **Step 3: Commit**

```bash
git add paper/main.tex
git commit -m "paper: tab:ci — soften 'non-overlapping' claim (paired, not unpaired)"
```

---

### Task 16: `tab:deobf` (L1388) — disclose always-on FPR cost

**Files:** `paper/main.tex:1390-1396`

- [ ] **Step 1: Edit** — append to caption:
```
Always-on decoding raises FPR to $0.27$ on clean traffic
(\S\ref{sec:deobf}), motivating triggered-only deployment.
```

- [ ] **Step 2: Verify** → compile.

- [ ] **Step 3: Commit**

```bash
git add paper/main.tex
git commit -m "paper: tab:deobf caption — flag always-on FPR cost"
```

---

### Task 17: `tab:hc` (L1400) — add sample size

**Files:** `paper/main.tex:1402-1411`

- [ ] **Step 1: Inspect** — confirm sample size by looking at the source data file.

```bash
cat scripts/run_healthcare.sh 2>/dev/null | head -20 || grep -nE "hipaa_phi|healthcare" scripts/make_tables.py | head -10
```

- [ ] **Step 2: Edit** — add `($n=$ … attack and … benign)` early in the caption. (Author fills in `n`.)

- [ ] **Step 3: Verify** → compile.

- [ ] **Step 4: Commit**

```bash
git add paper/main.tex
git commit -m "paper: tab:hc caption — state sample size"
```

---

### Task 18: `tab:judgeabl` (L1415) — replace "0.96 est." κ

**Files:** `paper/main.tex:1427-1432`

- [ ] **Step 1: Compute or remove** — find Qwen3 8B vs Llama 3.1 baseline agreement from the run outputs and replace `($\kappa{=}0.96$ est.)` with the computed value. If the raw run is gone, change to `($\kappa$ estimated from $94.5\%$ agreement)` — i.e. own the estimation rather than dropping a vague "est."

```bash
grep -rn "Qwen3" bench-out/ 2>/dev/null | head -5
```

- [ ] **Step 2: Edit accordingly**.

- [ ] **Step 3: Verify** → compile.

- [ ] **Step 4: Commit**

```bash
git add paper/main.tex
git commit -m "paper: tab:judgeabl — replace 'κ=0.96 est.' with explicit value or note"
```

---

### Task 19: `tab:failures` (L1578) — "real verdicts" → "selected illustrative"

**Files:** `paper/main.tex:1591-1595`

- [ ] **Step 1: Edit** — change `Real QFIRE-HealthBench attacks the injection classifier (protectai DeBERTa-v3) passes but QFIRE blocks, one per category. Verdicts are from the actual benchmark run; identifiers are synthetic.` to:
```
Selected QFIRE-HealthBench attacks (one per category) where the injection
classifier (protectai DeBERTa-v3) allows and QFIRE blocks. Verdicts are from the
actual benchmark run; identifiers are synthetic. These are illustrative examples
behind the $0.40\rightarrow0.83$ recall jump, not a complete enumeration.
```

- [ ] **Step 2: Verify** → compile.

- [ ] **Step 3: Commit**

```bash
git add paper/main.tex
git commit -m "paper: tab:failures caption — flag as illustrative, not enumerative"
```

---

### Task 20: `tab:related` (L260) — soften "Limitation" column editorialization

**Why:** The Limitation column on competitor systems ("High latency from Python / PyTorch inference", etc.) reads as critique without measurement-cited backing. Either tone down to descriptive (not evaluative) or add a footnote pointing to the source of the latency/scale claim.

**Files:** `paper/main.tex:268-294`

- [ ] **Step 1: Inspect**

```bash
sed -n '260,300p' paper/main.tex
```

- [ ] **Step 2: Edit** — change column header from `Limitation` to `Trade-off`. For each row, soften evaluative wording. Specific changes:
- L271 `High latency from Python / PyTorch inference` → `Python/PyTorch inference path (latency depends on host)`
- L274–275 `Reliance on external API management and standard datasets` → `Depends on external API management`
- L279 `Cloud semantic verification raises privacy and latency issues` → `Cloud semantic verification stage has privacy and latency trade-offs`
- L282 `High compute cost; hard to deploy stateless` → `Per-user profiling cost; not stateless`
- L286 `Demands structured, application-specific translation schemas` → `Requires application-specific translation schemas`
- L288–289 `Offline scanner, not an inline filter` → `Offline scanner (not an inline filter)`

- [ ] **Step 3: Verify**

```bash
cd paper && latexmk -pdf -interaction=nonstopmode main.tex 2>&1 | tail -3
```

- [ ] **Step 4: Commit**

```bash
git add paper/main.tex
git commit -m "paper: tab:related — 'Limitation' → 'Trade-off'; soften editorial phrasing"
```

---

### Task 21: `tab:haarf` (L1236) — soften caption claim about "measured evidence"

**Files:** `paper/main.tex:1250-1252`

- [ ] **Step 1: Edit** — change `QFIRE is the runtime mechanism that satisfies it and produces the measured evidence.` to `QFIRE is the runtime mechanism that satisfies it; the measured evidence backing each control lives in the referenced sections.`

- [ ] **Step 2: Verify** → compile.

- [ ] **Step 3: Commit**

```bash
git add paper/main.tex
git commit -m "paper: tab:haarf caption — point at where evidence lives (not the table)"
```

---

## Group 4: Layout / compile-warning fixes

### Task 22: Convert `tab:haarf` `p{}` columns to ragged-right `L{}`

**Why:** Underfull boxes (badness 2119–10000) at L1242–1247 come from narrow `p{2.6cm}p{5.4cm}p{4.6cm}` justified columns not breaking long words. Switch to the existing `L{...}` column type already defined at L62.

**Files:** `paper/main.tex:1238`

- [ ] **Step 1: Edit** — change `\begin{tabular}{p{2.6cm}p{5.4cm}p{4.6cm}}` to `\begin{tabular}{L{2.6cm}L{5.4cm}L{4.6cm}}`.

- [ ] **Step 2: Verify warnings dropped**

```bash
cd paper && latexmk -pdf -interaction=nonstopmode main.tex 2>&1 > /dev/null
grep -cE "Underfull.*1242|Underfull.*1243|Underfull.*1244|Underfull.*1245|Underfull.*1246|Underfull.*1247" main.log
```
Expected: count drops vs baseline. (Line numbers will shift if Task 5's abstract sentence pushed text down — grep for `Underfull \\hbox` count instead.)

- [ ] **Step 3: Visual check** — open `main.pdf`, find the HAARF control table, confirm cells are ragged-right and read cleanly.

- [ ] **Step 4: Commit**

```bash
git add paper/main.tex
git commit -m "paper: tab:haarf — ragged-right columns to clear underfull warnings"
```

---

### Task 23: Convert `tab:failures` `p{}` column to ragged-right `L{}`

**Files:** `paper/main.tex:1579`

- [ ] **Step 1: Edit** — change `\begin{tabular}{p{2.4cm}p{8.0cm}cc}` to `\begin{tabular}{L{2.4cm}L{8.0cm}cc}`.

- [ ] **Step 2: Verify** → compile, recount underfull warnings.

- [ ] **Step 3: Commit**

```bash
git add paper/main.tex
git commit -m "paper: tab:failures — ragged-right column for long quoted prompts"
```

---

### Task 24: Fix `fig:approaches` "Float too large for page by 12.97pt"

**Why:** L1568 warning. The 0.92·\linewidth bottom minipage + two 0.49·\linewidth top minipages slightly overrun.

**Files:** `paper/main.tex:1547-1568`

- [ ] **Step 1: Inspect** — `sed -n '1547,1570p' paper/main.tex`

- [ ] **Step 2: Edit two things**
1. Shrink the qfire panel: change `\begin{minipage}{0.92\textwidth}` to `\begin{minipage}{0.78\textwidth}` at L1559.
2. Slightly shrink top panels: change both `\begin{minipage}{0.49\textwidth}` to `\begin{minipage}{0.47\textwidth}` (L1549, L1553).

- [ ] **Step 3: Verify warning gone**

```bash
cd paper && latexmk -pdf -interaction=nonstopmode main.tex 2>&1 | grep "Float too large"
```
Expected: no match.

- [ ] **Step 4: Visual check** — open `main.pdf` to the supplementary-figures page; confirm the three-panel layout still reads correctly (titles fit, no panel is cropped).

- [ ] **Step 5: Commit**

```bash
git add paper/main.tex
git commit -m "paper: fig:approaches — shrink minipages to clear float-too-large warning"
```

---

### Task 25: (optional) Eliminate the `\fbox`-induced 1pt overfull warnings

**Why:** The `\renewcommand{\includegraphics}` at L80–82 wraps every image in a `\fbox` of width `0.5pt`. A `width=\linewidth` image becomes `\linewidth + 2*0.5pt`, exceeding the line width by exactly 1pt → all the "Overfull \hbox (1.0pt too wide)" warnings.

This is cosmetic noise — the visible frame doesn't actually clip — but if you want clean log output:

**Files:** `paper/main.tex:78-82`

- [ ] **Step 1: Edit** — replace the renewed command with one that subtracts the frame width:
```latex
\let\oldincludegraphics\includegraphics
\renewcommand{\includegraphics}[2][]{%
  \setlength{\fboxsep}{0pt}\setlength{\fboxrule}{0.5pt}%
  \settowidth{\@tempdima}{\fbox{\oldincludegraphics[#1]{#2}}}%
  \fbox{\oldincludegraphics[#1]{#2}}}
```

Or, simpler: leave the `\fbox` but apply `\sbox` and `\resizebox` to constrain to `\linewidth`. The cleanest fix is to drop the framing on full-width images:

```latex
\renewcommand{\includegraphics}[2][]{%
  \begingroup
    \setlength{\fboxsep}{0pt}\setlength{\fboxrule}{0.5pt}%
    \fbox{\oldincludegraphics[#1]{#2}}%
  \endgroup}
```
…and globally pass `width=\linewidth-1.2pt` instead of `width=\linewidth` on the offending images. Both approaches are ugly. **Recommendation: leave this alone** — these are sub-pixel warnings that do not show. Skip the task unless the author specifically wants a clean log.

- [ ] **Step 2: Decision** — skip and document, or apply.

- [ ] **Step 3: (if applied) Commit**

```bash
git add paper/main.tex
git commit -m "paper: silence 1pt \\fbox-induced overfull warnings"
```

---

## Group 5: Final rebuild and PR

### Task 26: Clean rebuild and visual review

- [ ] **Step 1: Clean rebuild**

```bash
cd /Users/ingrida/qfire/paper
latexmk -C  # purge aux files
latexmk -pdf -interaction=nonstopmode main.tex 2>&1 | tail -10
```
Expected: PDF builds, page count unchanged or +/- 1 (the abstract sentence may push one paragraph).

- [ ] **Step 2: Compare warning counts**

```bash
grep -cE "(Overfull|Underfull|Float too large)" main.log
```
Expected: count is lower than baseline from Step 0b.

- [ ] **Step 3: Visual diff key pages** — open `main.pdf` and check, in order:
1. Page 1: abstract box still fits (Task 5 added a sentence)
2. Page 2–3: hero figure and rule-library table look unchanged
3. Page with `tab:haarf`: ragged-right columns read cleanly (Task 22)
4. Appendix Figure `fig:approaches`: three panels fit without overrun (Task 24)
5. Appendix Table `tab:failures`: prompts wrap cleanly (Task 23)
6. Bibliography: `firewallsbench` shows year 2025; new entries for Sentinel and LLM Guard present

- [ ] **Step 4: Commit rebuilt PDF**

```bash
git add paper/main.pdf
git commit -m "paper: rebuild PDF after audit fixes"
```

---

### Task 27: Open the PR

- [ ] **Step 1: Push branch**

```bash
git push -u origin paper/audit-fixes-2026-06-03
```

- [ ] **Step 2: Open PR**

```bash
gh pr create --title "paper: audit fixes (writing + layout + citations)" --body "$(cat <<'EOF'
## Summary
Lands the writing / layout / citation fixes surfaced by the 2026-06-03 audit. Mechanical only — no new experiments, no central-thesis rewrite.

### What's in
- **Mechanical fixes** — Opus 4.7 model name (was 4.8), `~100`→`106` rule count, `F1 0.73→0.87` clarification at §5.2, soften "→0" claims with Wilson upper, Figure 12 caption matches its new schematic+dumbbell design
- **Abstract** — one sentence acknowledging the bare-judge tie on static HealthBench (body §5.2 already discloses this honestly; abstract was over-claiming)
- **Citations** — add `\cite{pyrit}`; add bib entries for qualifire Sentinel and Protect AI LLM Guard; fix `firewallsbench` year 2026→2025; verify haarf2026 DOI; drop unused `deberta2021`; remove dead `numbers.tex`
- **Tables** — ragged-right columns on `tab:haarf` and `tab:failures` (clears underfull warnings); caption clarifications on `tab:main` (cold/warm), `tab:ci` (paired vs unpaired), `tab:deobf` (always-on FPR), `tab:hc` (sample size), `tab:judgeabl` (κ estimate), `tab:failures` (illustrative not enumerative), `tab:related` ("Limitation" → "Trade-off"), `tab:haarf` (point at evidence)
- **Layout** — shrink `fig:approaches` panels to clear "Float too large" warning

### What's out (queued for separate PRs)
- §5.1 buried-lede restructure (Sentinel-first)
- §5.7 "100% vs Stage-3 0.13" reconciliation
- Limitations rewrite (HealthBench construction bias; in-sample FPR calibration; bare-judge static-corpus tie)
- Chain-naming glossary
- Matched-FPR PR curve for PromptGuard-2 on HealthBench (needs benchmark re-run)
- Paired McNemar / bootstrap for "statistically tied" claims (needs benchmark re-run)

## Test plan
- [ ] `latexmk -pdf main.tex` builds cleanly
- [ ] No undefined-citation warnings
- [ ] Overfull/underfull/float warning count drops vs baseline
- [ ] Visual check: abstract still fits its box; Fig. `fig:approaches` panels fit; `tab:haarf` and `tab:failures` read cleanly
- [ ] Bibliography shows Sentinel + LLM Guard entries; `firewallsbench` year is 2025; no `deberta2021` entry

🤖 Drafted with Claude Code; reviewed and edited by the authors.
EOF
)"
```

- [ ] **Step 3: Return PR URL**

---

## Self-Review

**Spec coverage:** All chosen Tier-1/2/3 items from the audit have tasks. Tier-4/5 (§5.1 restructure, §5.7 reconciliation, Limitations rewrite, new experiments) are explicitly out of scope per the user decision.

**Placeholders:** Task 4 (the 0.73 typo) and Task 11 (haarf DOI) both need an author judgment call — these are flagged explicitly with the decision points listed, not buried as "TBD." Task 17 needs the author to fill in `n` from the data file; the verification step shows how to find it. Task 18 needs the κ recomputed; the grep is given.

**Ordering note:** Group 1 (text) → Group 2 (bib) → Group 3 (caption) → Group 4 (layout) is the natural order because layout warnings shift in line number after text edits, so doing layout last avoids stale line references.

**One known interaction:** Task 5 (abstract sentence) may push body text down by ~1 line on page 1. If the abstract box overflows, fall back to a shorter version of the sentence — keep the substance ("bare LLM judge matches on static corpus; QFIRE's edge is auditability + adaptive robustness") but trim words.
