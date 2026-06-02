import analyze_e4 as a


def test_rate_and_wilson():
    assert a.rate([{"x": True}, {"x": False}], "x") == 0.5
    lo, hi = a.wilson(0, 20)
    assert lo == 0.0 and hi < 0.20


def test_split_by_guard():
    rows = [{"kind": "attack", "guard": False, "harm": True},
            {"kind": "attack", "guard": True, "harm": False}]
    off = [r for r in rows if not r["guard"]]
    on = [r for r in rows if r["guard"]]
    assert a.rate(off, "harm") == 1.0 and a.rate(on, "harm") == 0.0
