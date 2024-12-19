from branch_fixer.services.pytest.comprehensive_test_inputs import MathOperations, DataPoint

def test_precision():
    math = MathOperations(precision=3)
    result = math.transform_point(DataPoint(x=1.0, y=1.0))
    # Fixed: using correct precision
    assert round(result.x, 3) == 0.707
