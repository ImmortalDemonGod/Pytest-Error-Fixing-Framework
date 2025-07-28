# Contribution Guide

We welcome and appreciate contributions to `pytest-fixer`! This guide outlines the process for contributing to the project, from setting up your environment to submitting a pull request.

---

## 1. Setting Up Your Development Environment

First, follow the [Installation Guide](../user-guide/01-installation.md) to clone the repository and set up the `uv` virtual environment.

---

## 2. The Development Workflow

We follow a standard Git workflow for contributions:

1.  **Create an Issue:** Before starting work, please open a GitHub issue describing the bug you want to fix or the feature you want to add. This allows for discussion and prevents duplicated effort.

2.  **Create a Feature Branch:** Create a new branch for your work, named descriptively.

    ```bash
    # Example for a new feature
    git checkout -b feature/add-anthropic-support

    # Example for a bug fix
    git checkout -b fix/resolve-parsing-error
    ```

3.  **Implement Your Changes:** Write your code, following the architectural principles outlined in the [System Architecture](./01-architecture.md) document. Ensure your code is clean, well-commented, and includes necessary type hints.

---

## 3. Coding Standards and Quality

To maintain code quality, we use `ruff` for linting and formatting.

-   **Formatting:** Before committing, format your code to ensure it meets the project standard.
    ```bash
    ruff format .
    ```
-   **Linting:** Check for any code quality issues.
    ```bash
    ruff check .
    ```

---

## 4. Testing

Comprehensive testing is critical. Your contribution must include tests that cover the changes you've made.

1.  **Add or Update Tests:** Place new tests in the `tests/` directory, mirroring the structure of the `src/` directory.
2.  **Run the Full Test Suite:** Before submitting, run all tests to ensure your changes haven't introduced any regressions.
    ```bash
    pytest
    ```

---

## 5. Submitting a Pull Request

Once your changes are complete and all tests pass:

1.  **Commit Your Changes:** Use a clear and descriptive commit message.

    ```bash
    git commit -m "feat: Add support for Anthropic's Claude 3 models"
    ```

2.  **Push to Your Fork:**

    ```bash
    git push origin feature/add-anthropic-support
    ```

3.  **Open a Pull Request:**
    -   Navigate to the `pytest-fixer` repository on GitHub and open a pull request.
    -   The PR title should be clear and concise.
    -   The description should automatically link to the issue you created (e.g., "Closes #42").
    -   Provide a summary of the changes and any additional context a reviewer might need.

Your PR will be reviewed, and we may request changes before it is merged. Thank you for helping us improve `pytest-fixer`!
