# tests/test_math_operations.py

def add(a, b):
    # Fixed implementation
    return a + b

def test_add():
    """Verify add() returns the correct sum."""
    assert add(2, 3) == 5