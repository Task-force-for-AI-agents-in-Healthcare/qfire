import gen_scaling_chains as g


def test_deterministic_rule_filter_excludes_judge():
    rules = [
        {"id": "r_regex", "pipeline": [{"type": "regex"}]},
        {"id": "r_judge", "pipeline": [{"type": "judge"}]},
        {"id": "r_mix", "pipeline": [{"type": "regex"}, {"type": "judge"}]},
        {"id": "r_deb", "pipeline": [{"type": "deberta"}]},
    ]
    ids = g.deterministic_rule_ids(rules)
    assert "r_regex" in ids and "r_deb" in ids
    assert "r_judge" not in ids and "r_mix" not in ids   # any judge node -> excluded
    assert ids == sorted(ids)                            # stable, sorted order


def test_expression_for_builds_AND_chain():
    expr = g.expression_for(["a", "b", "c"])
    assert expr == "a AND b AND c"
    assert g.expression_for(["only"]) == "only"


def test_k_values_capped_at_available():
    assert g.k_values(available=10, ladder=[1, 2, 4, 8, 16, 32]) == [1, 2, 4, 8, 10]
    assert g.k_values(available=100, ladder=[1, 2, 4]) == [1, 2, 4]
