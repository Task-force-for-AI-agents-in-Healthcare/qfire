# E6 NeMo Guardrails — environment setup (reproducible recipe)

NeMo Guardrails 0.17 needs Python ≥3.10 and conflicts with the repo's Python 3.9 env, so
E6 runs in a **dedicated, gitignored venv** (`.venv-e6/`, Python 3.11). The non-obvious
fixes are recorded here because they are not discoverable from `pip install nemoguardrails`
alone (macOS 26 / Apple clang 21 toolchain quirks).

```bash
# 1. venv on Python 3.11 (3.13 lacks prebuilt wheels for NeMo's C-extension deps)
python3.11 -m venv .venv-e6
.venv-e6/bin/python -m pip install -U pip

# 2. annoy 1.17.3 (a NeMo dep) has NO prebuilt wheel and its source build fails on
#    macOS 26 with "'cerrno' file not found" (annoy hardcodes -mmacosx-version-min=10.12,
#    which breaks libc++ header lookup). Fix: point clang at the SDK's c++ headers.
SDK="$(xcrun --show-sdk-path)"
export SDKROOT="$SDK" MACOSX_DEPLOYMENT_TARGET=14.0 \
  CXXFLAGS="-isysroot $SDK -I$SDK/usr/include/c++/v1 -mmacosx-version-min=14.0" \
  CPPFLAGS="-isysroot $SDK"
.venv-e6/bin/python -m pip install --no-binary :all: "annoy>=1.17.3"

# 3. NeMo + Presidio + spaCy model (annoy already satisfied)
.venv-e6/bin/python -m pip install "nemoguardrails==0.17.0" presidio-analyzer presidio-anonymizer
.venv-e6/bin/python -m spacy download en_core_web_lg          # Presidio NER

# 4. LLM backend = local Ollama via its OpenAI-compatible /v1 endpoint. The native
#    `engine: ollama` path is broken here (langchain-ollama 0.2.3 forwards `temperature`
#    as a kwarg the installed ollama-python 0.6.2 rejects), so we use `engine: openai`
#    against http://localhost:11434/v1 instead (see config.yml). Pin compatible langchain:
.venv-e6/bin/python -m pip install "langchain-core>=0.3.85,<0.4" "langchain-openai<0.3"

# 5. jailbreak-detection heuristics need torch + transformers (gpt2-large perplexity,
#    auto-downloaded on first use)
.venv-e6/bin/python -m pip install torch transformers
```

Run: `OPENAI_API_KEY` must be set to any non-empty value (Ollama ignores it; langchain
requires it). The driver sets it automatically. See `scripts/run_e6_nemo.sh`.
