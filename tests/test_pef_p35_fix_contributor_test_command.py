"""RED test for F19/F74: contributor docs must instruct `.venv/bin/python -m pytest`, not bare `pytest`."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# F19, F74 target only these two files; docs/developer-guide/03-testing-strategy.md is explicitly
# out of scope (plan §10 "UNTOUCHED").
DOC_FILES = [
    REPO_ROOT / "docs" / "developer-guide" / "02-contribution-guide.md",
    REPO_ROOT / "CONTRIBUTING.md",
]

REQUIRED_COMMAND = ".venv/bin/python -m pytest"


def test_contributor_docs_use_venv_qualified_pytest_command():
    for doc_path in DOC_FILES:
        text = doc_path.read_text()
        lines = text.splitlines()

        bare_pytest_lines = [
            i + 1 for i, line in enumerate(lines) if line.strip() == "pytest"
        ]
        assert bare_pytest_lines == [], (
            f"{doc_path} has a bare `pytest` run instruction at line(s) "
            f"{bare_pytest_lines}; contributors must be told to run "
            f"`{REQUIRED_COMMAND}` per CLAUDE.md."
        )

        assert REQUIRED_COMMAND in text, (
            f"{doc_path} does not contain the required '{REQUIRED_COMMAND}' "
            f"test-run instruction."
        )
