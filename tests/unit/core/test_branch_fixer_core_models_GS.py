import unittest
import uuid
from pathlib import Path
from typing import List, Optional

from hypothesis import given, strategies as st

from branch_fixer.core.models import (
    ErrorDetails,
    FixAttempt,
    TestError as TestErrorModel  # Alias to prevent pytest collection warnings
)


class TestErrorDetails(unittest.TestCase):
    """Tests for the ErrorDetails data class."""

    @given(
        error_type=st.text(min_size=1),
        message=st.text(),
        stack_trace=st.one_of(st.none(), st.text())
    )
    def test_error_details_creation(self, error_type: str, message: str, stack_trace: Optional[str]) -> None:
        """Test creating ErrorDetails with various inputs."""
        error_details = ErrorDetails(
            error_type=error_type,
            message=message,
            stack_trace=stack_trace
        )
        self.assertEqual(error_details.error_type, error_type)
        self.assertEqual(error_details.message, message)
        self.assertEqual(error_details.stack_trace, stack_trace)

    def test_error_details_immutable(self) -> None:
        """Test that ErrorDetails instances are immutable."""
        error_details = ErrorDetails(
            error_type="TypeError",
            message="An error occurred.",
            stack_trace="Traceback (most recent call last)..."
        )
        with self.assertRaises(Exception):
            error_details.error_type = "ValueError"

    @given(
        error_type=st.text(min_size=1),
        message=st.text(),
        stack_trace=st.one_of(st.none(), st.text())
    )
    def test_error_details_round_trip(self, error_type: str, message: str, stack_trace: Optional[str]) -> None:
        """Round-trip test: create, serialize, deserialize, and verify equality."""
        error_details = ErrorDetails(
            error_type=error_type,
            message=message,
            stack_trace=stack_trace
        )
        serialized = {
            "error_type": error_details.error_type,
            "message": error_details.message,
            "stack_trace": error_details.stack_trace
        }
        deserialized = ErrorDetails(**serialized)
        self.assertEqual(error_details, deserialized)


class TestFixAttempt(unittest.TestCase):
    """Tests for the FixAttempt data class."""

    @given(
        temperature=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
        status=st.sampled_from(["in_progress", "success", "failed"]),
        id=st.uuids()
    )
    def test_fix_attempt_creation(self, temperature: float, status: str, id: uuid.UUID) -> None:
        """Test creating FixAttempt with various inputs."""
        fix_attempt = FixAttempt(
            temperature=temperature,
            status=status,
            id=id
        )
        self.assertEqual(fix_attempt.temperature, temperature)
        self.assertEqual(fix_attempt.status, status)
        self.assertEqual(fix_attempt.id, id)

    @given(
        temperature=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False)
    )
    def test_fix_attempt_default_values(self, temperature: float) -> None:
        """Test FixAttempt creation with default status and autogenerated id."""
        fix_attempt = FixAttempt(
            temperature=temperature
        )
        self.assertEqual(fix_attempt.temperature, temperature)
        self.assertEqual(fix_attempt.status, "in_progress")
        self.assertIsInstance(fix_attempt.id, uuid.UUID)

    @given(
        temperature=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False)
    )
    def test_fix_attempt_round_trip(self, temperature: float) -> None:
        """Round-trip test: create, serialize, deserialize, and verify equality."""
        fix_attempt = FixAttempt(
            temperature=temperature
        )
        serialized = {
            "temperature": fix_attempt.temperature,
            "status": fix_attempt.status,
            "id": str(fix_attempt.id)
        }
        deserialized = FixAttempt(
            temperature=serialized["temperature"],
            status=serialized["status"],
            id=uuid.UUID(serialized["id"])
        )
        self.assertEqual(fix_attempt, deserialized)


