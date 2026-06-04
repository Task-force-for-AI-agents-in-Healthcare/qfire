# Peer Review — QFIRE: *Beyond Injection Detection (Positive-Security Prompt Firewall for Healthcare)*

**Run:** 2026-06-04 (peer-review skill) · **Venue (assumed):** NeurIPS-style empirical systems/security triad · **Depth:** peer-review · **Draft:** `paper/PAPER.md` (canonical) + `paper/main.tex` + `paper/refs.bib`

> Venue note: the draft has no `venue:` frontmatter. By the skill's heuristics (empirical, LaTeX, systems/security) the NeurIPS triad — methods-skeptic + related-work-hawk + reproducibility-critic — was used. A clinical-informatics venue (JAMIA / npj Digital Medicine) or a security venue (USENIX Security / IEEE S&P) would shift emphasis toward the clinical-deid and threat-model angles; re-run with `--venue` to swap archetypes.

---

## Verdict

### **MAJOR-REVISION — conditional on floor fixes** (one reviewer at reject-as-is on framing)

The empirical core is genuinely interesting and unusually honest (the paper self-reports its own negatives), but it ships with **citation-integrity and reproducibility failures that must be fixed before it can be certified for review**:

1. **A wrong-source citation** anchors a related-work row (Semantic Firewalls — the cited arXiv ID points at an unrelated paper).
2. **Invented regulatory control identifiers** — 4 of 6 HAARF control IDs in the §4 mapping table do not appear in the cited HAARF document.
3. **An unsupported third-party training-data claim** underpins the §6.2 de-contamination rebuttal.
4. **The headline tables are not regenerable** — `make_tables.py` hardcodes the first author's laptop path and reads `bench.json` files that do not exist in the repo, directly refuting the paper's "everything regenerates from `make paper`" claim.

Conditional on those being addressed, the peer-review verdict is **major-revision**: the methods-skeptic flags that the paper's own §7 honest-negative (a *bare* judge already matches the "scaffold") undercuts the abstract's framing; the related-work-hawk identifies ~6 must-add prior works (Dual-LLM/Willison, StruQ, Jatmo, Spotlighting, Presidio, the clinical de-id literature); the reproducibility-critic rates the artifact substrate strong but the headline-table provenance broken.

---

## Floor pass

**28 citations · 24 verified · 1 wrong-source · 2 misrepresented · 2 minor-mischaracterized · 0 misquoted (no external direct quotes) · plus 4 confirmed reproducibility/provenance failures**

Every bib entry resolves to a *real* source (all 17 arXiv IDs HTTP 200, all HF cards/dataset cards live, the HAARF medRxiv DOI resolves with an exact title match, the HHS HIPAA page is a bot-blocked-but-real 403). The failures are not dead links — they are **misattributions**: a citation pointing at the wrong paper, and claims that the cited sources do not support.

| ID | Citation | Resolved | Verdict | Note |
|---|---|---|---|---|
| semanticfirewall2026 | arXiv:2603.03911 | resolves to **wrong paper** | **wrong-source** | ID = Bonfanti et al., *"From Threat Intelligence to Firewall Rules…"* — NOT "Semantic Firewalls w/ Online Ensemble Learning for RAG" |
| haarf2026 | medRxiv 10.64898/2026.04.09.26350519 | verified (title exact) | **misrepresented** | control IDs C3.6.1/C3.4.1/C6.3.1/C2.5.1 absent from HAARF; C3.2.1/C3.2.3 appear only informally |
| protectai_deberta (§6.2 use) | HF card | verified (card live) | **misrepresented** | "trained on [deepset]" — card lists 12 training sets, deepset not among them |
| camel2025 | arXiv:2503.18813 | verified | mischaracterized (minor) | two-LLM separation is the Dual-LLM pattern CaMeL *extends*; CaMeL adds a capability-tracking interpreter |
| nemoguardrails2023 | arXiv:2310.10501 | verified | mischaracterized (minor) | self-check + Presidio PII rails are library features, not in the cited 2023 paper |
| attentiontracker2025 | arXiv:2411.00348 | verified | nuance | "exploit model internals" reads adversarial; it *observes* attention (white-box, accurate) |
| firewallsbench2026 | arXiv:2510.05244 | verified | **SUPPORTED** (all 3 conjuncts: tool-boundary firewalls, benchmarks saturated, 3-stage cascade) |
| oneshield2025 | arXiv:2507.21170 | verified | **SUPPORTED** |
| cognitivefirewall2026 | arXiv:2603.23791 | verified | **SUPPORTED** (split-compute edge/cloud, browser agents, indirect injection) |
| psgagent2025 | arXiv:2509.23614 | verified | **SUPPORTED** (training-free, per-user profiles, cross-turn) |
| ppa2025 | arXiv:2506.05739 | verified | **SUPPORTED** (polymorphic prompt assembly = randomized structure) |
| spin2024 | arXiv:2410.13236 | verified | **SUPPORTED** (self-supervised, detect+reverse) |
| llamafirewall2025 | arXiv:2505.03574 | verified | **SUPPORTED** (PromptGuard 2 + AlignmentCheck + CodeShield confirmed) |
| protectai_deberta (§3.4 use) | HF card | verified | **SUPPORTED** (near-perfect on own split: Acc 0.9999 / F1 0.9998) |
| greshake2023, perez2022, deberta2021*, garak2024, pyrit, agentdojo2024, injecagent2024, deepset_pi, jailbreak_cls, hlyn_deberta70m, ort, ollama, hipaa_safe_harbor, wilson1927 | all | verified | resolve + characterized fairly (`*deberta2021` defined-but-uncited) |

