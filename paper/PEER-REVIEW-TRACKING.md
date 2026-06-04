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
| QPR-4 | 1 | **WONTFIX** | HAARF control-ID mapping (§4). Rome's call 2026-06-04: **trust HAARF as-is, no change.** (For the record: 4 of 6 IDs — C3.6.1/C3.4.1/C6.3.1/C2.5.1 — aren't in the *public* medRxiv paper, which only exposes ~14 IDs in red-team scenarios; the co-author has the authoritative 279-control list.) | closed — no change |
| QPR-5 | 1 | **DONE** | §6.2 de-contamination: dropped the unsupported "which protectai-DeBERTa trained on" memorization claim; reframed as a conservative train/eval-overlap sensitivity test. Result unchanged. Approved by Rome 2026-06-04. | PR `fix/paper-citation-integrity` |
| QPR-6 | 2 | **DOING** | CaMeL mischar: it *extends* the Dual-LLM (Willison) pattern with a capability-tracking interpreter; add a clause + cite Willison. | PR `fix/paper-related-work` |
| QPR-7 | 2 | TODO | NeMo Guardrails: self-check + Presidio rails are library features, not in the cited 2023 paper — cite the NeMo docs for the specific input-rail stack, or note as library features. | follow-up PR |
| QPR-8 | 2 | **DOING** | Related-work additions (Reviewer 2). Rome 2026-06-04: scope + ship a focused PR, iterate on it. Shipping the essentials: Dual-LLM/Willison, StruQ, Jatmo, Spotlighting/Hines, clinical de-id (i2b2/n2c2 + Philter). (Optional Rebuff/Lakera/SecAlign/Llama-Guard deferred to PR iteration.) | PR `fix/paper-related-work` |
| QPR-9 | 2 | **WONTFIX** | Methods framing / apples-to-oranges reframe. Rome's call 2026-06-04: **not worried about it.** | closed |
| QPR-10 | 3 | TODO | Consistency polish: seed 42 (paper) vs 1337 (dataset card); rule counts 106/113/141; pin Ollama model digests; duplicate section numbers (§3.10, §3.13); use-or-remove uncited `deberta2021`. | follow-up PR |
| QPR-11 | 3 | **DONE** | Semantic Firewalls Table-1 mechanism verified against the full MDPI PDF (filed at `paper/refs/ai-07-00080.pdf`, CC-BY): the re-grounded description matches; the original "type-safe closed vocabulary" was fully fabricated. | PR `fix/paper-citation-integrity` |
| QPR-12 | 3 | **DONE** | File the cited Semantic Firewalls source PDF — CC-BY allows redistribution → committed to `paper/refs/` with attribution README. | PR `fix/paper-citation-integrity` |

Floor items fully **verified SUPPORTED** (no action): firewallsbench, OneShield,
Cognitive Firewall, PSG-Agent, PPA, SPIN, LlamaFirewall, protectai near-perfect-
on-own-split, all 17 arXiv IDs + HF/medRxiv/HHS resolve.
