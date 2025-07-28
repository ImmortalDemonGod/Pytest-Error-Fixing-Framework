# Quick Start Guide

This guide will get you up and running with `pytest-fixer` in just a few minutes. It assumes you have already completed the [Installation and Setup](./01-installation.md).

---

## Your First Fix: A Step-by-Step Example

Let's walk through a complete end-to-end example of using `pytest-fixer` to automatically fix a failing test.

### 1. Create a Failing Test

First, let's create a simple, predictably failing test file in your project.

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

Now, from the root of the `Pytest-Error-Fixing-Framework` directory, run the `fix` command. We'll use non-interactive mode for a fully automated run.

```bash
python -m src.branch_fixer.main fix --test-path="tests/test_math_operations.py" --non-interactive
```

### 3. Observe the Workflow

The tool will now execute its automated workflow. You will see logs indicating the following steps:

1.  **Test Execution:** `pytest-fixer` runs the test and discovers that `test_add` is failing.
2.  **Error Analysis:** It parses the `pytest` output to understand the `AssertionError`.
3.  **Branch Creation:** It creates a new, isolated Git branch (e.g., `fix-test_math_operations-test_add-xxxxxxxx`) to safely contain the fix.
4.  **AI Fix Generation:** It sends the error context to an LLM and receives a suggested code change.
5.  **Code Application:** It safely applies the fix, changing `return a - b` to `return a + b`.
6.  **Verification:** It re-runs `test_add`, which now passes.
7.  **Cleanup:** It logs the success and deletes the temporary fix branch, leaving your working directory clean.

### 4. Reviewing the Result

While the tool cleans up after itself, the fix has been successfully applied to your local file. You can now commit the corrected code. For more permanent changes, you can configure the tool to automatically create pull requests.

You have successfully used `pytest-fixer` to automate a debugging and fixing cycle!