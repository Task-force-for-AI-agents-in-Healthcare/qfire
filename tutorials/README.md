# QFIRE tutorials

Hands-on, copy-pasteable guides for the main ways people use QFIRE. Every command
here runs **fully offline** against a local Ollama model — no paid API keys
required.

Work through them in order if you're new, or jump to the journey that matches
what you're trying to do.

| # | Tutorial | You are… | You'll learn to… |
|---|----------|----------|------------------|
| 01 | [Getting started](01-getting-started.md) | trying QFIRE for the first time | install, run your first `check`, and read a collapse trace |
| 02 | [Proxy in front of your app](02-proxy-in-front-of-your-app.md) | an app developer with an existing LLM integration | drop QFIRE in by swapping one base URL — no code changes |
| 03 | [Writing a custom rule & chain](03-writing-a-custom-rule.md) | scoping an LLM call to *your* purpose | author a rule, give it fixtures, and wire it into a chain |
| 04 | [Benchmarking & reproducibility](04-benchmarking-and-reproducibility.md) | a researcher or evaluator | replay attack corpora and regenerate the headline metrics |
| 05 | [Healthcare / PHI guardrails](05-healthcare-phi-guardrails.md) | building a clinical-adjacent assistant | block diagnosis, dosing, and PHI exfiltration with the HIPAA chain |
| 06 | [Auditing & reporting](06-auditing-and-reporting.md) | on the hook for compliance / forensics | read the immutable audit log and summarize decisions |

## The one-minute mental model

A QFIRE **rule** scopes an LLM call to a plain-language *purpose* and runs the
inbound prompt through a **detector pipeline** (regex, entropy, a DeBERTa
injection classifier, an LLM scope-judge, …). A **chain** collapses many rules
into a single terminal decision:

```
prompt ─▶ chain ─▶ [ rule₁ rule₂ … ruleₙ ] ─▶ ALLOW ─▶ forward to provider
                                            └▶ BLOCK ─▶ refusal envelope (provider never contacted)
```

- **`qfire check`** — evaluate a prompt, print the verdict. Never calls a provider.
- **`qfire run`** — evaluate, and on ALLOW execute the downstream call.
- **`qfire serve`** — the same engine as a wire-compatible proxy daemon.
- **`qfire rules explain`** — dry-run a chain and print the full decision tree.
- **`qfire bench`** — replay corpora and emit research metrics.

## Prerequisites (once)

```bash
# 1. Rust 1.85+
rustup update

# 2. A local Ollama with a small model (the default profile)
#    https://ollama.com/download
ollama pull llama3.2

# 3. Build the release binary from the repo root
cargo build --release
```

Everything below assumes you run from the repo root and that
`./target/release/qfire` exists. Tip: `export PATH="$PWD/target/release:$PATH"`
so you can type `qfire` directly.
