import analyze_throughput as a


def test_median():
    assert a.median([3.0, 1.0, 2.0]) == 2.0
    assert a.median([1.0, 2.0, 3.0, 4.0]) == 2.5
    assert a.median([5.0]) == 5.0


def test_speedup():
    assert a.speedup(summed=100.0, wall=25.0) == 4.0
    assert a.speedup(summed=10.0, wall=0.0) == 0.0   # guard div-by-zero


def test_pct_saved():
    # gated does 30ms of detector work; always does 100ms -> 70% work saved
    assert a.pct_saved(gated=30.0, always=100.0) == 70.0
    assert a.pct_saved(gated=5.0, always=0.0) == 0.0   # guard div-by-zero
