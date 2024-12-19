# src/branch_fixer/services/pytest/test_fixtures.py
import pytest
from branch_fixer.services.pytest.comprehensive_test_inputs import DataPoint

@pytest.fixture
def sample_point():
    print("Setting up fixture")
    point = DataPoint(x=1.0, y=2.0, label="test")
    print(f"Created point: {point}")
    return point

def test_with_fixture(sample_point):
    print(f"Testing with point: {sample_point}")
    assert sample_point.x == 1.0
    assert sample_point.y == 2.0
