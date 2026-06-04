# QFIRE paper — peer-review action tracking

Source: `/peer-review` run 2026-06-04 (report: `paper/PAPER-peer-review.{md,json}`).
Standing in for beads — the `qf` Dolt beads DB is missing its `issue_prefix`
config, so `bd create` fails here (reads work). Unblock: run `bd init --prefix qf`
from `crew/onyx` (config.yaml already declares `qf`), then these can be replayed
as real beads. Status keys: TODO / DOING / DONE / BLOCKED / DISCUSS.

| # | Pri | Status | Item | PR / owner |
|---|-----|--------|------|-----------|
| QPR-1 | 0 crit | **DONE** | Wrong-source `semanticfirewall2026`: arXiv:2603.03911 → correct MDPI paper (Castro-Maldonado et al., *AI* 7(3):80, 2026, doi:10.3390/ai7030080). Title was right; arXiv ID hallucinated onto an unrelated paper. Fixed bib + the 3 prose sites that carried the false "type-safe closed vocabulary" mechanism. | PR `fix/paper-citation-integrity` |
| QPR-2 | 0 crit | **DONE** | `make paper` broken on any non-author machine: `scripts/*` hardcoded `/Users/jim/Desktop/qfire`. De-hardcoded 24 scripts to the repo-relative idiom. | PR `fix/make-paper-reproducible` |
| QPR-3 | 1 | DONE | Add missing bib entries for headline baseline **qualifire Sentinel** and **Microsoft Presidio** (used 5×); wire `\cite` at first mention. | PR `fix/paper-citation-integrity` |
| QPR-4 | 1 | **DISCUSS** | HAARF control-ID mapping (§4): 4 of 6 IDs (C3.6.1, C3.4.1, C6.3.1, C2.5.1) absent from the public HAARF paper; the real IDs for those topics are C5.1.1 (PHI/identity), C6.2.1 (authority), and category-level C2/C3 (audit/monitoring). HAARF co-author is on the paper — reconcile against their authoritative 279-control list, or recast the table at category granularity / as "our operationalization." | Rome → co-author |
| QPR-5 | 1 | **DISCUSS** | §6.2 de-contamination: "546 deepset rows … which protectai-DeBERTa trained on" is unsupported (protectai model card lists 12 training sets; deepset not among them; neither of our 2 corpus sources appears either). Proposed reword drops the memorization claim, keeps the result. Awaiting Rome's OK. | proposed; needs sign-off |
| QPR-6 | 2 | TODO | CaMeL mischar: it *extends* the Dual-LLM (Willison) pattern with a capability-tracking interpreter; add a clause + cite Willison. | follow-up PR |
| QPR-7 | 2 | TODO | NeMo Guardrails: self-check + Presidio rails are library features, not in the cited 2023 paper — cite the NeMo docs for the specific input-rail stack, or note as library features. | follow-up PR |
| QPR-8 | 2 | **DISCUSS** | Related-work additions (Reviewer 2): essential — Dual-LLM/Willison, StruQ, Jatmo, Spotlighting/Hines, the clinical de-id literature (i2b2/n2c2, Philter); optional — Rebuff/Lakera/Vigil, SecAlign, Llama Guard one-liner. Scope TBD with Rome. | Rome to scope |
| QPR-9 | 2 | DISCUSS | Methods framing (Reviewer 1): the abstract/title attribute the static-recall gap to the "scaffold," but it's an apples-to-oranges comparison (combined chain vs pure injection classifiers). Reframe the headline around the multi-axis story (latency, audit, adaptive robustness, PHI determinism), not raw recall. (Rome: interested in more than R — see PR discussion.) | Rome to decide |
| QPR-10 | 3 | TODO | Consistency polish: seed 42 (paper) vs 1337 (dataset card); rule counts 106/113/141; pin Ollama model digests; duplicate section numbers (§3.10, §3.13); use-or-remove uncited `deberta2021`. | follow-up PR |
| QPR-11 | 3 | DISCUSS | Verify Semantic Firewalls Table-1 mechanism vs the full MDPI PDF (fetch blocked here; re-grounded to the abstract for now). | needs full-text check |

Floor items fully **verified SUPPORTED** (no action): firewallsbench, OneShield,
Cognitive Firewall, PSG-Agent, PPA, SPIN, LlamaFirewall, protectai near-perfect-
on-own-split, all 17 arXiv IDs + HF/medRxiv/HHS resolve.
