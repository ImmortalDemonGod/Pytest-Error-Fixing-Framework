# branch_fixer/services/ai/manager.py
from typing import Optional, Dict, Any
from pathlib import Path
import requests  # Changed from aiohttp to requests
from branch_fixer.core.models import TestError, CodeChanges

class AIManagerError(Exception):
    """Base exception for AI manager errors"""
    pass

class PromptGenerationError(AIManagerError):
    """Raised when prompt construction fails"""
    pass

class CompletionError(AIManagerError):
    """Raised when AI completion fails"""
    pass

class AIManager:
    """Manages interactions with AI service for generating test fixes"""

    def __init__(self, api_key: str, model: str = "gpt-4", 
                base_url: str = "https://api.openai.com/v1"):
        """Initialize AI manager with API credentials.
        
        Args:
            api_key: OpenAI API key
            model: Model identifier (default: gpt-4)
            base_url: API endpoint (default: OpenAI)
            
        Raises:
            ValueError: If api_key is empty or model is invalid
        """
        if not api_key:
            raise ValueError("API key cannot be empty")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def generate_fix(self, error: TestError, temperature: float) -> CodeChanges:
        """Generate a fix attempt for the given test error.
        
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
            
        # Create prompt and get completion
        prompt = self._construct_prompt(error)
        completion = self._get_completion(prompt, temperature)
        
        # Parse and return changes
        return self._parse_response(completion)

    def _construct_prompt(self, error: TestError) -> Dict[str, Any]:
        """Construct AI prompt from error information.
        
        Args:
            error: TestError instance to generate prompt for
            
        Returns:
            Dict containing prompt messages and parameters
            
        Raises:
            PromptGenerationError: If error lacks required information
        """
        try:
            return {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a Python testing expert. Fix the failing test while maintaining the test's intent."
                    },
                    {
                        "role": "user",
                        "content": f"""
Fix this failing test:
Test Function: {error.test_function}
Test File: {error.test_file}
Error Type: {error.error_details.error_type}
Error Message: {error.error_details.message}
Stack Trace: {error.error_details.stack_trace if error.error_details.stack_trace else 'None'}
"""
                    }
                ],
                "model": self.model,
                "response_format": {"type": "text"}
            }
        except Exception as e:
            raise PromptGenerationError(f"Failed to construct prompt: {str(e)}") from e

    def _get_completion(self, prompt: Dict[str, Any], temperature: float) -> str:
        """Make API request to get completion.
        
        Args:
            prompt: Constructed prompt dictionary
            temperature: Sampling temperature
            
        Returns:
            Model completion text
            
        Raises:
            CompletionError: If API request fails
        """
        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": prompt["messages"],
                    "temperature": temperature
                },
                timeout=30
            )
            
            if response.status_code != 200:
                raise CompletionError(f"API request failed: {response.text}")
                
            return response.json()["choices"][0]["message"]["content"]
                
        except requests.RequestException as e:
            raise CompletionError(f"API request failed: {str(e)}") from e

    def _parse_response(self, response: str) -> CodeChanges:
        """Parse AI response into CodeChanges object.
        
        Args:
            response: Raw completion text
            
        Returns:
            CodeChanges object with parsed changes
            
        Raises:
            ValueError: If response cannot be parsed
        """
        try:
            original_code = response.split("Original code:")[1].split("Modified code:")[0].strip()
            modified_code = response.split("Modified code:")[1].strip()
            return CodeChanges(
                original_code=original_code,
                modified_code=modified_code
            )
        except (IndexError, AttributeError) as e:
            raise ValueError(f"Failed to parse response: {str(e)}") from e