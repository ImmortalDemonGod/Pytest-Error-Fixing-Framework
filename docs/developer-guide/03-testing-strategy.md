# Testing Strategy

A robust testing strategy is essential for maintaining the quality and reliability of `pytest-fixer`. Our approach combines multiple layers of testing to ensure that every part of the system works as expected, from individual components to the end-to-end workflow.

---

## 1. Philosophy: Test-Driven Development (TDD)

We adhere to a TDD philosophy. This means:
1.  **Write a failing test** that defines a new feature or behavior.
2.  **Write the minimum code** necessary to make the test pass.
3.  **Refactor** the code to improve its design while keeping the test green.

This approach ensures that our codebase is always covered by tests and that our design is driven by clear, testable requirements.

---

## 2. Layers of Testing

Our testing strategy is divided into three main layers, mirroring our [System Architecture](./01-architecture.md).

### **Layer 1: Unit Tests**

-   **Purpose:** To verify that individual components (classes, functions) in the `core` (Domain) and `orchestration` (Application) layers work in isolation.
-   **Location:** `tests/unit/`
-   **Characteristics:**
    -   Fast and independent.
    -   Use mocks and stubs to isolate the component under test from external dependencies (like the file system, Git, or LLM APIs).
    -   **Example:** A unit test for the `FixService` would mock the `AIManager` and `GitRepository` to verify that the retry and temperature logic works correctly without making real API calls.

### **Layer 2: Integration Tests**

-   **Purpose:** To verify that components from different layers work together correctly.
-   **Location:** `tests/integration/`
-   **Characteristics:**
    -   Involve real interactions between a limited set of components.
    -   May interact with the file system or a temporary Git repository but should still mock external network calls (e.g., to the OpenAI API).
    -   **Example:** An integration test could verify that the `FixOrchestrator` correctly uses the `PytestRunner` to identify a failure and the `GitRepository` to create a branch, while mocking the `AIManager` to provide a canned fix.

### **Layer 3: End-to-End (E2E) Tests**

-   **Purpose:** To simulate a real user scenario from start to finish, verifying the entire workflow.
-   **Location:** `tests/e2e/`
-   **Characteristics:**
    -   Slow and comprehensive.
    -   Run against a real, temporary project structure with actual failing tests.
    -   May involve real (but controlled) network calls to LLM APIs, often using a dedicated, low-cost model and API key for testing.
    -   **Example:** An E2E test would invoke the CLI with `python -m src.branch_fixer.main fix ...`, point it to a sample project with a known bug, and assert that the tool successfully creates a branch, applies a fix, verifies it, and cleans up.

---

## 3. Running Tests

To run the full suite of tests, use the following command from the root directory:

```bash
pytest
```

To run tests from a specific layer or file:

