#!/usr/bin/env python3
"""
CLI entry point for Contrast Application Identifier.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import click

from .agent import identify_application
from .config import Config
from .models import IdentificationResult


@click.command()
@click.argument(
    "repo_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=".",
)
@click.option(
    "--provider",
    type=click.Choice(["azure", "anthropic", "bedrock", "gemini"], case_sensitive=False),
    help="LLM provider to use (overrides LLM_PROVIDER env var)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False),
    help="Output JSON file (default: stdout)",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging to stderr",
)
def main(
    repo_path: str,
    provider: Optional[str],
    output: Optional[str],
    debug: bool,
):
    """
    Identify which Contrast Security application corresponds to a repository.

    REPO_PATH: Path to repository to analyze (default: current directory)
    """
    # Convert to absolute path
    repo_path = str(Path(repo_path).resolve())

    # Override provider if specified
    if provider:
        os.environ["LLM_PROVIDER"] = provider

    # Override debug if specified
    if debug:
        os.environ["DEBUG_LOGGING"] = "true"

    # Load configuration
    try:
        config = Config()
    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)

    # Run identification
    start_time = time.time()
    result = asyncio.run(_run_identification(config, repo_path))
    execution_time_ms = (time.time() - start_time) * 1000

    # Build result object
    result_obj = IdentificationResult(
        success=result is not None,
        repository_path=repo_path,
        match=result,
        error=None if result else "No matching Contrast application found",
        execution_time_ms=execution_time_ms,
    )

    # Output JSON
    json_output = result_obj.model_dump_json(indent=2)

    if output:
        Path(output).write_text(json_output)
        if config.debug_logging:
            click.echo(f"Result written to {output}", err=True)
    else:
        click.echo(json_output)

    # Exit code
    sys.exit(0 if result else 2)


async def _run_identification(config: Config, repo_path: str):
    """
    Run agent identification with error handling.

    Returns:
        ApplicationMatch if found, None otherwise
    """
    try:
        return await identify_application(config, repo_path)
    except TimeoutError as e:
        click.echo(f"Error: {e}", err=True)
        return None
    except Exception as e:
        click.echo(f"Error during identification: {e}", err=True)
        if config.debug_logging:
            import traceback
            traceback.print_exc(file=sys.stderr)
        return None


if __name__ == "__main__":
    main()
