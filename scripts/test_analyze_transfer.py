import analyze_transfer as a


def test_threshold_for_fpr():
    # benign scores; threshold so that <=20% of benign exceed it (FPR target 0.2)
    benign = [0.1, 0.2, 0.3, 0.4, 0.9]
    thr = a.threshold_for_fpr(benign, target_fpr=0.2)
    fpr = sum(1 for s in benign if s >= thr) / len(benign)
    assert fpr <= 0.2 + 1e-9


def test_rate_at_threshold():
    scores = [0.1, 0.6, 0.7, 0.95]
    assert a.rate_at_threshold(scores, 0.65) == 0.5  # two of four >= 0.65


def test_wilson_interval_basic():
    lo, hi = a.wilson(8, 10)
    assert 0.0 <= lo < 0.8 < hi <= 1.0
