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
        """
        Test the creation of a TestError aggregate with basic attributes.
        The test error should initialize with correct values and be in an unfixed state.
        """
        self.assertEqual(self.error.status, "unfixed")
        self.assertEqual(self.error.test_file, self.test_file)
        self.assertEqual(self.error.test_function, self.test_function)
        self.assertEqual(self.error.error_details.error_type, self.error_type)
        self.assertEqual(self.error.error_details.message, self.error_message)
        self.assertTrue(isinstance(self.error.id, UUID))
        self.assertEqual(len(self.error.fix_attempts), 0)

    def test_start_fix_attempt(self):
        """
        Test starting a new fix attempt.
        Should create an attempt with specified temperature and increment attempt count.
        """
        # When
        attempt = self.error.start_fix_attempt(temperature=0.4)
        
        # Then
        self.assertEqual(len(self.error.fix_attempts), 1)
        self.assertEqual(attempt.temperature, 0.4)
        self.assertEqual(attempt.status, "in_progress")
        self.assertEqual(self.error.status, "unfixed")
        
        # Starting another attempt should increment the counter
        second_attempt = self.error.start_fix_attempt(temperature=0.5)
        self.assertEqual(len(self.error.fix_attempts), 2)
        self.assertEqual(second_attempt.temperature, 0.5)

    def test_mark_attempt_success(self):
        """
        Test marking a fix attempt as successful.
        Should update both attempt and error status.
        """
        # Given an error with an attempt
        attempt = self.error.start_fix_attempt(temperature=0.4)
        
        # When marking as fixed
        self.error.mark_fixed(attempt)
        
        # Then
        self.assertEqual(attempt.status, "success")
        self.assertEqual(self.error.status, "fixed")

    def test_mark_attempt_failed(self):
        """
        Test marking a fix attempt as failed.
        Should update attempt status but keep error unfixed.
        """
        # Given an error with an attempt
        attempt = self.error.start_fix_attempt(temperature=0.4)
        
        # When marking as failed
        self.error.mark_attempt_failed(attempt)
        
        # Then
        self.assertEqual(attempt.status, "failed")
        self.assertEqual(self.error.status, "unfixed")

    def test_cannot_start_attempt_when_fixed(self):
        """
        Test that we cannot start new fix attempts on a fixed error.
        """
        # Given a fixed error
        attempt = self.error.start_fix_attempt(temperature=0.4)
        self.error.mark_fixed(attempt)
        
        # When/Then
        with self.assertRaises(ValueError):
            self.error.start_fix_attempt(temperature=0.5)

    def test_error_details_immutability(self):
        """
        Test that ErrorDetails is immutable (frozen dataclass).
        """
        from branch_fixer.domain.models import ErrorDetails
        
        details = ErrorDetails(error_type="TypeError", message="Some error")
        
        # Attempting to modify should raise an error
        with self.assertRaises(Exception):  # FrozenInstanceError from dataclasses
            details.error_type = "ValueError"