```bash
# Run all unit tests
pytest tests/unit/

# Run a specific test file
pytest tests/integration/test_fix_orchestrator.py
```
        error = TestError(
            test_file=Path("tests/test_example.py"),
            test_function="test_something",
            error_details=ErrorDetails(error_type="AssertionError", message="Expected X but got Y")
        )
        
        self.assertEqual(error.status, "unfixed")
        self.assertEqual(error.test_function, "test_something")
        self.assertTrue(isinstance(error.id, UUID))
        self.assertEqual(error.error_details.error_type, "AssertionError")
        self.assertEqual(error.error_details.message, "Expected X but got Y")

    def test_start_fix_attempt(self):
        # We want to start a fix attempt with a given temperature and see that attempt recorded
        from pathlib import Path
        from src.domain.models import TestError, ErrorDetails

        error = TestError(
            test_file=Path("tests/test_example.py"),
            test_function="test_something",
            error_details=ErrorDetails(error_type="AssertionError", message="Expected X but got Y")
        )

        attempt = error.start_fix_attempt(0.4)
        self.assertEqual(attempt.attempt_number, 1)
        self.assertEqual(attempt.temperature, 0.4)
        self.assertIn(attempt, error.fix_attempts)
        self.assertEqual(error.status, "unfixed")  # still unfixed until success

    def test_mark_fixed(self):
        # After a successful fix, error should be "fixed"
        from pathlib import Path
        from src.domain.models import TestError, ErrorDetails

        error = TestError(
            test_file=Path("tests/test_example.py"),
            test_function="test_something",
            error_details=ErrorDetails(error_type="AssertionError", message="Expected X but got Y")
        )
        attempt = error.start_fix_attempt(0.4)
        # Pseudocode for success marking:
        # error.mark_fixed(attempt)
        # self.assertEqual(error.status, "fixed")
        # self.assertEqual(attempt.status, "success")

        error.mark_fixed(attempt)
        self.assertEqual(error.status, "fixed")
        self.assertEqual(attempt.status, "success")

    def test_mark_attempt_failed(self):
        from pathlib import Path
        from src.domain.models import TestError, ErrorDetails

        error = TestError(
            test_file=Path("tests/test_example.py"),
            test_function="test_something",
            error_details=ErrorDetails(error_type="AssertionError", message="Expected X but got Y")
        )
        attempt = error.start_fix_attempt(0.4)
        
        # If the attempt fails:
        error.mark_attempt_failed(attempt)
        self.assertEqual(attempt.status, "failed")
        self.assertEqual(error.status, "unfixed")  # still unfixed after a failed attempt
```

**Result**: Running these tests now would fail since `src.domain.models` doesn’t exist.

---

## Step 2: Error Analysis Service Tests

**Goal**: Create a service that, given pytest output, returns a list of `TestError` objects. Define a minimal test to ensure we can parse a known failing test from a snippet of pytest output.

### `tests/test_error_analysis_service.py`

```python
import unittest

class TestErrorAnalysisService(unittest.TestCase):
    def test_analyze_simple_failure(self):
        # Given a simplified pytest output snippet:
        pytest_output = """
        tests/test_example.py::test_something FAILED AssertionError: Expected X but got Y
        -----------------------------
        stack trace details here
        """

        # We expect the service to return a list with one TestError
        from src.domain.services import ErrorAnalysisService
        from pathlib import Path
        service = ErrorAnalysisService()

        errors = service.analyze_errors(pytest_output)
        self.assertIsNotNone(errors)
        self.assertEqual(len(errors), 1)
        error = errors[0]
        self.assertEqual(error.test_file, Path("tests/test_example.py"))
        self.assertEqual(error.test_function, "test_something")
        self.assertEqual(error.error_details.error_type, "AssertionError")
        self.assertIn("Expected X but got Y", error.error_details.message)
```

*Note*: This test defines what we expect from `ErrorAnalysisService`, with no code for it yet.

---

## Step 3: Application Use Cases Tests

**Goal**: Define a test for the main use case—attempting to fix an unfixed error using a `TestFixingService` in the application layer. This service will:

- Retrieve an error by ID.
- Attempt to generate a fix using `AIManager`.
- Apply changes, verify fix using `TestRunner`.
- If successful, mark as fixed and commit with `VCSManager`.
- If failed, revert changes and retry until `max_retries` is reached.

We will **mock dependencies** (`AIManager`, `TestRunner`, `VCSManager`, `ChangeApplier`) since we focus on logic rather than actual integration.

### `tests/test_application_usecases.py`

```python
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

