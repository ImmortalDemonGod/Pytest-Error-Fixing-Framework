#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Define the base directory
BASE_DIR="pytest_fixer"

# Create the base directory
mkdir -p "$BASE_DIR"

# List of all files to create within the project
FILES=(
    # Root files
    "$BASE_DIR/README.md"
    "$BASE_DIR/setup.py"
    "$BASE_DIR/requirements.txt"

    # branch_fixer package
    "$BASE_DIR/branch_fixer/__init__.py"
    "$BASE_DIR/branch_fixer/main.py"

    # branch_fixer/pytest package
    "$BASE_DIR/branch_fixer/pytest/__init__.py"
    "$BASE_DIR/branch_fixer/pytest/error_info.py"
    "$BASE_DIR/branch_fixer/pytest/runner.py"

    # branch_fixer/pytest/error_parser package
    "$BASE_DIR/branch_fixer/pytest/error_parser/__init__.py"
    "$BASE_DIR/branch_fixer/pytest/error_parser/collection_parser.py"
    "$BASE_DIR/branch_fixer/pytest/error_parser/failure_parser.py"
    "$BASE_DIR/branch_fixer/pytest/error_parser/summary_parser.py"

    # branch_fixer/git package
    "$BASE_DIR/branch_fixer/git/__init__.py"
    "$BASE_DIR/branch_fixer/git/repo.py"
    "$BASE_DIR/branch_fixer/git/branch_ops.py"
    "$BASE_DIR/branch_fixer/git/pr_ops.py"

    # branch_fixer/utils package
    "$BASE_DIR/branch_fixer/utils/__init__.py"
    "$BASE_DIR/branch_fixer/utils/cli.py"
    "$BASE_DIR/branch_fixer/utils/logging_config.py"
    "$BASE_DIR/branch_fixer/utils/prompt_handler.py"

    # test_generator package
    "$BASE_DIR/test_generator/__init__.py"

    # test_generator/analyze package
    "$BASE_DIR/test_generator/analyze/__init__.py"
    "$BASE_DIR/test_generator/analyze/parser.py"
    "$BASE_DIR/test_generator/analyze/extractor.py"

    # test_generator/generate package
    "$BASE_DIR/test_generator/generate/__init__.py"
    "$BASE_DIR/test_generator/generate/templates.py"
    "$BASE_DIR/test_generator/generate/optimizer.py"

    # test_generator/generate/strategies package
    "$BASE_DIR/test_generator/generate/strategies/__init__.py"
    "$BASE_DIR/test_generator/generate/strategies/hypothesis.py"
    "$BASE_DIR/test_generator/generate/strategies/fabric.py"
    "$BASE_DIR/test_generator/generate/strategies/pynguin.py"

    # test_generator/output package
    "$BASE_DIR/test_generator/output/__init__.py"
    "$BASE_DIR/test_generator/output/writer.py"
    "$BASE_DIR/test_generator/output/formatter.py"

    # shared package
    "$BASE_DIR/shared/__init__.py"
    "$BASE_DIR/shared/git.py"
    "$BASE_DIR/shared/testing.py"
    "$BASE_DIR/shared/logging.py"

    # cli package
    "$BASE_DIR/cli/__init__.py"
    "$BASE_DIR/cli/fix.py"
    "$BASE_DIR/cli/generate.py"

    # tests directories
    "$BASE_DIR/tests/branch_fixer/__init__.py"
    "$BASE_DIR/tests/test_generator/__init__.py"
    "$BASE_DIR/tests/integration/__init__.py"
)

# Iterate through the list and create directories and files
for file in "${FILES[@]}"; do
    dir=$(dirname "$file")
    mkdir -p "$dir"
    touch "$file"
done

echo "Project structure for 'pytest_fixer' has been set up successfully."
echo "Navigate to the '$BASE_DIR' directory to start working on your project."