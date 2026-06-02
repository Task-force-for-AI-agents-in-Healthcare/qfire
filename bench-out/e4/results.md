# E4 — End-to-End Agent Harm Reduction — Results

Agent llama3.1:8b (temp 0, seed 42), guard chain bench_combined. 40 attack + 40 benign episodes x guard on/off.

## Harmful-action rate (attack episodes)

| guard | n | harmful | rate | 95% Wilson |
|---|---|---|---|---|
| OFF | 40 | 15 | 0.375 | [0.242, 0.530] |
| ON | 40 | 0 | 0.000 | [0.000, 0.088] |

**Harm reduction: 0.375 -> 0.000 (delta -0.375).**
- direct: OFF 0.450 -> ON 0.000 (n=20 each)
- indirect: OFF 0.300 -> ON 0.000 (n=20 each)

## Benign task-completion rate

| guard | n | completed | rate | 95% Wilson |
|---|---|---|---|---|
| OFF | 40 | 38 | 0.950 | [0.835, 0.986] |
| ON | 40 | 33 | 0.825 | [0.680, 0.913] |

**Utility cost: 0.950 -> 0.825 (delta -0.125).**
