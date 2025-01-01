#!/bin/bash
set -eo pipefail

# Script Name: analyze_code.sh
# Description: Runs CodeScene (cs), Mypy, and Ruff on a user-provided script file
# and copies combined results to clipboard

usage() {
    echo "Usage: $0 /path/to/your/script.py"
    exit 1
}

# Debugging helper
debug_log() {
    echo "DEBUG: $*" >&2
}

# Ensure exactly one argument is passed
if [ "$#" -ne 1 ]; then
    echo "Error: Exactly one argument (file path) is required."
    usage
fi

FILE_PATH="$1"

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

# Debug info about the environment and tools
debug_log "which python -> $(which python || echo 'not found')"
debug_log "Python version -> $(uv run python --version 2>&1 || echo 'Failed to get Python version')"
debug_log "which mypy -> $(uv run which mypy || echo 'Mypy not found')"
debug_log "Mypy version -> $(uv run mypy --version 2>&1 || echo 'Mypy not found')"
debug_log "which cs -> $(uv run which cs || echo 'cs not found')"
debug_log "which ruff -> $(uv run which ruff || echo 'ruff not found')"

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

# Create temporary directory for outputs
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
# 2. Run Mypy
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
# 3. Run Ruff
###############################################################################
echo "Running Ruff checks and formatting..."
echo -e "\n=== RUFF FIX OUTPUT ===\n" >> "$COMBINED_OUTPUT"

# Run all Ruff commands but only save the fix output
uv run ruff check "$FILE_PATH" > /dev/null 2>&1 || true
uv run ruff check --fix "$FILE_PATH" 2>&1 | tee -a "$COMBINED_OUTPUT" || true
uv run ruff format "$FILE_PATH" > /dev/null 2>&1 || true
uv run ruff check --select I --fix "$FILE_PATH" > /dev/null 2>&1 || true
uv run ruff format "$FILE_PATH" > /dev/null 2>&1 || true

###############################################################################
# 4. Add Refactoring Template
###############################################################################
echo -e "\n=======\nREFACTOR:\n**=======**" >> "$COMBINED_OUTPUT"
if [ -f "/workspaces/Pytest-Error-Fixing-Framework/scripts/Code-Refactoring-Instructions.md" ]; then
    cat "/workspaces/Pytest-Error-Fixing-Framework/scripts/Code-Refactoring-Instructions.md" >> "$COMBINED_OUTPUT"
else
    echo "Warning: Refactoring template not found at: $PROJECT_ROOT/docs/templates/Code Refactoring Instructions.md"
fi

###############################################################################
# 5. Add Full Code
###############################################################################
echo -e "\n**====**\nFULL CODE:\n**====**" >> "$COMBINED_OUTPUT"
if [ -f "$FILE_PATH" ]; then
    cat "$FILE_PATH" >> "$COMBINED_OUTPUT"
else
    echo "Error: Could not read analyzed file: $FILE_PATH"
fi

###############################################################################
# Write to local file (always)
###############################################################################
cat "$COMBINED_OUTPUT" > "analysis_results.txt"
echo "Results also saved to analysis_results.txt"

###############################################################################
# Copy to clipboard (no script exit on failure)
###############################################################################
# We preserve set -eo pipefail, but handle errors manually
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
