# tests/test_math_operations.py

def add(a, b):
    # Fixed implementation
    return a + b

def test_add():
    """This test will fail because of the bug in add()."""
    assert add(2, 3) == 5