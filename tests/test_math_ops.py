import math_ops

def test_add():
    assert math_ops.add(1, 2) == 3
    assert math_ops.add(-1, 1) == 0
    assert math_ops.add(-1, -1) == -2
    assert math_ops.add(0, 0) == 0
