# E7 — Standard agent benchmarks (AgentDojo + InjecAgent)

**Agent model:** `qwen3-coder:30b` · **Judge:** `gemma2:9b`  
**AgentDojo attack:** `important_instructions` · benchmark_version `v1.2.2`  
**Guard ON:** per-suite domain-scope chains e7_<suite> / e7_injecagent (injection default + fixed-domain positive-security scope); E7-local injection variants fix shared-rule FPs that only surface on agent transcripts. See E7 findings for disclosed deviations.

## AgentDojo (per-suite + pooled)

Targeted ASR = fraction of security cases where the attacker goal was achieved (lower is better). Benign Utility / Utility-Under-Attack higher is better. Wilson 95% CIs in brackets (percent).

| suite | guard | Benign Utility | Utility-Under-Attack | Targeted ASR | n(benign/sec) |
|---|---|---|---|---|---|
| banking | off | 50.0% [19–81] | 33.3% [16–56] | 27.8% [12–51] | 6/18 |
| banking | on | 16.7% [3–56] | 16.7% [6–39] | 0.0% [0–18] | 6/18 |
| slack | off | 66.7% [30–90] | 50.0% [29–71] | 22.2% [9–45] | 6/18 |
| slack | on | 33.3% [10–70] | 16.7% [6–39] | 0.0% [0–18] | 6/18 |
| travel | off | 83.3% [44–97] | 55.6% [34–75] | 22.2% [9–45] | 6/18 |
| travel | on | 0.0% [0–39] | 0.0% [0–18] | 0.0% [0–18] | 6/18 |
| workspace | off | 33.3% [10–70] | 27.8% [12–51] | 0.0% [0–18] | 6/18 |
| workspace | on | 33.3% [10–70] | 0.0% [0–18] | 0.0% [0–18] | 6/18 |
| POOLED | off | 58.3% [39–76] | 41.7% [31–53] | 18.1% [11–28] | 24/72 |
| POOLED | on | 20.8% [9–40] | 8.3% [4–17] | 0.0% [0–5] | 24/72 |

## InjecAgent (dh / ds / total)

ASR = attack success rate (lower is better). Valid Rate = fraction of agent responses parseable as a tool action.

| split | guard | ASR-valid | ASR-all | Valid Rate | n(breach/valid/all) |
|---|---|---|---|---|---|
| dh | off | 6.9% [2–22] | 6.7% | 96.7% | 2/29/30 |
| dh | on | 3.4% [1–17] | 3.3% | 96.7% | 1/29/30 |
| ds | off | 22.2% [11–41] | 20.0% | 90.0% | 6/27/30 |
| ds | on | 3.4% [1–17] | 3.3% | 96.7% | 1/29/30 |
| total | off | 14.3% [7–26] | 13.3% | 93.3% | 8/56/60 |
| total | on | 3.4% [1–12] | 3.3% | 96.7% | 2/58/60 |

## Side-by-side with E4 (healthcare mock-EHR)

| metric | guard off | guard on |
|---|---|---|
| E4 harmful-action rate | 37.5% | 0.0% |
| E4 benign completion | 95.0% | 82.5% |

_E4 mock-EHR ReAct agent (llama3.1:8b); harmful-action rate with/without QFIRE._
