import analyze_adaptive as a


def test_recall_from_block_rate():
    # an all-attack set: recall == block_rate
    assert a.recall_of({"reports": [{"overall": {"block_rate": 0.91}}]}) == 0.91


def test_gap():
    assert a.gap(scope=0.95, classifier=0.40) == 0.55
    assert a.gap(scope=0.40, classifier=0.95) == -0.55  # honest: scope worse


def test_pct():
    assert a.pct(0.873) == "87.3%"