class TestTestError(unittest.TestCase):
    """Tests for the TestError aggregate root."""

    def create_test_error(self) -> TestErrorModel:
        """Helper method to create a fresh TestError instance."""
        error_details = ErrorDetails(
            error_type="ValueError",
            message="Invalid input provided.",
            stack_trace="Traceback (most recent call last)..."
        )
        test_error = TestErrorModel(
            test_file=Path("/path/to/test_file.py"),
            test_function="test_function",
            error_details=error_details
        )
        return test_error

    @given(
        temperature=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False)
    )
    def test_start_fix_attempt(self, temperature: float) -> None:
        """Test starting a new fix attempt."""
        test_error = self.create_test_error()
        initial_attempts = len(test_error.fix_attempts)
        attempt = test_error.start_fix_attempt(temperature=temperature)
        self.assertIsInstance(attempt, FixAttempt)
        self.assertEqual(attempt.temperature, temperature)
        self.assertEqual(attempt.status, "in_progress")
        self.assertIn(attempt, test_error.fix_attempts)
        self.assertEqual(test_error.status, "unfixed")
        self.assertEqual(len(test_error.fix_attempts), initial_attempts + 1)

    @given(
        temperature=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False)
    )
    def test_start_fix_attempt_on_fixed_error(self, temperature: float) -> None:
        """Test that starting a fix attempt on a fixed error raises ValueError."""
        test_error = self.create_test_error()
        test_error.status = "fixed"
        with self.assertRaises(ValueError) as context:
            test_error.start_fix_attempt(temperature=temperature)
        self.assertEqual(str(context.exception), "Cannot start new fix attempt on a fixed error")

    @given(
        fix_attempt=st.builds(FixAttempt)
    )
    def test_mark_fixed(self, fix_attempt: FixAttempt) -> None:
        """Test marking a fix attempt as fixed."""
        test_error = self.create_test_error()
        test_error.fix_attempts.append(fix_attempt)
        test_error.mark_fixed(fix_attempt)
        self.assertEqual(fix_attempt.status, "success")
        self.assertEqual(test_error.status, "fixed")

    @given(
        fix_attempt=st.builds(FixAttempt)
    )
    def test_mark_fixed_with_invalid_attempt(self, fix_attempt: FixAttempt) -> None:
        """Test that marking a non-associated fix attempt as fixed raises ValueError."""
        test_error = self.create_test_error()
        with self.assertRaises(ValueError) as context:
            test_error.mark_fixed(fix_attempt)
        self.assertEqual(str(context.exception), "Attempt does not belong to this error")

    @given(
        fix_attempt=st.builds(FixAttempt)
    )
    def test_mark_fixed_changes_status_only_once(self, fix_attempt: FixAttempt) -> None:
        """Ensure that marking an attempt as fixed changes the status only once."""
        test_error = self.create_test_error()
        test_error.fix_attempts.append(fix_attempt)
        test_error.mark_fixed(fix_attempt)
        with self.assertRaises(ValueError):
            test_error.mark_fixed(fix_attempt)

    @given(
        fix_attempt=st.builds(FixAttempt)
    )
    def test_mark_attempt_failed(self, fix_attempt: FixAttempt) -> None:
        """Test marking a fix attempt as failed."""
        test_error = self.create_test_error()
        test_error.fix_attempts.append(fix_attempt)
        test_error.mark_attempt_failed(fix_attempt)
        self.assertEqual(fix_attempt.status, "failed")
        self.assertEqual(test_error.status, "unfixed")

    @given(
        fix_attempt=st.builds(FixAttempt)
    )
    def test_mark_attempt_failed_with_invalid_attempt(self, fix_attempt: FixAttempt) -> None:
        """Test that marking a non-associated fix attempt as failed raises ValueError."""
        test_error = self.create_test_error()
        with self.assertRaises(ValueError) as context:
            test_error.mark_attempt_failed(fix_attempt)
        self.assertEqual(str(context.exception), "Attempt does not belong to this error")

    @given(
        test_file=st.text(min_size=1).map(Path),
        test_function=st.text(min_size=1),
        error_details=st.builds(
            ErrorDetails,
            error_type=st.text(min_size=1),
            message=st.text(),
            stack_trace=st.one_of(st.none(), st.text())
        ),
        fix_attempts=st.lists(st.builds(FixAttempt), max_size=10)
    )
    def test_test_error_creation(self, test_file: Path, test_function: str, error_details: ErrorDetails, fix_attempts: List[FixAttempt]) -> None:
        """Test creating TestError with various inputs."""
        test_error = TestErrorModel(
            test_file=test_file,
            test_function=test_function,
            error_details=error_details,
            fix_attempts=fix_attempts
        )
        self.assertEqual(test_error.test_file, test_file)
        self.assertEqual(test_error.test_function, test_function)
        self.assertEqual(test_error.error_details, error_details)
        self.assertEqual(test_error.fix_attempts, fix_attempts)
        self.assertIn(test_error.status, ["unfixed", "fixed"])

    def test_test_error_round_trip(self) -> None:
        """Round-trip test: serialize and deserialize TestError and verify equality."""
        test_error = self.create_test_error()
        serialized = {
            "test_file": str(test_error.test_file),
            "test_function": test_error.test_function,
            "error_details": {
                "error_type": test_error.error_details.error_type,
                "message": test_error.error_details.message,
                "stack_trace": test_error.error_details.stack_trace
            },
            "id": str(test_error.id),
            "status": test_error.status,
            "fix_attempts": [
                {
                    "temperature": attempt.temperature,
                    "status": attempt.status,
                    "id": str(attempt.id)
                }
                for attempt in test_error.fix_attempts
            ]
        }
        deserialized_error_details = ErrorDetails(**serialized["error_details"])
        deserialized_fix_attempts = [
            FixAttempt(
                temperature=attempt_data["temperature"],
                status=attempt_data["status"],
                id=uuid.UUID(attempt_data["id"])
            )
            for attempt_data in serialized["fix_attempts"]
        ]
        deserialized_test_error = TestErrorModel(
            test_file=Path(serialized["test_file"]),
            test_function=serialized["test_function"],
            error_details=deserialized_error_details,
            id=uuid.UUID(serialized["id"]),
            status=serialized["status"],
            fix_attempts=deserialized_fix_attempts
        )
        self.assertEqual(test_error, deserialized_test_error)

    @given(
        temperature=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False)
    )
    def test_start_fix_attempt_integrity(self, temperature: float) -> None:
        """Ensure that starting a fix attempt maintains data integrity."""
        test_error = self.create_test_error()
        initial_attempts = len(test_error.fix_attempts)
        attempt = test_error.start_fix_attempt(temperature=temperature)
        self.assertEqual(len(test_error.fix_attempts), initial_attempts + 1)
        self.assertIn(attempt, test_error.fix_attempts)
        self.assertEqual(attempt.status, "in_progress")


if __name__ == "__main__":
    unittest.main()