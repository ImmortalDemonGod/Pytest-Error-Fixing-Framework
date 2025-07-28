
You are given one or more automatically generated Python test files that test various classes and functions. These tests may have issues such as poor naming conventions, inconsistent usage of self, lack of setUp methods, minimal docstrings, redundant or duplicate tests, and limited assertion coverage. They may also fail to leverage hypothesis and unittest.mock effectively, and might not be logically grouped.

Your task is to produce a single, consolidated, high-quality test file from the given input files. The refactored test file should incorporate the following improvements:
    1.  Consolidation and Organization:
        •   Combine all tests from the provided files into one coherent Python test file.
        •   Group tests into classes that correspond logically to the functionality they are testing. For example, separate test classes by the class or function under test (e.g., TestDataPoint, TestMathOperationsAdd).
        •   Within each class, order test methods logically (e.g., basic functionality first, edge cases, error handling, and round-trip tests afterward).
    2.  Clean, Readable Code:
        •   Use descriptive, PEP 8-compliant class and method names.
        •   Add docstrings to each test class and test method, explaining their purpose and what they verify.
        •   Remove redundant, duplicate, or meaningless tests. Combine or refactor tests that cover the same functionality into a single, comprehensive test method when appropriate.
    3.  Proper Test Fixtures:
        •   Utilize setUp methods to instantiate commonly used objects before each test method, reducing redundancy.
        •   Ensure that instance methods of classes under test are called on properly instantiated objects rather than passing self incorrectly as an argument.
    4.  Robust Assertions and Coverage:
        •   Include multiple assertions in each test to thoroughly verify behavior and correctness.
        •   Use unittest’s assertRaises for expected exceptions to validate error handling.
        •   Implement at least one round-trip test (e.g., encode then decode a data structure, or transform an object multiple times to ensure idempotency).
    5.  Effective Use of Hypothesis:
        •   Employ hypothesis to generate a wide range of input data, ensuring better coverage and exposing edge cases.
        •   Use strategies like st.builds to create complex objects (e.g., custom dataclasses) with varied attribute values.
        •   Enforce constraints (e.g., allow_nan=False) to avoid nonsensical test inputs.
    6.  Mocking External Dependencies:
        •   Use unittest.mock where appropriate to simulate external dependencies or environments, ensuring tests are reliable and isolated from external conditions.

Input:

TEST CODE:
FULL SRC CODE:

Output:
Provide a single Python code block containing the fully refactored, consolidated test file. The output should be ready-to-run with python -m unittest and should exhibit all the improvements listed above.
