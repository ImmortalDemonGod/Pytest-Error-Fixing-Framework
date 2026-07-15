"""RED test for finding F20/F54: README.md and execution-flow.md document the
wrong API key environment variable (OPENAI_API_KEY instead of OPENROUTER_API_KEY).
"""
from pathlib import Path

from branch_fixer.utils.run_cli import fix

REPO_ROOT = Path(__file__).resolve().parents[1]


def _real_api_key_envvar() -> str:
    """Ground truth: the envvar the `fix` command's --api-key option actually reads."""
    for param in fix.params:
        if param.name == "api_key":
            return param.envvar
    raise AssertionError("--api-key option not found on `fix` command")


def test_readme_documents_the_real_api_key_envvar():
    envvar = _real_api_key_envvar()
    readme_text = (REPO_ROOT / "README.md").read_text()

    assert envvar in readme_text, (
        f"README.md must instruct users to set {envvar} (the env var the CLI's "
        f"--api-key option actually reads), but it does not appear in README.md"
    )
    assert "OPENAI_API_KEY" not in readme_text, (
        "README.md still tells users to set OPENAI_API_KEY, which the CLI never reads "
        "(the --api-key option only honors OPENROUTER_API_KEY)"
    )


def test_execution_flow_doc_documents_the_real_api_key_envvar():
    envvar = _real_api_key_envvar()
    doc_path = REPO_ROOT / "docs" / "developer-guide" / "04-execution-flow.md"
    doc_text = doc_path.read_text()

    assert envvar in doc_text, (
        f"{doc_path} must show the --api-key option bound to envvar={envvar!r} "
        f"(matching the real source in src/branch_fixer/utils/run_cli.py)"
    )
    assert "OPENAI_API_KEY" not in doc_text, (
        f"{doc_path} still shows envvar='OPENAI_API_KEY', which diverges from the "
        f"real click option definition"
    )
