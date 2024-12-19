#!/bin/bash

# Base directory
BASE_DIR="/Volumes/Totallynotaharddrive/Pytest-Error-Fixing-Framework"
SRC_PYTEST_DIR="$BASE_DIR/src/branch_fixer/services/pytest"
TESTS_DIR="$BASE_DIR/tests"

# Create new directory structure
echo "Creating new directory structure..."
mkdir -p "$TESTS_DIR"/{unit,integration,e2e}/{core,git,pytest,workflow}
mkdir -p "$TESTS_DIR/unit/pytest/parsers"
mkdir -p "$TESTS_DIR/unit/math"
mkdir -p "$TESTS_DIR/fixtures"

# Move unit tests
echo "Moving unit tests..."

# Core unit tests
mv "$TESTS_DIR/domain/test_models.py" "$TESTS_DIR/unit/core/"
mv "$TESTS_DIR/branch_fixer/test_branch_fixer_core_models_GS.py" "$TESTS_DIR/unit/core/"
mv "$TESTS_DIR/domain/test_error.py" "$TESTS_DIR/unit/core/"

# Git unit tests
mv "$TESTS_DIR/branch_fixer/git/test_git_repository.py" "$TESTS_DIR/unit/git/"
mv "$TESTS_DIR/branch_fixer/git/test_branch_manger.py" "$TESTS_DIR/unit/git/"

# Pytest unit tests
mv "$TESTS_DIR/pytest/error_parser/test_collection_parser.py" "$TESTS_DIR/unit/pytest/parsers/"
mv "$TESTS_DIR/pytest/error_parser/test_failure_parser.py" "$TESTS_DIR/unit/pytest/parsers/"
mv "$TESTS_DIR/pytest/test_error_info.py" "$TESTS_DIR/unit/pytest/"
mv "$SRC_PYTEST_DIR/test_fixtures.py" "$TESTS_DIR/unit/pytest/"

# Math unit tests
mv "$TESTS_DIR/test_math_fix.py" "$TESTS_DIR/unit/math/"

# Move integration tests
echo "Moving integration tests..."
mv "$SRC_PYTEST_DIR/test_pytest_runner.py" "$TESTS_DIR/integration/pytest/"
mv "$TESTS_DIR/integration/test_fix_workflow.py" "$TESTS_DIR/integration/workflow/"

# Move E2E tests
echo "Moving E2E tests..."
mv "$SRC_PYTEST_DIR/test_verify_fix_workflow.py" "$TESTS_DIR/e2e/workflow/"

# Move fixtures
echo "Moving fixtures..."
mv "$TESTS_DIR/branch_fixer/git/conftest.py" "$TESTS_DIR/fixtures/git_fixtures.py"
mv "$TESTS_DIR/integration/conftest.py" "$TESTS_DIR/fixtures/integration_fixtures.py"

# Create new conftest.py that imports from fixtures
cat > "$TESTS_DIR/conftest.py" << 'EOF'
"""Global pytest fixtures"""
from tests.fixtures.git_fixtures import *
from tests.fixtures.integration_fixtures import *
EOF

# Cleanup
echo "Cleaning up..."
# Remove empty directories
find "$TESTS_DIR" -type d -empty -delete
# Remove example/sanity tests
rm -f "$TESTS_DIR/test_hello.py"
rm -f "$SRC_PYTEST_DIR/test_simple.py"

echo "Test migration completed!"