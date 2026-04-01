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
        self.max_retries = max_retries

    @staticmethod
    def _hypothesis_bin() -> str:
        """Return the absolute path to the hypothesis binary in the active venv."""
        return str(Path(sys.executable).parent / "hypothesis")

    @classmethod
    def is_available(cls) -> bool:
        """Return True if the ``hypothesis`` CLI is reachable in the active venv."""
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
        """Run ``hypothesis write`` for *entity*/*variant* and return clean code.

        Retries up to ``self.max_retries`` times (matches original script's
        try_generate_test loop).  Returns None if all attempts fail or produce
        insufficient/unparseable output.
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
        env = self._build_env()
        cmd = f"{self._hypothesis_bin()} write {args}"
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                env=env,
            )
        except Exception:
            return None

        return self._process_result(result)

    @staticmethod
    def _build_env() -> dict:
        env = os.environ.copy()
        env["PYTHONPATH"] = ":".join(sys.path)
        env.setdefault("PYTHONIOENCODING", "utf-8")
        return env

    @staticmethod
    def _process_result(result: subprocess.CompletedProcess) -> Optional[str]:
        if result.returncode == 0 and result.stdout:
            content = result.stdout.strip()
            if len(content) >= _MIN_CONTENT_LENGTH:
                return content
            return None

        if result.stderr and not any(e in result.stderr for e in _KNOWN_ERRORS):
            # Non-trivial failure — caller can log if desired
            pass
        return None
