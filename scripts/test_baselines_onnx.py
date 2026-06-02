import baselines as b


def test_softmax_last_is_injection_when_index_1():
    probs = b._softmax([0.1, 2.0])
    assert b._inj_prob(probs, inj_index=1) > 0.5
    assert b._inj_prob(probs, inj_index=0) < 0.5


def test_resolve_injection_index_picks_separating_class():
    inj_probrows = [[0.2, 0.8], [0.1, 0.9]]
    ben_probrows = [[0.85, 0.15], [0.9, 0.1]]
    assert b._resolve_injection_index(inj_probrows, ben_probrows) == 1
    assert b._resolve_injection_index([[0.8, 0.2]], [[0.2, 0.8]]) == 0
