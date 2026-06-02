import baselines as b


def test_judge_blocks():
    assert b.judge_blocks("BLOCK: tries to exfiltrate the system prompt") is True
    assert b.judge_blocks("ALLOW") is False
    assert b.judge_blocks("allow - benign question") is False
    # unparseable -> conservative allow (do not over-count blocks)
    assert b.judge_blocks("I'm not sure about that") is False


def test_sentinel_registered():
    keys = [k for k, _ in b.MODELS]
    assert "prompt-injection-sentinel" in keys
    # bare judge present, Llama Guard removed
    ok = [n for n, _, _ in b.OLLAMA_MODELS]
    assert "llm-judge-3.1-8b" in ok
    assert not any("guard" in n for n in ok)
