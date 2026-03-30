# Quick Start Guide

This guide will get you up and running with `pytest-fixer` in just a few minutes. It assumes you have already completed the [Installation and Setup](./01-installation.md).

---

## Your First Fix: A Step-by-Step Example

Let's walk through a complete end-to-end example of using `pytest-fixer` to automatically fix a failing test.

### 1. Create a Failing Test

Create a file named `tests/test_math_operations.py` with the following content:

```python
# tests/test_math_operations.py

def add(a, b):
    # A buggy implementation
    return a - b

def test_add():
    """This test will fail because of the bug in add()."""
    assert add(2, 3) == 5
```

### 2. Run the Fixer

From the root of the `Pytest-Error-Fixing-Framework` directory, load your environment and run the `fix` command:

```bash
set -a && source .env && set +a
.venv/bin/python -m branch_fixer.main fix --test-path tests/test_math_operations.py --non-interactive
```

### 3. Observe the Workflow

The tool will execute its automated workflow. You will see logs indicating the following steps:

1.  **Test Execution:** `pytest-fixer` runs the test and discovers that `test_add` is failing.
2.  **Error Analysis:** It parses the failure to understand the `AssertionError`.
3.  **Branch Creation:** It creates a new, isolated Git branch (e.g., `fix-test_math_operations-test_add-xxxxxxxx`) to safely contain the fix.
4.  **AI Fix Generation:** It sends the error context to an LLM and receives a suggested code change.
5.  **Code Application:** It safely applies the fix, changing `return a - b` to `return a + b`.
6.  **Verification:** It re-runs `test_add`, which now passes.
7.  **Cleanup:** It logs the success and cleans up.

### 4. Reviewing the Result

The fix has been applied to your local file. The tool creates a Git branch containing the fix — you can review it, push it, or open a pull request from it.

You have successfully used `pytest-fixer` to automate a debugging and fixing cycle!
