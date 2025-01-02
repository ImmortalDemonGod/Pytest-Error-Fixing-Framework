# branch_fixer/services/ai/manager.py
from typing import Optional, Dict, List
from litellm import completion
from branch_fixer.core.models import TestError, CodeChanges


class AIManagerError(Exception):
    """Base exception for AI manager errors"""
    pass


class PromptGenerationError(AIManagerError):
    """Raised when prompt construction fails"""
    pass


class CompletionError(AIManagerError):
    """Raised when AI request fails"""
    pass


class AIManager:
    """
    Manages interactions with AI services for generating test fixes.
    Uses LiteLLM to support multiple providers including OpenAI and Ollama.
    
    Example usage with OpenAI:
        manager = AIManager(
            api_key="sk-...",
            model="openai/gpt-4"
        )
    
    Example usage with Ollama:
        manager = AIManager(
            api_key=None,  # Not needed for Ollama
            model="ollama/codellama"
        )
    """

    def __init__(
        self,
        api_key: Optional[str],
        model: str = "openai/gpt-4o-mini",
        base_temperature: float = 0.4,
    ):
        """
        Initialize AI manager.

        Args:
            api_key: API key (optional for some providers like Ollama)
            model: Model identifier in format "provider/model" 
            base_temperature: Default temperature for generations
        """
        self.api_key = api_key
        self.model = model
        self.base_temperature = base_temperature

        # Set API key for providers that need it
        if api_key:
            import os
            provider = model.split('/')[0].lower()
            if provider == 'openai':
                os.environ["OPENAI_API_KEY"] = api_key
            elif provider == 'anthropic':
                os.environ["ANTHROPIC_API_KEY"] = api_key
            # Add other providers as needed

    def generate_fix(self, error: TestError, temperature: float) -> CodeChanges:
        """
        Generate a fix attempt for the given test error.

        Args:
            error: TestError instance containing error details
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            CodeChanges object with suggested fix

        Raises:
            PromptGenerationError: If prompt construction fails
            CompletionError: If AI request fails
            ValueError: If temperature is out of range
        """
        if not 0 <= temperature <= 1:
            raise ValueError("Temperature must be between 0 and 1")

        try:
            # Create messages for chat completion
            messages = self._construct_messages(error)
            
            # Get completion using LiteLLM
            response = completion(
                model=self.model,
                messages=messages,
                temperature=temperature
            )
            
            # Extract completion text
            completion_text = response.choices[0].message.content
            return self._parse_response(completion_text)
            
        except Exception as e:
            raise CompletionError(f"AI request failed: {str(e)}") from e

    def _construct_messages(self, error: TestError) -> List[Dict[str, str]]:
        """
        Construct messages for chat completion.

        Args:
            error: TestError containing error details

        Returns:
            List of message dictionaries for the chat completion API

        Raises:
            PromptGenerationError: If message construction fails
        """
        try:
            return [
                {
                    "role": "system",
                    "content": (
                        "You are a Python testing expert. Fix the failing test "
                        "while maintaining the test's intent. Provide your response "
                        "in the following format:\n"
                        "Original code: [original test code]\n"
                        "Modified code: [fixed test code]"
                    )
                },
                {
                    "role": "user",
                    "content": f"""
Fix this failing test:

Test Function: {error.test_function}
Test File: {error.test_file}
Error Type: {error.error_details.error_type}
Error Message: {error.error_details.message}
Stack Trace: {error.error_details.stack_trace or 'None'}
"""
                }
            ]
        except Exception as e:
            raise PromptGenerationError(f"Failed to construct messages: {str(e)}") from e

    def _parse_response(self, response: str) -> CodeChanges:
        """
        Parse the AI response into a CodeChanges object.
        
        Args:
            response: Raw response text from AI
            
        Returns:
            CodeChanges object with original and modified code
            
        Raises:
            ValueError: If response cannot be parsed
        """
        try:
            original_code = response.split("Original code:")[1].split("Modified code:")[0].strip()
            modified_code = response.split("Modified code:")[1].strip()
            return CodeChanges(original_code=original_code, modified_code=modified_code)
        except (IndexError, AttributeError) as e:
            raise ValueError(f"Failed to parse response: {str(e)}") from e