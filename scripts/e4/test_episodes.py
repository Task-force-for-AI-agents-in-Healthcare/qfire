import episodes as e


def test_counts_and_kinds():
    eps = e.build()
    assert sum(x["kind"] == "benign" for x in eps) == 40
    assert sum(x["kind"] == "attack" for x in eps) == 40
    assert sum(x.get("vector") == "indirect" for x in eps) == 20


def test_every_episode_has_required_fields():
    for x in e.build():
        assert x["task"] and x["kind"] in ("benign", "attack")
        if x["kind"] == "benign":
            assert x["expected_tool"]            # the benign tool that completes it
        if x.get("vector") == "indirect":
            assert x["injected"]                 # {tool: malicious text}


def test_indirect_injection_targets_a_real_tool():
    import sandbox as s
    for x in e.build():
        if x.get("vector") == "indirect":
            assert all(t in s.TOOLS for t in x["injected"])
