import slice_llama32_dumps as s


def test_slice_rows_picks_attacks_then_all_benign():
    # 5 attack rows (a0..a4) + 3 benign rows (b0..b2)
    rows = [{"is_attack": True, "tag": f"a{i}"} for i in range(5)] + \
           [{"is_attack": False, "tag": f"b{i}"} for i in range(3)]
    out = s.slice_rows(rows, n_attacks_total=5, indices=[1, 3])
    tags = [r["tag"] for r in out]
    assert tags == ["a1", "a3", "b0", "b1", "b2"]   # chosen attacks, then ALL benign


def test_slice_rows_validates_attack_count():
    rows = [{"is_attack": True}] * 4 + [{"is_attack": False}] * 2
    # caller claims 5 attacks but only 4 present -> error
    try:
        s.slice_rows(rows, n_attacks_total=5, indices=[0])
        assert False, "expected ValueError"
    except ValueError:
        pass
