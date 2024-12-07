# Pytest-Fixer TDD Blueprint

## Aligning on the Goal 🧙🏾‍♂️

Let’s adopt a **fully Test-Driven Development (TDD)** approach. This means we define our desired behavior and outcomes as tests first—no production code will be written until we have tests describing what we want.

Below is an outline of how we can start from scratch, writing tests for the core functionality of the `pytest-fixer` project. After we agree on and finalize these tests (the contract of what we want), we will proceed to implement the code that makes these tests pass.

---

## Key Principles

### 1. Test-Driven Development (TDD)
- **Write tests** that define the desired functionality and behavior.
- **Run tests** and see them fail.
- **Write just enough code** to make tests pass.
- **Refactor** as needed, keeping tests green.

### 2. Domain-Driven & Layered Architecture
As previously discussed, we aim for a clean architecture (domain, application, infrastructure). We’ll start simple:
- **Initial Tests**: Focus on core domain logic and application-level use cases.
- **Add Complexity**: Incrementally enhance the architecture as we progress.

### 3. Incremental Approach
- **Start Simple**: Begin with the simplest domain behaviors (e.g., managing `TestError` aggregates, fix attempts).
- **Expand Outward**: Move to application services (e.g., attempting a fix) and then to integration with `AIManager`, `TestRunner`, and `ChangeApplier`.
- **Repeat Cycle**: For each step, write tests first, then code.

---

## What We Want to Achieve

### Core User Story
As a developer, I want the `pytest-fixer` tool to:
1. **Identify test failures** from pytest output.
2. **Store them**.
3. **Attempt to fix them** by:
   - Generating fixes with AI.
   - Applying changes to the code.
   - Verifying if the fix resolves the test failure.
   - If it fails, revert changes and try again with increased AI “temperature”.
   - If it succeeds, mark the error as fixed.

We will break this story into smaller, testable chunks.

---

## Project Structure

We’ll plan tests first. A suggested structure:

```
pytest_fixer/
├── tests/
│   ├── test_domain_models.py
│   ├── test_error_analysis_service.py
│   ├── test_application_usecases.py
│   ├── test_integration.py
│   └── __init__.py
└── src/
    ├── domain/
    ├── application/
    ├── infrastructure/
    └── ...
```

- **Tests Directory (`tests/`)**: All tests reside here.
- **Source Directory (`src/`)**: Future code will be placed here. Currently, only tests are written; no code exists in `src/` yet.

---

## Step 1: Domain Model Tests

**Goal**: Ensure our `TestError` and `FixAttempt` domain models behave correctly. Confirm that we can create `TestError` aggregates, add fix attempts, and mark them as fixed or failed.

### `tests/test_domain_models.py`

```python
import unittest
from uuid import UUID

class TestDomainModels(unittest.TestCase):
    def test_create_test_error(self):
        # We want to create a TestError with file, function, error details
        # We expect an unfixed status initially
        # Pseudocode usage:
        # error = TestError(
        #     test_file=Path("tests/test_example.py"),
        #     test_function="test_something",
        #     error_details=ErrorDetails(error_type="AssertionError", message="Expected X but got Y")
        # )
        # self.assertEqual(error.status, "unfixed")
        # self.assertEqual(error.test_function, "test_something")
        # self.assertIsNotNone(error.id)
        
        # Initially, this test will fail because we have no such classes implemented.
        # We'll just write the asserts we want:
        from pathlib import Path
        from src.domain.models import TestError, ErrorDetails

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