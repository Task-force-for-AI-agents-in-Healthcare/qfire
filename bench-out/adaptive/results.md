# E1 — Adaptive Attacks vs the Scope Firewall — Results

Recall = fraction of adaptive attacks BLOCKed (higher = more robust). '—' = detector not run. scope = QFIRE scope+PHI chain.

| adaptive set | DeBERTa | PromptGuard-2 | QFIRE scope+PHI | PHI-only | judge-only | scope−classifier gap |
|---|---|---|---|---|---|---|
| impersonation_healthcare | 15.0% | 12.5% | 100.0% | 34.2% | 90.8% | +85.0% |
| paraphrase_evaded | 0.0% | 20.2% | 100.0% | 9.0% | 98.9% | +79.8% |
| encoded_healthcare | 54.4% | 44.2% | 100.0% | 6.6% | 96.5% | +45.6% |
| encoded_injection | 49.0% | 38.5% | 100.0% | 3.0% | 98.5% | +51.0% |

## Phase 2 — paraphrase-to-evade (vs DeBERTa)

- seeds: 100; **DeBERTa evasion rate: 89.0%**; median iterations-to-evade: 1
- (Recall of QFIRE scope+PHI on the DeBERTa-evading set is the `paraphrase_evaded` row above.)
