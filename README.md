# Pytest-Error-Fixing-Framework

[![Continuous Integration](https://github.com/ImmortalDemonGod/pytest-fixer/actions/workflows/ci.yml/badge.svg)](https://github.com/ImmortalDemonGod/pytest-fixer/actions/workflows/ci.yml)
[![Docstring Coverage](https://github.com/ImmortalDemonGod/pytest-fixer/actions/workflows/docstr-coverage.yml/badge.svg)](https://github.com/ImmortalDemonGod/pytest-fixer/actions/workflows/docstr-coverage.yml)
[![MIT License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An AI-powered tool that automatically fixes failing pytest tests by analyzing error output, proposing code changes, and verifying the fix.

## Features

-   **Automated Test Fixing:** Parses pytest error logs to identify failures.
-   **AI-Powered Suggestions:** Uses an AI model to generate code fixes.
-   **Git Integration:** Automatically creates a new branch for the fix.
-   **Iterative Verification:** Reruns tests to confirm the fix is effective.

## Documentation

For full, detailed instructions, please see our official documentation site:

-   **[User Guide](https://immortaldemongod.github.io/Pytest-Error-Fixing-Framework/user-guide/01-installation/)**: For everyone who wants to use the tool.
-   **[Developer Guide](https://immortaldemongod.github.io/Pytest-Error-Fixing-Framework/developer-guide/01-architecture/)**: For everyone who wants to contribute to the tool.

## Development Setup

This project uses [Go Task](https://taskfile.dev) as a standardized task runner for development and automation. All common operations are defined in the `Taskfile.yml`.

### Prerequisites

Before you begin, ensure you have [Go Task](https://taskfile.dev/installation/) installed on your system.

### 1. Clone and Set Up

The `setup` task will create a Python virtual environment, install all required dependencies using `uv`, and prepare the project for use.

```sh
git clone https://github.com/ImmortalDemonGod/pytest-fixer.git
cd pytest-fixer
task setup
```

After setup, activate the virtual environment:

```sh
source .venv/bin/activate
```

### 2. Configure Your API Key

Create a `.env` file in the project root and add your API key.

```sh
echo "OPENAI_API_KEY='your-api-key-here'" > .env
```

### 3. Run the Fixer

You can run the main application using the `run:fix` task. Pass any CLI arguments after `--`.

```sh
task run:fix -- --test-path /path/to/your/tests
```

To see all available tasks, run `task --list-all`.

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for more details on how to get started.

## Known Issues

### Pytest Cleanup Warnings

When running the test suite, you may encounter `PytestWarning` messages related to errors during the removal of temporary directories:

```
PytestWarning: (rm_rf) error removing /private/var/folders/...
OSError: [Errno 66] Directory not empty: ...
```

This is caused by a known issue with `gitpython`, which can leave lingering file handles on `.git` directories, preventing pytest from cleaning them up successfully.

We have investigated this issue extensively and implemented all recommended code-level fixes, including ensuring all `git.Repo` objects are closed and their caches are cleared. However, the warnings persist, suggesting a deeper issue within the library or its interaction with the operating system.

Since all tests pass and this warning does not affect the correctness of the application, we have decided to document it here rather than continue to pursue a fix. The warnings can be safely ignored.
