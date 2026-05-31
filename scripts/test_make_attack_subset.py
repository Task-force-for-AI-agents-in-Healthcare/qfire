import make_attack_subset as m


def test_pick_indices_deterministic_and_sorted():
    a = m.pick_indices(929, 300, seed=42)
    b = m.pick_indices(929, 300, seed=42)
    assert a == b                      # deterministic
    assert len(a) == 300
    assert a == sorted(a)              # sorted ascending
    assert len(set(a)) == 300          # unique
    assert all(0 <= i < 929 for i in a)


def test_pick_indices_different_seed_differs():
    assert m.pick_indices(929, 300, seed=42) != m.pick_indices(929, 300, seed=7)


def test_pick_indices_caps_at_total():
    assert m.pick_indices(10, 300, seed=42) == list(range(10))
