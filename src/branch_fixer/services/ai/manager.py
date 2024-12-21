# branch_fixer/services/ai/manager.py
from typing import Optional, Dict, Any
from pathlib import Path
import requests  # Changed from aiohttp to requests
from branch_fixer.core.models import TestError, CodeChanges
from typing import Dict, Any
from marvin.client import MarvinClient  # or AsyncMarvinClient if you prefer async


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
    Manages interactions with an AI service for generating test fixes.

    This version works with Marvin's client, which can be configured
    to talk to Ollama or OpenAI (or another LLM service) depending
    on your needs. For Ollama, you typically set 'base_url' to your
    local server endpoint, e.g. 'http://192.168.4.20:11434'.

    Example usage with Ollama:
        manager = AIManager(
            api_key="",  # If needed, or you can pass None
            model="qwen2.5-coder:3b",
            base_url="http://192.168.4.20:11434/api"
        )
        fix = manager.generate_fix(error, temperature=0.0)
    """

    def __init__(
        self,
        api_key: str,
        model: str = "qwen2.5-coder:3b",
        base_url: str = "http://192.168.4.20:11434/api"
    ):
        """
        Initialize AI manager with API credentials or local server.

        Args:
            api_key: For OpenAI usage you can provide an API key. 
                     If talking to Ollama on a local server, 
                     an API key is typically not needed.
            model: Model identifier (for Ollama, something like 'qwen2.5-coder:3b').
            base_url: The API endpoint for your LLM server.
        """
        # Some local checks, feel free to adapt:
        if api_key is None:
            api_key = ""  # Usually not needed for Ollama

        self.api_key = api_key
        self.model = model
        self.base_url = base_url

        # Create a Marvin client.
        # If you need to call asynchronously, use AsyncMarvinClient.
        self.client = MarvinClient(
            api_key=self.api_key,
            base_url=self.base_url,
            # If you'd like a default model, set it here:
            model=self.model
        )

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
            
            
        # Create prompt and get completion

        # Create prompt and get completion
        prompt = self._construct_prompt(error)
        completion_text = self._get_completion(prompt, temperature)
        return self._parse_response(completion_text)

    def _construct_prompt(self, error: TestError) -> Dict[str, Any]:
        """
        Construct AI prompt from error information.

        Returns a dict with 'messages' that Marvin can pass
        to the 'generate_chat' method, or Ollama's /chat endpoint.
        """
        try:
            return {
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a Python testing expert. Fix the failing test "
                            "while maintaining the test's intent."
                        ),
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
                    },
                ]
            }
        except Exception as e:
            raise PromptGenerationError(f"Failed to construct prompt: {str(e)}") from e

    def _get_completion(self, prompt: Dict[str, Any], temperature: float) -> str:
        """
        Make a request to Marvin (which can talk to Ollama or other LLMs) to get completion.
        """
        try:
            # For a single-turn completion. 
            # If you want to stream responses, set stream=True and handle partial chunks.
            response = self.client.generate_chat(
                messages=prompt["messages"],
                model=self.model,       # override if needed
                temperature=temperature,
                stream=False
            )

            # Typical Marvin response is an OpenAI-style ChatCompletion:
            #   response.choices[0].message.content
            return response.choices[0].message.content

        except Exception as e:
            raise CompletionError(f"AI request failed: {str(e)}") from e

    def _parse_response(self, response: str) -> CodeChanges:
        """
        Parse the AI response into a CodeChanges object.
        We expect the text to contain 'Original code:' 
        followed by 'Modified code:' in some shape.
        """
        try:
            original_code = response.split("Original code:")[1].split("Modified code:")[0].strip()
            modified_code = response.split("Modified code:")[1].strip()
            return CodeChanges(original_code=original_code, modified_code=modified_code)
        except (IndexError, AttributeError) as e:
            raise ValueError(f"Failed to parse response: {str(e)}") from e