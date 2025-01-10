#!/bin/bash
set -eo pipefail

# Script Name: analyze_code.sh
# Description: Runs CodeScene (cs), Mypy, and Ruff on a user-provided script file
# and copies combined results to clipboard.

###############################################################################
# 0. Usage & Flag Parsing
###############################################################################

usage() {
    echo "Usage: $0 [--test] /path/to/your/script.py"
    exit 1
}

# Debugging helper
debug_log() {
    echo "DEBUG: $*" >&2
}

# Default: Not in test mode
TEST_MODE=false

# Simple argument parsing
if [ "$#" -eq 0 ]; then
    usage
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --test)
            TEST_MODE=true
            shift
            ;;
        -*)
            echo "Unknown option: $1"
            usage
            ;;
        *)
            FILE_PATH="$1"
            shift
            ;;
    esac
done

# Validate we have a file path
if [[ -z "$FILE_PATH" ]]; then
    echo "Error: A script file path is required."
    usage
fi

if [ ! -f "$FILE_PATH" ]; then
    echo "Error: The file '$FILE_PATH' does not exist."
    exit 1
fi

# Function to find the project root
find_project_root() {
    local path="$1"
    while [[ "$path" != "/" ]]; do
        if [[ -d "$path/.git" ]] || [[ -f "$path/pyproject.toml" ]] || [[ -f "$path/setup.py" ]]; then
            echo "$path"
            return
        fi
        path=$(dirname "$path")
    done
    echo ""
}

PROJECT_ROOT=$(find_project_root "$(dirname "$FILE_PATH")")

if [[ -z "$PROJECT_ROOT" ]]; then
    echo "Error: Could not determine the project root. Ensure your project has a .git directory, pyproject.toml, or setup.py."
    exit 1
fi

debug_log "Project root determined as '$PROJECT_ROOT'."

cd "$PROJECT_ROOT" || { echo "Error: Failed to change directory to '$PROJECT_ROOT'."; exit 1; }

###############################################################################
# 0a. Debug info about the environment and tools
###############################################################################
debug_log "which python -> $(which python || echo 'not found')"
debug_log "Python version -> $(uv run python --version 2>&1 || echo 'Failed to get Python version')"
debug_log "which mypy -> $(uv run which mypy || echo 'Mypy not found')"
debug_log "Mypy version -> $(uv run mypy --version 2>&1 || echo 'Mypy not found')"
debug_log "which cs -> $(uv run which cs || echo 'cs not found')"
debug_log "which ruff -> $(uv run which ruff || echo 'ruff not found')"

# Warn if VIRTUAL_ENV doesn't match .venv
if [ -n "$VIRTUAL_ENV" ] && [[ "$VIRTUAL_ENV" != *".venv"* ]]; then
    echo "warning: \`VIRTUAL_ENV=$VIRTUAL_ENV\` does not match the project environment path \`.venv\` and will be ignored"
fi

# Initialize PYTHONPATH if not set
PYTHONPATH=${PYTHONPATH:-}
# Add PROJECT_ROOT to PYTHONPATH
if [ -z "$PYTHONPATH" ]; then
    PYTHONPATH="$PROJECT_ROOT"
else
    PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
fi
export PYTHONPATH

debug_log "PYTHONPATH set to '$PYTHONPATH'."
debug_log "Current Directory: $(pwd)"

###############################################################################
# 0b. Create temporary directory for outputs
###############################################################################
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

# Final combined output file
COMBINED_OUTPUT="$TEMP_DIR/combined_analysis.txt"
touch "$COMBINED_OUTPUT"

echo "Starting analysis on '$FILE_PATH'..."

###############################################################################
# 1. Run CodeScene
###############################################################################
echo "Running CodeScene..."
if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is not installed or not in PATH. Please install uv and ensure it's accessible."
    exit 1
fi

echo -e "\n=== CODESCENE ANALYSIS ===\n" >> "$COMBINED_OUTPUT"
if ! uv run cs review "$FILE_PATH" --output-format json > "$TEMP_DIR/codescene_results.json"; then
    echo "Warning: CodeScene command failed. Continuing with other checks..."
else
    cat "$TEMP_DIR/codescene_results.json" >> "$COMBINED_OUTPUT"
fi

