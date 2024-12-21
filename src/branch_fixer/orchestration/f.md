You are given the following background context and requirements for an AIManager class. Study them carefully, then implement a fully functional AIManager class in Python. Afterward, write test code to verify that the implemented AIManager works as intended.

Background Context and Requirements:

The AIManager class manages AI interactions for generating and validating code fixes for failing tests. It must handle multiple attempts if the first fix attempt is not valid, adjust parameters (like temperature) and potentially alter prompt or model parameters between attempts, and internally perform the validation loop without relying on external calls. The entire logic of iterating attempts until a successful fix or exhausting all attempts should be contained within generate_fix.
Key Responsibilities:
	1.	Fix Generation and Validation Loop (generate_fix):
The generate_fix method:
	•	Receives a TestError and an initial temperature.
	•	Constructs a prompt from the given TestError by calling _construct_prompt.
	•	Calls an LLM simulation method to generate a code fix (_simulate_llm_call).
	•	Immediately validates the generated fix by calling verify_fix.
	•	If the fix is invalid and there are remaining attempts, it should adjust parameters (e.g., increase the temperature, modify the prompt, or potentially switch models or add supplemental instructions) and try again.
	•	Continues this loop until:
	•	A valid fix is found, in which case generate_fix returns the CodeChanges.
	•	Or all max_attempts are exhausted, raising CompletionError.
Important:
	•	Multiple attempts must be handled entirely inside generate_fix.
	•	After each attempt, generate_fix calls verify_fix internally—there should be no need for test code to manually call verify_fix for multiple attempts.
	•	Attempt history should be recorded, including temperature, success/failure, and a summary of changes.
	2.	Prompt Construction (_construct_prompt):
The _construct_prompt(error: TestError) method:
	•	Returns a structured prompt dict containing:
	•	System/instructions to fix the failing test.
	•	The original failing test code and detailed error information (error message, stack trace).
	•	Any repository context if available (optional).
	•	Previous attempt summaries (including the attempt number, temperature used, whether the attempt succeeded or failed, and a brief summary of changes attempted).
	•	If any required data is missing, it should raise PromptGenerationError.
	3.	Asynchronous Behavior:
All key methods that simulate external operations should be asynchronous:
	•	generate_fix, _validate_fix, verify_fix, and _simulate_llm_call should be async methods.
	•	Use asyncio.sleep() as needed to simulate I/O or processing time.
	4.	Validation (_validate_fix and verify_fix):
	•	_validate_fix(changes: CodeChanges, error: TestError) simulates checking the code fix.
For testing simplicity, consider the fix valid if "valid_fix" appears in modified_code.
Otherwise, consider it invalid.
	•	verify_fix(changes: CodeChanges, error: TestError) calls _validate_fix and returns True if the fix is valid, False if not.
	•	If verify_fix returns False and attempts remain, generate_fix should try another attempt internally.
	•	If something unexpected happens during validation, raise ValidationError.
	5.	Multiple Strategies:
	•	If the first attempt fails, adjust the approach for the second attempt (e.g., increase temperature by 0.1, tweak prompt instructions, or even switch to a different model name if desired).
	•	Document these changes in the attempt history, stored in attempt_history.
	•	Keep track of each attempt’s parameters and results so that _construct_prompt can include them in subsequent prompts.
	6.	Data Models:
	•	TestError holds error_message, failing_test, stack_trace, and original_code.
	•	CodeChanges holds original_code and modified_code.
	7.	Error Handling:
	•	Raise PromptGenerationError if prompt construction fails (e.g., missing required info).
	•	Raise CompletionError if no valid fix can be found after max_attempts.
	•	Raise ValueError if invalid parameters are provided (e.g., temperature out of range).
	•	Raise ValidationError if unexpected issues occur during validation.
	8.	Unit Tests:
Create a separate test file (e.g., test_ai_manager.py) that imports the implemented AIManager and tests all required behaviors:
	•	Test a scenario where the first attempt succeeds immediately.
	•	Test a scenario where the first attempt fails validation, and a subsequent attempt (with adjusted parameters) succeeds.
	•	Test prompt construction logic to ensure it includes all required fields and handles missing data properly.
	•	Test validation logic, ensuring that the presence of "valid_fix" leads to success, and its absence leads to failure.
	•	Test that proper exceptions are raised for invalid parameters, prompt failures, and completion failures.
	•	Verify that generate_fix handles multiple attempts internally without requiring external code to manage the loop.

