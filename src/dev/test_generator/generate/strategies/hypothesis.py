"""
Hypothesis strategy — infrastructure layer.

Calls ``hypothesis write`` as a subprocess and post-processes the output.
Promotes the subprocess-calling logic from scripts/hypot_test_gen.py
(TestGenerator.run_hypothesis_write / process_hypothesis_result).
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from src.dev.test_generator.core.models import GenerationVariant, TestableEntity
from src.dev.test_generator.generate.templates import build_hypothesis_command
from src.dev.test_generator.output.formatter import fix_generated_code

# Minimum character count for a generated test to be considered non-trivial.
_MIN_CONTENT_LENGTH = 50

# stderr fragments that indicate hypothesis write failed for a known reason
# (entity not inspectable / not callable) — not worth logging as an error.
_KNOWN_ERRORS = (
    "InvalidArgument: Got non-callable",
    "Could not resolve",
    "but it doesn't have a",
)

# Patterns in generated output that make a test permanently Unsatisfiable.
# hypothesis write emits st.nothing() when it cannot build a value for a
# parameter (most commonly `self` on an unbound instance method).  Such
# tests can never run a single example and are worse than no test at all.
_BROKEN_OUTPUT_PATTERNS = ("st.nothing()",)


class HypothesisStrategy:
    """Generate tests using ``hypothesis write`` subprocesses.

    This is the MVP strategy — a direct port of scripts/hypot_test_gen.py
    run_hypothesis_write() into the DDD layer structure.

    Parameters
    ----------
    max_retries:
        Number of times to retry a failing ``hypothesis write`` call before
        giving up (matches the original script's try_generate_test loop).
        Default: 3.
    """

    def __init__(self, max_retries: int = 3) -> None:
        """
        Initialize the strategy with a retry limit for generation attempts.
        
        Parameters:
            max_retries (int): Maximum number of times to retry running `hypothesis write` when generating code; generation will perform at least one attempt even if this value is less than 1.
        """
        self.max_retries = max_retries

    @staticmethod
    def _hypothesis_bin() -> str:
        """
        Get the absolute path to the `hypothesis` executable located next to the active Python interpreter.
        
        Returns:
            path (str): Absolute filesystem path to the `hypothesis` executable.
        """
        return str(Path(sys.executable).parent / "hypothesis")

    @classmethod
    def is_available(cls) -> bool:
        """
        Check whether the `hypothesis` CLI next to the active Python interpreter is available.
        
        Runs `hypothesis --version`; missing binary or a timeout is treated as unavailable.
        
        Returns:
            True if the `hypothesis` executable exists and exits with code 0 for `--version`, False otherwise (including missing binary or timeout).
        """
        try:
            result = subprocess.run(
                [cls._hypothesis_bin(), "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def generate(
        self,
        entity: TestableEntity,
        variant: GenerationVariant,
    ) -> Optional[str]:
        """
        Generate test code for the given entity and variant and return the cleaned output.
        
        Attempts generation up to `max(1, self.max_retries)` times; on the first successful run returns the post-processed code, otherwise returns `None` when all attempts fail or produce rejected output.
        
        Parameters:
            entity (TestableEntity): The target code entity to generate tests for.
            variant (GenerationVariant): The generation variant or configuration to use.
        
        Returns:
            str | None: Cleaned generated test code as a string, or `None` if generation failed or produced insufficient/filtered output.
        """
        args = build_hypothesis_command(entity, variant)
        for _ in range(max(1, self.max_retries)):
            raw = self._run_hypothesis_write(args)
            if raw is not None:
                return fix_generated_code(raw)
        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _run_hypothesis_write(self, args: str) -> Optional[str]:
        """
        Run the `hypothesis write` CLI with the provided argument string and return validated output.
        
        Parameters:
            args (str): Space-separated command-line arguments to append to `hypothesis write`.
        
        Returns:
            Optional[str]: The processed stdout content if the command completed successfully and passed validation; `None` if the binary is missing, the command times out or fails, an OS error occurs, or the output is rejected by validation.
        """
        env = self._build_env()
        cmd = [self._hypothesis_bin(), "write"] + args.split()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=60,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None

        return self._process_result(result)

    @staticmethod
    def _build_env() -> dict:
        """
        Constructs an environment mapping for subprocess execution with a normalized Python path and default encoding.
        
        Returns:
            env (dict): A copy of the current environment with `PYTHONPATH` set to the joined `sys.path` (using `os.pathsep`) and `PYTHONIOENCODING` set to `"utf-8"` if it was not already present.
        """
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(sys.path)
        env.setdefault("PYTHONIOENCODING", "utf-8")
        return env

    @staticmethod
    def _process_result(result: subprocess.CompletedProcess) -> Optional[str]:
        """
        Determine whether a subprocess.CompletedProcess represents acceptable Hypothesis output and, if so, return its cleaned stdout.
        
        Parameters:
            result (subprocess.CompletedProcess): The completed subprocess result from running the Hypothesis CLI.
        
        Returns:
            Optional[str]: Stripped stdout content if the process exited with code 0, the content length is at least _MIN_CONTENT_LENGTH, and the content does not contain any substring from _BROKEN_OUTPUT_PATTERNS; `None` otherwise.
        """
        if result.returncode == 0 and result.stdout:
            content = result.stdout.strip()
            if len(content) < _MIN_CONTENT_LENGTH:
                return None
            # Reject outputs that would produce Unsatisfiable tests
            if any(p in content for p in _BROKEN_OUTPUT_PATTERNS):
                return None
            return content

        if result.stderr and not any(e in result.stderr for e in _KNOWN_ERRORS):
            # Non-trivial failure — caller can log if desired
            pass
        return None