class TestApplicationUseCases(unittest.TestCase):
    def test_attempt_fix_success_on_first_try(self):
        # Setup a mock error repository with one unfixed error
        from src.domain.models import TestError, ErrorDetails
        from pathlib import Path
        error_id = uuid4()
        test_error = TestError(
            id=error_id,
            test_file=Path("tests/test_example.py"),
            test_function="test_something",
            error_details=ErrorDetails(error_type="AssertionError", message="Expected X but got Y")
        )

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = test_error
        mock_repo.get_unfixed_errors.return_value = [test_error]

        # Mock AIManager to always return a CodeChanges object:
        from src.domain.models import CodeChanges
        mock_ai = MagicMock()
        mock_ai.generate_fix.return_value = CodeChanges(original="bug", modified="fix")

        # Mock TestRunner: run_test_and_check returns True on first attempt
        mock_test_runner = MagicMock()
        mock_test_runner.run_test_and_check.return_value = True

        # Mock VCSManager: just commit without error
        mock_vcs = MagicMock()

        # Mock ChangeApplier: apply and revert do nothing
        mock_applier = MagicMock()

        # Now test the service
        from src.application.usecases import TestFixingService
        service = TestFixingService(
            error_repo=mock_repo,
            ai_manager=mock_ai,
            test_runner=mock_test_runner,
            vcs_manager=mock_vcs,
            change_applier=mock_applier,
            initial_temp=0.4,
            temp_increment=0.1,
            max_retries=3
        )

        # Attempt fix
        success = service.attempt_fix(error_id)
        self.assertTrue(success)
        self.assertEqual(test_error.status, "fixed")
        # Ensure commit was called
        mock_vcs.commit_changes.assert_called_once()
        # Ensure test was run
        mock_test_runner.run_test_and_check.assert_called_once_with(test_error.test_file, test_error.test_function)
        # Ensure AI fix generated
        mock_ai.generate_fix.assert_called_once_with(test_error, 0.4)

    def test_attempt_fix_failure_all_retries(self):
        # If the fix never passes verification, we end up returning False
        from src.domain.models import TestError, ErrorDetails
        from pathlib import Path
        error_id = uuid4()
        test_error = TestError(
            id=error_id,
            test_file=Path("tests/test_example.py"),
            test_function="test_something",
            error_details=ErrorDetails(error_type="AssertionError", message="Expected X but got Y")
        )

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = test_error

        # AI returns changes each time, but test never passes:
        from src.domain.models import CodeChanges
        mock_ai = MagicMock()
        mock_ai.generate_fix.return_value = CodeChanges(original="bug", modified="fix")

        mock_test_runner = MagicMock()
        mock_test_runner.run_test_and_check.return_value = False  # never passes

        mock_vcs = MagicMock()
        mock_applier = MagicMock()

        from src.application.usecases import TestFixingService
        service = TestFixingService(
            error_repo=mock_repo,
            ai_manager=mock_ai,
            test_runner=mock_test_runner,
            vcs_manager=mock_vcs,
            change_applier=mock_applier,
            initial_temp=0.4,
            temp_increment=0.1,
            max_retries=2
        )

        success = service.attempt_fix(error_id)
        self.assertFalse(success)
        self.assertEqual(test_error.status, "unfixed")
        # Verifications:
        # AI generate fix should be called twice (max_retries=2)
        self.assertEqual(mock_ai.generate_fix.call_count, 2)
        # Test runner also called twice
        self.assertEqual(mock_test_runner.run_test_and_check.call_count, 2)
        # VCS commit never called
        mock_vcs.commit_changes.assert_not_called()
        # After each failure, revert should be called
        self.assertEqual(mock_applier.revert.call_count, 2)
```

---

## Step 4: Integration Test (Optional at this Stage)

We could write a high-level test simulating the whole pipeline once we have some code. However, for now, these unit tests are sufficient to guide our initial implementation.

---

## Summary of Next Steps

1. **Run These Tests Now**: They will fail because none of the referenced classes or logic exists.
2. **Implement Minimal Code in `src/`**: Develop just enough code to make these tests pass, step by step.
3. **Refactor the Code Once Tests Are Passing**: Improve the code quality while ensuring tests remain green.

We have a clear contract defined by tests, ensuring we only build what’s required and verifying functionality as we proceed.

This test suite and approach should serve as a strong starting point for a TDD-driven rewrite of the `pytest-fixer` tool’s core functionality.

---

## Conclusion

Adopting a Test-Driven Development approach ensures that our development process is guided by well-defined tests, promoting high-quality, maintainable, and reliable code. By following this blueprint, the `pytest-fixer` project will be built incrementally with a strong foundation, allowing for scalable and efficient development.