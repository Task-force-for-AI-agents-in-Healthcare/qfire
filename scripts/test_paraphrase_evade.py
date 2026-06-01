import paraphrase_evade as p


def test_parse_blocked_from_qfire_output():
    assert p.is_blocked("BLOCK by bench_deberta [deberta] — ...") is True
    assert p.is_blocked("ALLOW — expression satisfied (3ms ...)") is False


def test_evade_loop_stops_when_allowed():
    # paraphraser returns variants; scorer says BLOCK until the 3rd, then ALLOW
    variants = iter(["v1", "v2", "v3", "v4", "v5"])
    scores = iter([True, True, False])  # blocked, blocked, allowed
    res = p.evade_loop("seed", lambda _t: next(variants),
                       lambda _t: next(scores), cap=5)
    assert res["evaded"] is True
    assert res["iterations"] == 3
    assert res["text"] == "v3"


def test_evade_loop_gives_up_at_cap():
    res = p.evade_loop("seed", lambda _t: "x",
                       lambda _t: True, cap=4)  # always blocked
    assert res["evaded"] is False
    assert res["iterations"] == 4
    assert res["text"] == "x"
