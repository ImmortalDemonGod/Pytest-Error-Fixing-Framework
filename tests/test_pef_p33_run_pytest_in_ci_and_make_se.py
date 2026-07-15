"""RED test for finding F32/F28: deploy.yml must gate on pytest; ci.yml's security
job must either hard-fail on CVEs or link a tracking issue.

These are CI workflow YAML files, not importable Python modules, so the "unit under
test" here is the real, on-disk workflow file content, parsed directly — matching the
plan's Layer-A-equivalent for config-only changes (.aiv/plans/pef-p33-run-pytest-in-ci-and-make-se-plan.md §12).
"""

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def test_deploy_workflow_runs_pytest_before_mkdocs_build():
    workflow = yaml.safe_load(DEPLOY_WORKFLOW.read_text())
    steps = workflow["jobs"]["build-and-deploy"]["steps"]

    step_names = [step.get("name", "") for step in steps]
    run_commands = [step.get("run", "") for step in steps]

    pytest_step_indices = [i for i, run in enumerate(run_commands) if "pytest" in run]
    assert pytest_step_indices, (
        "deploy.yml's build-and-deploy job has no step invoking pytest; "
        f"steps found: {step_names}"
    )

    build_step_indices = [
        i for i, run in enumerate(run_commands) if "mkdocs build" in run
    ]
    assert build_step_indices, "deploy.yml no longer builds the docs site with mkdocs build"

    pytest_step = steps[pytest_step_indices[0]]
    assert not pytest_step.get("continue-on-error"), (
        "the pytest step in deploy.yml must not set continue-on-error, otherwise a "
        "failing test suite would not block the deploy"
    )

    assert pytest_step_indices[0] < build_step_indices[0], (
        "pytest must run before mkdocs build so a failing test suite blocks the deploy"
    )


def test_ci_security_job_fails_build_or_links_tracking_issue():
    raw = CI_WORKFLOW.read_text()
    workflow = yaml.safe_load(raw)
    security_job = workflow["jobs"]["security"]

    hard_blocks_cves = not security_job.get("continue-on-error", False)

    security_block_match = re.search(
        r"^\s{2}security:\n(?:.*\n)*?(?=^\s{2}\S.*:\n|\Z)", raw, re.MULTILINE
    )
    assert security_block_match, "could not locate the ci.yml `security:` job block"
    security_block = security_block_match.group(0)

    links_tracking_issue = bool(
        re.search(r"github\.com/[\w.-]+/[\w.-]+/issues/\d+", security_block)
    )

    assert hard_blocks_cves or links_tracking_issue, (
        "ci.yml's security job neither fails the build on CVEs (continue-on-error is "
        "still true) nor links a tracking issue (no github.com/.../issues/<n> "
        "reference found near the job)"
    )
