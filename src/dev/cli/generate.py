"""
CLI entry point for the ``generate`` subcommand.

Usage
-----
.venv/bin/python -m branch_fixer.main generate --source-path src/mymodule.py

This wires up the GenerationOrchestrator to Click options, then prints
a summary of successful/failed/skipped generation attempts.
"""

import sys
from pathlib import Path

import click

from src.dev.test_generator.generate.optimizer import GenerationOrchestrator
from src.dev.test_generator.generate.strategies.hypothesis import HypothesisStrategy


@click.command("generate")
@click.option(
    "--source-path",
    required=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help="Path to the Python source file to generate tests for.",
)
@click.option(
    "--output-dir",
    default="generated_tests",
    show_default=True,
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help="Directory where generated test files will be written.",
)
@click.option(
    "--strategy",
    default="hypothesis",
    show_default=True,
    type=click.Choice(["hypothesis"], case_sensitive=False),
    help="Test generation strategy to use.",
)
def generate_command(source_path: Path, output_dir: Path, strategy: str) -> None:
    """
    Generate property-based tests for a given Python source file and write them to an output directory.
    
    Parameters:
        source_path (Path): Path to the Python source file to analyze and generate tests for.
        output_dir (Path): Destination directory where generated tests will be written.
        strategy (str): Generation strategy to use; currently only `"hypothesis"` is supported.
    
    Notes:
        Exits the process with status code 1 if the requested strategy is unknown, if the
        `"hypothesis"` CLI is not available (when `strategy` is `"hypothesis"`), or if the
        overall generation request completes with a failure status.
    """

    if strategy == "hypothesis":
        if not HypothesisStrategy.is_available():
            click.echo(
                "Error: 'hypothesis' CLI not found. "
                "Install it with: pip install hypothesis[cli]",
                err=True,
            )
            sys.exit(1)
        strat = HypothesisStrategy()
    else:
        click.echo(f"Unknown strategy: {strategy}", err=True)
        sys.exit(1)

    click.echo(f"Generating tests for: {source_path}")
    click.echo(f"Output directory: {output_dir}")

    orchestrator = GenerationOrchestrator(strategy=strat)
    request = orchestrator.run(source_path, output_dir)

    success = len(request.successful_attempts)
    failed = len(request.failed_attempts)
    skipped = sum(1 for a in request.attempts if a.status == "skipped")

    click.echo(f"\nDone. {success} generated, {failed} failed, {skipped} skipped.")
    if request.status == "failed":
        sys.exit(1)
