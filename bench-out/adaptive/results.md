# E1 — Adaptive Attacks vs the Scope Firewall — Results

Recall = fraction of adaptive attacks BLOCKed (higher = more robust). '—' = detector not run. scope = QFIRE scope+PHI chain.

| adaptive set | DeBERTa | PromptGuard-2 | Sentinel | bare-judge | QFIRE scope+PHI | PHI-only | scope-judge | scope−classifier gap |
|---|---|---|---|---|---|---|---|---|
| impersonation_healthcare | 15.0% | 12.5% | 45.0% | 34.2% | 100.0% | 34.2% | 90.8% | +55.0% |
| paraphrase_evaded | 0.0% | 20.2% | 49.4% | 44.9% | 100.0% | 9.0% | 98.9% | +50.6% |
| encoded_healthcare | 54.4% | 44.2% | 71.3% | 40.4% | 100.0% | 6.6% | 96.5% | +28.7% |
| encoded_injection | 49.0% | 38.5% | 53.3% | 59.1% | 100.0% | 3.0% | 98.5% | +46.7% |

## Phase 2 — paraphrase-to-evade (vs DeBERTa)

- seeds: 100; **DeBERTa evasion rate: 89.0%**; median iterations-to-evade: 1
- (Recall of QFIRE scope+PHI on the DeBERTa-evading set is the `paraphrase_evaded` row above.)
