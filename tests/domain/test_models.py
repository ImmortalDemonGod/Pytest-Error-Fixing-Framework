# tests/domain/test_models.py
import unittest
from uuid import UUID
from pathlib import Path
from dataclasses import dataclass

class TestErrorDomainModel(unittest.TestCase):
    def setUp(self):
        """Set up common test data"""
        self.test_file = Path("tests/example_test.py")
        self.test_function = "test_something"
        self.error_type = "AssertionError"
        self.error_message = "Expected 5 but got 4"
        
        from branch_fixer.domain.models import TestError, ErrorDetails
        self.error = TestError(
            test_file=self.test_file,
            test_function=self.test_function,
            error_details=ErrorDetails(
                error_type=self.error_type,
                message=self.error_message
            )
        )

    def test_create_test_error(self):
        """Test the creation of a TestError aggregate with basic attributes."""
        self.assertEqual(self.error.status, "unfixed")
        self.assertEqual(self.error.test_file, self.test_file)
        self.assertEqual(self.error.test_function, self.test_function)
        self.assertEqual(self.error.error_details.error_type, self.error_type)
        self.assertEqual(self.error.error_details.message, self.error_message)
        self.assertTrue(isinstance(self.error.id, UUID))
        self.assertEqual(len(self.error.fix_attempts), 0)

    def test_start_fix_attempt(self):
        """Test starting a new fix attempt."""
        attempt = self.error.start_fix_attempt(temperature=0.4)
        
        self.assertEqual(len(self.error.fix_attempts), 1)
        self.assertEqual(attempt.temperature, 0.4)
        self.assertEqual(attempt.status, "in_progress")
        self.assertEqual(self.error.status, "unfixed")
        
        second_attempt = self.error.start_fix_attempt(temperature=0.5)
        self.assertEqual(len(self.error.fix_attempts), 2)
        self.assertEqual(second_attempt.temperature, 0.5)

    def test_mark_attempt_success(self):
        """Test marking a fix attempt as successful."""
        attempt = self.error.start_fix_attempt(temperature=0.4)
        self.error.mark_fixed(attempt)
        
        self.assertEqual(attempt.status, "success")
        self.assertEqual(self.error.status, "fixed")

    def test_mark_attempt_failed(self):
        """Test marking a fix attempt as failed."""
        attempt = self.error.start_fix_attempt(temperature=0.4)
        self.error.mark_attempt_failed(attempt)
        
        self.assertEqual(attempt.status, "failed")
        self.assertEqual(self.error.status, "unfixed")

    def test_cannot_start_attempt_when_fixed(self):
        """Test that we cannot start new fix attempts on a fixed error."""
        attempt = self.error.start_fix_attempt(temperature=0.4)
        self.error.mark_fixed(attempt)
        
        with self.assertRaises(ValueError):
            self.error.start_fix_attempt(temperature=0.5)

    def test_error_details_immutability(self):
        """Test that ErrorDetails is immutable."""
        from branch_fixer.domain.models import ErrorDetails
        details = ErrorDetails(error_type="TypeError", message="Some error")
        
        with self.assertRaises(Exception):
            details.error_type = "ValueError"

    def test_mark_fixed_with_foreign_attempt(self):
        """Test that marking fixed with an attempt from another error raises ValueError."""
        from branch_fixer.domain.models import TestError, ErrorDetails, FixAttempt
        
        # Create another error instance
        other_error = TestError(
            test_file=Path("tests/other_test.py"),
            test_function="test_other",
            error_details=ErrorDetails(
                error_type="TypeError",
                message="Other error"
            )
        )
        
        # Create an attempt on the other error
        foreign_attempt = other_error.start_fix_attempt(temperature=0.4)
        
        # Try to mark our original error as fixed with the foreign attempt
        with self.assertRaises(ValueError) as cm:
            self.error.mark_fixed(foreign_attempt)
        self.assertEqual(str(cm.exception), "Attempt does not belong to this error")

    def test_mark_failed_with_foreign_attempt(self):
        """Test that marking failed with an attempt from another error raises ValueError."""
        from branch_fixer.domain.models import TestError, ErrorDetails, FixAttempt
        
        # Create another error instance
        other_error = TestError(
            test_file=Path("tests/other_test.py"),
            test_function="test_other",
            error_details=ErrorDetails(
                error_type="TypeError",
                message="Other error"
            )
        )
        
        # Create an attempt on the other error
        foreign_attempt = other_error.start_fix_attempt(temperature=0.4)
        
        # Try to mark our original error's attempt as failed with the foreign attempt
        with self.assertRaises(ValueError) as cm:
            self.error.mark_attempt_failed(foreign_attempt)
        self.assertEqual(str(cm.exception), "Attempt does not belong to this error")