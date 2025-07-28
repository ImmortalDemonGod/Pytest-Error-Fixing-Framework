# CLI Command Reference

This document provides a complete reference for the command-line interface (CLI) of `pytest-fixer`.

---

## Main Command: `fix`

The primary command for running the test-fixing workflow.

**Usage:**

```bash
python -m src.branch_fixer.main fix [OPTIONS]
```

---

## Command-Line Options

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--api-key` | `STRING` | (env var) | Your LLM provider API key. Can also be set via the `OPENAI_API_KEY` environment variable. **(Required)** |
| `--test-path` | `PATH` | (none) | The specific test file or directory to run fixes on. If not provided, `pytest` will discover tests from the root. |
| `--test-function` | `STRING` | (none) | The specific test function to fix (e.g., `test_add`). Requires `--test-path` to also be set. |
| `--non-interactive`| `FLAG` | `False` | Runs the tool in fully automated mode without prompting the user for decisions. |
| `--max-retries` | `INT` | `3` | The maximum number of times the AI will attempt to fix a single error. |
| `--initial-temp` | `FLOAT` | `0.4` | The initial temperature (randomness) for the AI model's first fix attempt. |
| `--temp-increment` | `FLOAT` | `0.1` | The amount to increase the temperature on each subsequent retry. |
| `--fast-run` | `FLAG` | `False` | A debugging mode that only attempts to fix the *first* failing test it finds, then exits. |
| `--cleanup-only` | `FLAG` | `False` | Skips the fixing workflow and only runs the cleanup process to remove any leftover `fix-...` branches. |
| `--dev-force-success` | `FLAG` | `False` | A development flag that marks all fix attempts as successful without calling the AI, useful for testing the workflow logic. |
| `--help` | `FLAG` | `False` | Show the help message and exit. |

---

## Interactive Mode

When running in interactive mode (the default, without `--non-interactive`), the tool will pause at each failing test and prompt you for an action:

*   **[Y] Attempt AI-based fix:** (Default) Proceeds with the automated AI fixing workflow.
*   **[M] Perform manual fix:** Pauses the tool and allows you to edit the files manually. Press Enter when you are done to re-run the test and verify your fix.
*   **[N] Skip this test:** Skips the current failing test and moves on to the next one.
*   **[Q] Quit fixing tests entirely:** Aborts the entire session and proceeds to cleanup.