### Wrong-source (1) — **CRITICAL**
- **semanticfirewall2026 → arXiv:2603.03911.** The cited ID resolves to *"From Threat Intelligence to Firewall Rules: Semantic Relations in Hybrid AI Agent and Expert System Architectures"* (Bonfanti, Colaiacomo, Cagliero, Basile, 2026/03/04) — a network-security/expert-system paper. The bib title ("Semantic Firewalls with Online Ensemble Learning for Secure Agentic RAG Systems") and every characterization built on it (related-work Table 1 row; intro "transform prompts into a type-safe closed vocabulary to eliminate syntactic bypasses"; positioning "abstractive protocol transformer / online ensemble") have **no basis in the actually-cited document**. Cited 3×. **Fix:** find the real paper and its correct arXiv ID, re-verify the characterization, or drop the row.

### Misrepresented (2) — must fix
- **HAARF control IDs (§4 table, §5 conclusion).** Fresh-context read of HAARF found C3.6.1, C3.4.1, C6.3.1, C2.5.1 **absent**; C3.2.1/C3.2.3 appear only in red-team scenario prose with no formal definition. The paper presents a "direct" mapping where "each abstract control becomes a versioned rule." **Caveat:** the verifier may not have reached a HAARF appendix/supplement, and a HAARF co-author (Schwoebel) may be on this paper and able to reconcile — but as written and independently verifiable, the specific IDs are not in the source. **Fix:** rebuild the mapping against control IDs that actually exist in HAARF, or recast as "our proposed operationalization" rather than HAARF's own taxonomy.
- **protectai "trained on deepset" (§6.2).** The de-contamination rebuttal asserts 546 deepset rows are "its **train** split, which protectai-DeBERTa trained on." The protectai model card lists 12 training datasets; deepset/prompt-injections is not among them. The *empirical* result (DeBERTa scores **higher** on the held-out split) stands on its own, but the stated *mechanism* ("we removed the data it memorized") is unsupported. **Fix:** substantiate with a citable source or rewrite to not assert memorization (the result refutes contamination regardless).

### Mischaracterized (2 minor) — should fix
- **CaMeL** — add a clause: CaMeL *extends* the Dual-LLM (Willison) pattern with a capability-tracking interpreter; the two-LLM separation alone is Willison's, and is (per CaMeL) insufficient by itself.
- **NeMo Guardrails** — the jailbreak rail is in the 2023 paper, but the self-check/topical and Presidio PII rails are post-paper library features. Cite the NeMo Guardrails docs for the specific input-rail stack you ran, or note they are library (not paper) features.

### Reproducibility / provenance failures (4 confirmed by direct repo inspection)
- **Hardcoded path:** `scripts/make_tables.py:9` → `BASE = "/Users/jim/Desktop/qfire"`. `make tables`/`make paper` crash with `PermissionError: '/Users'` on any other machine.
- **Missing headline data:** `make_tables.py` reads `bench-out/{exp1,exp2,healthcare}/bench.json` + `bench-out/baselines.json`. **Zero `bench.json` files exist anywhere in the repo** (confirmed via `find`). The §3.1 detection matrix, accuracy-CI, de-obf, and HealthBench tables cannot be regenerated from committed artifacts — directly refuting "everything regenerates from `make paper`." (Provenance is *inverted*: the round-2/rebuttal experiments under `bench-out/{adaptive,throughput,e4,e7,external,cascade,...}` **do** carry committed JSON; the most-cited table is the least reproducible.)
- **Seed contradiction:** paper claims "seed 42" throughout; `corpora/healthcare_bench/README.md:30` says the dataset was "Generated deterministically (**seed 1337**)."
- **Count reconciliation:** body "106 rules", Appendix A / lint "113 rules"; actual `- id:` grep = **141 total / 107 excluding `rules/bench` + `rules/e7`**. Neither headline number is the literal filesystem count.