Template Code (All methods raise NotImplementedError initially):

import asyncio
from typing import Any, Dict, List, Optional

class PromptGenerationError(Exception):
    """Raised when constructing the prompt fails."""
    pass

class CompletionError(Exception):
    """Raised when no valid completion can be generated after all attempts."""
    pass

class ValidationError(Exception):
    """Raised when validation of a fix fails unexpectedly."""
    pass

class TestError:
    """
    Holds information about a failing test.
    
    Attributes:
        error_message (str): A description of the test error.
        failing_test (str): The name/identifier of the failing test.
        stack_trace (str): The stack trace or debug info for the error.
        original_code (str): The original code that caused the failure.
    """
    def __init__(self, error_message: str, failing_test: str, stack_trace: str, original_code: str):
        self.error_message = error_message
        self.failing_test = failing_test
        self.stack_trace = stack_trace
        self.original_code = original_code

class CodeChanges:
    """
    Holds information about code changes proposed as a fix.
    
    Attributes:
        original_code (str)
        modified_code (str)
    """
    def __init__(self, original_code: str, modified_code: str):
        self.original_code = original_code
        self.modified_code = modified_code

class AIManager:
    """
    Manages AI interactions for generating and validating code fixes.
    
    The AIManager coordinates the generation of code fixes, handles
    multiple strategies if needed, and manages the verification process.
    
    Responsibilities:
    - Generation of fixes for test failures
    - Multiple attempt strategies (e.g., adjusting temperature, altering prompt/model)
    - Context management for LLM prompts
    - Verification of generated fixes
    - Fix attempt history tracking
    """
    
    def __init__(self, api_key: str, model: str, max_attempts: int = 3):
        """
        Initialize the AIManager.
        
        Args:
            api_key (str): LLM service API key.
            model (str): The model name/identifier for code generation.
            max_attempts (int): Maximum attempts to generate a valid fix.
        """
        self.api_key = api_key
        self.model = model
        self.max_attempts = max_attempts
        self.attempt_history: List[Dict[str, Any]] = []
    
    async def generate_fix(self, error: TestError, temperature: float) -> CodeChanges:
        """
        Generate a fix for the given test error.
        
        Steps:
        1. Validate input parameters.
        2. Construct a prompt with _construct_prompt.
        3. Attempt to generate a fix by calling _simulate_llm_call.
        4. Validate the generated fix using verify_fix.
        5. If invalid and attempts remain, adjust parameters and retry.
        6. Return the successful CodeChanges if found, else raise CompletionError.
        
        Raises:
            PromptGenerationError: If prompt construction fails.
            CompletionError: If no valid fix is produced after max_attempts.
            ValueError: If temperature or other parameters are invalid.
        """
    
    def _construct_prompt(self, error: TestError) -> Dict[str, Any]:
        """
        Construct the LLM prompt.
        
        The prompt should include instructions to fix the failing test, original code,
        error details, and previous attempt summaries.
        
        Raises:
            PromptGenerationError if mandatory info is missing.
        """
        raise NotImplementedError("_construct_prompt method not implemented yet.")
    
    async def _validate_fix(self, changes: CodeChanges, error: TestError) -> bool:
        """
        Validate that the generated fix meets requirements and fixes the issue.
        
        For simplicity, consider the fix valid if 'valid_fix' is in modified_code.
        
        Raises:
            ValidationError if unexpected issues occur.
        """
    
    async def verify_fix(self, changes: CodeChanges, error: TestError) -> bool:
        """
        Verify the fix by invoking _validate_fix and returning True if valid, else False.
        """
    
    async def apply_fix(self, changes: CodeChanges) -> None:
        """
        Simulate applying the fix. This can be a no-op or logging action.
        """
    
    async def _simulate_llm_call(self, prompt: Dict[str, Any], temperature: float) -> CodeChanges:
        """
        Simulate an LLM call to produce code changes.
        
        Raises:
            CompletionError if simulation fails unexpectedly.
        """
