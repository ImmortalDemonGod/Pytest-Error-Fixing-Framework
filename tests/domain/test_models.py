# tests/domain/test_models.py
import unittest
from uuid import UUID
from pathlib import Path
from dataclasses import dataclass

class TestErrorDomainModel(unittest.TestCase):
    def test_create_test_error(self):
        """
        Test the creation of a TestError aggregate with basic attributes.
        The test error should initialize with correct values and be in an unfixed state.
        """
        # Given
        test_file = Path("tests/example_test.py")
        test_function = "test_something"
        error_type = "AssertionError"
        error_message = "Expected 5 but got 4"
        
        # When
        from branch_fixer.domain.models import TestError, ErrorDetails
        
        error = TestError(
            test_file=test_file,
            test_function=test_function,
            error_details=ErrorDetails(
                error_type=error_type,
                message=error_message
            )
        )
        
        # Then
        self.assertEqual(error.status, "unfixed")
        self.assertEqual(error.test_file, test_file)
        self.assertEqual(error.test_function, test_function)
        self.assertEqual(error.error_details.error_type, error_type)
        self.assertEqual(error.error_details.message, error_message)
        self.assertTrue(isinstance(error.id, UUID))
        self.assertEqual(len(error.fix_attempts), 0)