### Unmarked / uncited tools (minor)
- **qualifire Sentinel** (a headline baseline, F1 0.98) is referenced by name but has **no bib entry** — the HF card (`qualifire/prompt-injection-sentinel`) is live; add it.
- **Microsoft Presidio** is invoked 5× (the PHI/PII engine inside the NeMo baseline, and the implicit comparator for QFIRE's own PHI panel) with no citation.

---

## Peer-review pass

### Reviewer 1 — Methods Skeptic (NeurIPS) · severity: **reject-as-is → major-revision**

Credits the paper's candor (self-reported negatives in §3.4/§3.5/§3.10/§7) but holds the line: **the headline "0.40 (PromptGuard-2) vs 0.83 (QFIRE)" is apples-to-oranges** (combined scope+PHI chain vs pure injection classifiers — true by construction), and the paper's own §7 honest-negative shows a **bare llama3.1:8B judge already reaches R 0.82 / F1 0.90**, tying the full "scaffold." So the static-recall headline the abstract/title sell is, on the paper's own evidence, "an LLM asked the right question closes the gap," not "the scaffold does." Required: (1) isolate the scaffold from the model — combined chain vs bare judge with QFIRE's *own* scope prompt, across all axes; (2) leave-one-component-out additive ablation decomposing 0.59→0.83 (PHI vs scope-judge); (3) human-labeled gold HealthBench subset with IAA (benign + malicious are both currently model-generated; benign was "scope-filtered" by the very notion under test → FPR deflation risk); (4) matched-FPR baseline comparison (QFIRE is calibrated to 0.08 FPR; baselines run at default thresholds); (5) report the in-loop cascade collapse (recall 0.13–0.37 at the *deployed* `bench_combined` point) as a co-headline with the strict-chain 100%; (6) cache-disabled latency with dispersion across >1 machine. Also: "classifiers structurally cannot" is overstated (the bare judge is a single-model counterexample); broken section numbering (two §3.10, two §3.13).

### Reviewer 2 — Related-Work Hawk (NeurIPS) · severity: **major-revision**

The empirical core is salvageable but the related-work scaffolding is "currently unsound." Folds in the floor failures (wrong-source C1, HAARF IDs C2, protectai-training C3, CaMeL C4) and adds **missing prior art in all three claimed contribution areas**, of which 1–4, 8, 9 are non-optional:
1. **Dual-LLM / Willison** — absent (the conceptual ancestor; its omission caused C4).
2. **StruQ** (Chen et al.) — absent (structured-query instruction/data separation).
3. **Jatmo** (Piet et al.) — absent (task-specific fine-tune defense; the "do you need a second model" trade-off).
4. **Spotlighting / Hines et al.** — absent (delimiting/datamarking — closest prior art to QFIRE's de-obf + delimiter handling, which the paper's own §3.13 caveat iii stumbles on).
5. SecAlign — absent. 6. **Rebuff / Lakera Guard / Vigil** — absent (the *deployed* prompt-injection firewalls QFIRE most directly competes with; Rebuff is a near-architectural sibling). 7. Llama Guard — present-but-only-dismissed (excluded as baseline OK, but warrants a citation + sentence). 8. **Presidio** — used 5×, never cited. 9. **Clinical de-identification literature** (i2b2/n2c2 shared tasks, Philter, NLM-Scrubber, neural de-id) — absent, "the biggest hole": a regex+structured 18-identifier Safe-Harbor matcher is exactly what this 20-year literature has built; a clinical-NLP reviewer rejects on this alone. Also flags: "complete 18-identifier" is a strong correctness claim unearned by §3.3 (PHI chain alone = 0.25 recall); the Table 1 "Operational limitation" column is asymmetric advocacy; the "first baseline covering all three pillars" claim is vacuous (pillars are QFIRE-defined).

### Reviewer 3 — Reproducibility Critic (NeurIPS) · severity: **major-revision**

"Unusually well-instrumented" — the toolchain, every named script, the rule/chain library, both corpora, the synthetic-identifier dataset card, and all 7 `docs/superpowers/specs/*-results.md` files exist (credit). **But the central "regenerates from `make paper`" claim is false as committed:** hardcoded `/Users/jim/Desktop/qfire` path + the four headline `bench.json` inputs do not exist in the repo (confirmed). Gated baselines (PromptGuard-2, Sentinel) require an HF gate an external reader may lack, with no committed prediction dumps to bridge; Ollama judge models are unpinned bare tags (judge ablations §3.6/§3.9 not weight-reproducible); "seed 42 everywhere" collides with the dataset card's seed 1337 and with admittedly-stochastic LLM-generated corpora/judges. All fixes are mechanical (de-hardcode the path, commit the four `bench.json` or an offline regenerator, pin Ollama digests, dump gated-baseline predictions, reconcile 106/113/141 and seed 42/1337) — no new science.

### Synthesizer

**MAJOR-REVISION — conditional on floor failures being resolved.** All three reviewers converge on major-revision; the methods-skeptic is at reject-as-is on the *current framing* of the abstract/title. The paper is honest and the systems work is real, but it cannot be certified for review until: (floor) the wrong-source citation, the HAARF control-ID mapping, and the protectai-training claim are corrected and independently re-verified; (artifact) `make paper` actually runs on a clean checkout. After the floor fixes + the scaffold-vs-bare-judge isolation + a matched-FPR baseline + the clinical-de-id related work, the synthesizer estimates **borderline** at a systems/security venue — the scope/PHI-gap result is a real contribution if the framing is rewritten to claim only what the experiments isolate.

---

## Action list (priority order)

1. **[floor-fix · CRITICAL]** Fix `semanticfirewall2026`: the cited arXiv:2603.03911 is the wrong paper. Find the real "Semantic Firewalls" source + correct ID, re-verify the Table 1 row and intro characterization, or drop it.
2. **[floor-fix · HIGH]** Rebuild the §4 HAARF control-ID mapping against IDs that actually exist in HAARF (C3.6.1/C3.4.1/C6.3.1/C2.5.1 not found; C3.2.1/C3.2.3 informal-only), or recast as the authors' proposed operationalization rather than HAARF's taxonomy. Reconcile with the HAARF co-author if one is on this paper.
3. **[floor-fix · MED]** §6.2: substantiate "protectai-DeBERTa trained on deepset" with a citable source, or rewrite to not assert memorization (the held-out result refutes contamination either way).
4. **[artifact-fix · HIGH]** De-hardcode `scripts/make_tables.py:9` (`__file__`-relative `BASE`) and commit the four headline `bench-out/{exp1,exp2,healthcare}/bench.json` + `baselines.json` (or an offline regenerator) so `make paper` runs on a clean checkout.
5. **[major-revision]** Isolate the scaffold from the model: combined chain vs bare llama3.1:8B judge (with QFIRE's own scope prompt) across static recall, generic injection, latency, and adaptive families — and rewrite the abstract/title so the static-recall headline claims only what survives.
6. **[major-revision]** Leave-one-component-out additive ablation on HealthBench (classifier → +PHI → +scope → full), CIs + McNemar between rungs.
7. **[major-revision]** Human-labeled gold HealthBench subset (IAA); re-measure FPR on benign prompts not scope-filtered by QFIRE's own notion; anchor the §3.8–3.9 J/TNR ablations.
8. **[major-revision]** Matched-FPR baseline comparison (threshold-sweep PromptGuard-2/DeBERTa/Sentinel on HealthBench); report adaptive robustness at the *deployed* operating point as a co-headline with the strict-chain 100%.
9. **[related-work]** Add the must-cite prior art: Dual-LLM/Willison, StruQ, Jatmo, Spotlighting/Hines, Presidio, and the clinical de-id literature (i2b2/n2c2, Philter); cite the qualifire Sentinel HF card; soften CaMeL and NeMo characterizations.
10. **[polish]** Reconcile seed 42 vs dataset-card seed 1337; reconcile rule counts (106/113/141); pin Ollama model digests; dump gated-baseline predictions; fix duplicated section numbers (§3.10, §3.13); remove or use the uncited `deberta2021` entry.

Re-run `/peer-review paper/PAPER.md` after revisions — the JSON manifest diffs across runs to show which items closed.
