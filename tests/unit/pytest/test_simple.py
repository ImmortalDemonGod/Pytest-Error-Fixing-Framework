# src/branch_fixer/services/pytest/test_simple.py
import pytest
from tests.unit.pytest.comprehensive_test_inputs import MathOperations

def test_add_simple():
    print("Starting add_simple test")
    math = MathOperations()
    result = math.add(2, 3)
    print(f"Result: {result}")
    assert result == 5
    print("stdout capture")

def test_add_negative():
    print("Starting add_negative test")
    math = MathOperations()
    assert math.add(-1, -2) == -3