###############################################################################
# 2. Ensure lxml is installed before running Mypy with --xml-report
###############################################################################
if ! uv run python -c 'import lxml' 2>/dev/null; then
    echo "lxml is not installed. Attempting to install..."
    if ! python -m pip install lxml; then
        echo "Warning: Could not install lxml. Mypy XML reporting might fail."
    fi
fi

###############################################################################
# 3. Run Mypy
###############################################################################
echo "Running Mypy..."
echo -e "\n=== MYPY ANALYSIS ===\n" >> "$COMBINED_OUTPUT"

RELATIVE_PATH=${FILE_PATH#"$PROJECT_ROOT/"}
MYPY_XML_PATH="$TEMP_DIR/mypy_report.xml"

uv run mypy "$FILE_PATH" --pretty --xml-report "$TEMP_DIR" || {
    echo "Note: Mypy found issues (this is normal)."
}

# Extract the specific file's XML content if it exists
if [ -f "$TEMP_DIR/index.xml" ]; then
    cat "$TEMP_DIR/index.xml" >> "$COMBINED_OUTPUT"
fi

###############################################################################
# 4. Run Ruff
###############################################################################
echo "Running Ruff checks and formatting..."
echo -e "\n=== RUFF FIX OUTPUT ===\n" >> "$COMBINED_OUTPUT"

uv run ruff check "$FILE_PATH" > /dev/null 2>&1 || true
uv run ruff check --fix "$FILE_PATH" 2>&1 | tee -a "$COMBINED_OUTPUT" || true
uv run ruff format "$FILE_PATH" > /dev/null 2>&1 || true
uv run ruff check --select I --fix "$FILE_PATH" > /dev/null 2>&1 || true
uv run ruff format "$FILE_PATH" > /dev/null 2>&1 || true

###############################################################################
# 5. Add Prompt (Refactoring or Test Prompt) Depending on Flag
###############################################################################
echo -e "\n=======\nPROMPT:\n**=======**" >> "$COMBINED_OUTPUT"

if [ "$TEST_MODE" = true ]; then
    # Here Document for your test prompt
    cat <<'EOF' >> "$COMBINED_OUTPUT"
# SYSTEM

You are a Python testing expert specializing in writing pytest test cases. You will receive Python function information and create comprehensive test cases following pytest best practices.

## GOALS

1. Create thorough pytest test cases for the given Python function
2. Cover normal operations, edge cases, and error conditions
3. Use pytest fixtures when appropriate
4. Include proper type hints and docstrings
5. Follow pytest naming conventions and best practices

## RULES

1. Always include docstrings explaining test purpose
2. Use descriptive variable names
3. Include type hints for all parameters
4. Create separate test functions for different test cases
5. Use pytest.mark.parametrize for multiple test cases when appropriate
6. Include error case testing with pytest.raises when relevant
7. Add comments explaining complex test logic
8. Follow the standard test_function_name pattern for test names

## CONSTRAINTS

1. Only write valid pytest code
2. Only use standard pytest features and commonly available packages
3. Keep test functions focused and avoid unnecessary complexity
4. Don't test implementation details, only public behavior
5. Don't create redundant tests

## WORKFLOW

1. Analyze the provided function
2. Identify key test scenarios
3. Create appropriate fixtures if needed
4. Write test functions with clear names and docstrings
5. Include multiple test cases and edge cases
6. Add error condition testing
7. Verify all function parameters are tested
8. Add type hints and documentation

## FORMAT

```python
# Test code here
```

# USER

I will provide you with Python function information. Please generate pytest test cases following the above guidelines.

# ASSISTANT

I'll analyze the provided function and create comprehensive pytest test cases following best practices for testing normal behavior, edge cases, and error conditions.

The test code will be properly structured with:
- Clear docstrings explaining test purpose
- Type hints for all parameters
- Appropriate fixtures where needed
- Parametrized tests for multiple cases
- Error case handling
- Meaningful variable names and comments

Let me know if you need any adjustments to the generated test cases.
===
Follow the Pre-test analysis first then write the tests
# Pre-Test Analysis
1. Identify the exact function/code to be tested
   - Copy the target code and read it line by line
   - Note all parameters, return types, and dependencies
   - Mark any async/await patterns
   - List all possible code paths
2. Analyze Infrastructure Requirements
   - Check if async testing is needed
   - Identify required mocks/fixtures
   - Note any special imports or setup needed
   - Check for immutable objects that need special handling
3. Create Test Foundation
   - Write basic fixture setup
   - Test the fixture with a simple case
   - Verify imports work
   - Run once to ensure test infrastructure works
4. Plan Test Cases
   - List happy path scenarios
   - List error cases from function's try/except blocks
   - Map each test to specific lines of code
   - Verify each case tests something unique
5. Write and Verify Incrementally
   - Write one test case
   - Run coverage to verify it hits expected lines
   - Fix any setup issues before continuing
   - Only proceed when each test works
6. Cross-Check Coverage
   - Run coverage report
   - Map uncovered lines to missing test cases
   - Verify edge cases are covered
   - Confirm error handling is tested
7. Final Verification
   - Run full test suite
   - Compare before/after coverage
   - Verify each test targets the intended function
   - Check for test isolation/independence
# Red Flags to Watch For
- Tests that don't increase coverage
- Overly complex test setups
- Tests targeting multiple functions
- Untested fixture setups
- Missing error cases
- Incomplete mock configurations
# Questions to Ask
- Am I actually testing the target function?
- Does each test serve a clear purpose?
- Are the mocks properly configured?
- Have I verified the test infrastructure works?
- Does the coverage report show improvement?
-------
Write pytest code for this code snippet:

EOF

else
    # Here Document for your normal refactoring prompt
    cat <<'EOF' >> "$COMBINED_OUTPUT"
REFACTOR:
=======
The major types of code refactoring mentioned include:

1. **Extract Function**: Extracting code into a function or method (also referred to as Extract Method).
2. **Extract Variable**: Extracting code into a variable.
3. **Inline Function**: The inverse of Extract Function, where a function is inlined back into its calling code.
4. **Inline Variable**: The inverse of Extract Variable, where a variable is inlined back into its usage.
5. **Change Function Declaration**: Changing the names or arguments of functions.
6. **Rename Variable**: Renaming variables for clarity.
7. **Encapsulate Variable**: Encapsulating a variable to manage its visibility.
8. **Introduce Parameter Object**: Combining common arguments into a single object.
9. **Combine Functions into Class**: Grouping functions with the data they operate on into a class.
10. **Combine Functions into Transform**: Merging functions particularly useful with read-only data.
11. **Split Phase**: Organizing modules into distinct processing phases.

These refactorings focus on improving code clarity and maintainability without altering its observable behavior.

For more detailed information, you might consider using tools that could provide further insights or examples related to these refactoring types.

EOF
fi

# Add a final line that indicates the request to show the full code
echo -e "\n====\nFULL CODE:\n====\nshow the full file dont drop comments or existing functionality" >> "$COMBINED_OUTPUT"

###############################################################################
# 6. Add Full Code
###############################################################################
echo -e "\n**====**\nFULL CODE:\n**====**" >> "$COMBINED_OUTPUT"
if [ -f "$FILE_PATH" ]; then
    cat "$FILE_PATH" >> "$COMBINED_OUTPUT"
else
    echo "Error: Could not read analyzed file: $FILE_PATH"
fi

###############################################################################
# 7. Write to local file (always)
###############################################################################
cat "$COMBINED_OUTPUT" > "analysis_results.txt"
echo "Results also saved to analysis_results.txt"

###############################################################################
# 8. Copy to clipboard (no script exit on failure)
###############################################################################
if [[ "$OSTYPE" == "darwin"* ]]; then
    if command -v pbcopy >/dev/null 2>&1; then
        if cat "$COMBINED_OUTPUT" | pbcopy 2>/dev/null; then
            echo "Analysis results copied to clipboard (macOS)."
        else
            echo "Clipboard copy failed with pbcopy."
        fi
    else
        echo "pbcopy not found. Could not copy to clipboard."
    fi
elif command -v xclip >/dev/null 2>&1; then
    if cat "$COMBINED_OUTPUT" | xclip -selection clipboard 2>/dev/null; then
        echo "Analysis results copied to clipboard (Linux - xclip)."
    else
        echo "Clipboard copy failed with xclip."
    fi
elif command -v xsel >/dev/null 2>&1; then
    if cat "$COMBINED_OUTPUT" | xsel --clipboard 2>/dev/null; then
        echo "Analysis results copied to clipboard (Linux - xsel)."
    else
        echo "Clipboard copy failed with xsel."
    fi
else
    echo "Could not copy to clipboard. Please install xclip or xsel on Linux, or run on macOS."
fi

echo "All analyses are complete."
exit 0