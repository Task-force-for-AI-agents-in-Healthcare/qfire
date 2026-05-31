import analyze_policy_length as a


def rows():
    # 2 attacks, 2 benign. Block both attacks (TPR=1.0); block one benign (TNR=0.5).
    return [
        {"is_attack": True, "blocked": True},
        {"is_attack": True, "blocked": True},
        {"is_attack": False, "blocked": False},
        {"is_attack": False, "blocked": True},
    ]


def test_metrics_tpr_tnr_j_f1():
    m = a.metrics(rows())
    assert m["tpr"] == 1.0
    assert m["tnr"] == 0.5
    assert abs(m["youden_j"] - 0.5) < 1e-9      # 1.0 + 0.5 - 1
    assert abs(m["over_refusal"] - 0.5) < 1e-9  # 1 - TNR
    # precision = 2/3, recall = 1.0 -> F1 = 0.8
    assert abs(m["f1"] - 0.8) < 1e-9


def test_metrics_handles_empty_classes():
    m = a.metrics([{"is_attack": True, "blocked": False}])
    assert m["tpr"] == 0.0
    assert m["tnr"] == 0.0  # no benign -> defined as 0.0


def test_word_count():
    assert a.word_count("Marketing content only.") == 3
    assert a.word_count("  one   two  ") == 2
