import analyze_cross_model as x


def test_pooled_latency_is_mean_across_domains():
    # mean_detector_ms per domain for one (model,rung)
    assert x.pooled_latency([10.0, 20.0, 30.0, 40.0]) == 25.0


def test_pooled_latency_ignores_none():
    assert x.pooled_latency([10.0, None, 30.0]) == 20.0


def test_pooled_latency_all_none_is_none():
    assert x.pooled_latency([None, None]) is None
