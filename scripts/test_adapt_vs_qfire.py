import adapt_vs_qfire as a


def test_evade_loop_stops_when_allowed():
    seq = iter([True, True, False])  # blocked, blocked, allowed (evaded)
    res = a.evade_loop("x", blocker=lambda t: next(seq),
                       mutate=lambda t, i: t + str(i), budget=10)
    assert res["evaded"] is True and res["iters"] == 3


def test_evade_loop_budget_exhausted_counts_blocked():
    res = a.evade_loop("x", blocker=lambda t: True,
                       mutate=lambda t, i: t, budget=10)
    assert res["evaded"] is False and res["iters"] == 10


def test_evade_loop_original_already_allowed():
    res = a.evade_loop("x", blocker=lambda t: False,
                       mutate=lambda t, i: t, budget=10)
    assert res["evaded"] is True and res["iters"] == 1


def test_median_iters():
    assert a.median_iters([{"iters": 1}, {"iters": 3}, {"iters": 5}]) == 3
