"""
Pydantic AI agent for identifying Contrast applications from repositories.
"""

import asyncio
from typing import Optional
from pydantic_ai import Agent
from .config import Config
from .dependencies import AgentDependencies
from .models import ApplicationMatch
from .providers import get_model
from .mcp_tools import create_mcp_toolsets


AGENT_INSTRUCTIONS = """
Match the repository at {repo_path} to a Contrast Security application.

IMPORTANT: Minimize tool calls to reduce cost. Follow this exact order and STOP as soon as you have a match:

STEP 1 - Check for Contrast config (FASTEST PATH):
- Look for contrast_security.yaml or contrast.yaml in repo root
- If found and contains application.name, search Contrast for that exact name and return immediately

STEP 2 - Check project config (if step 1 didn't match):
- Read ONE file: pom.xml (Java), package.json (Node), or pyproject.toml (Python)
- Extract project name/artifactId
- Search Contrast once with that name

STEP 3 - Return result:
- If match found: HIGH confidence
- If no match: Return NOT_FOUND with LOW confidence

DO NOT:
- List directory contents unless necessary
- Read multiple config files
- Make multiple search calls
- Get route coverage (not needed for basic matching)
- Explore source code files

Keep reasoning brief.
"""


async def identify_application(
    config: Config,
    repo_path: str,
) -> Optional[ApplicationMatch]:
    """
    Identify which Contrast application corresponds to the repository.

    Args:
        config: Application configuration
        repo_path: Path to repository to analyze

    Returns:
        ApplicationMatch if found, None if no match

    Raises:
        Exception: If agent execution fails
    """
    # Create LLM model
    model = get_model(config)

    # Create MCP toolsets
    toolsets = await create_mcp_toolsets(config, repo_path)

    # Create agent dependencies
    deps = AgentDependencies(
        repository_path=repo_path,
        debug_mode=config.debug_logging,
    )

    # Create agent with instructions
    agent = Agent(
        model=model,
        deps_type=AgentDependencies,
        output_type=ApplicationMatch,
        system_prompt=AGENT_INSTRUCTIONS.format(repo_path=repo_path),
        mcp_servers=toolsets,
        retries=2,
    )

    # Run agent (no timeout wrapper to avoid Python 3.13 cancel scope issues)
    try:
        result = await agent.run(
            user_prompt=(
                f"Identify the Contrast application that corresponds to "
                f"the repository at {repo_path}. Analyze the repository "
                f"structure and files, then search for matching Contrast "
                f"applications."
            ),
            deps=deps,
        )

        if config.debug_logging:
            import sys
            print(f"Agent result: {result.output}", file=sys.stderr)
            print(f"Agent usage: {result.usage()}", file=sys.stderr)

        return result.output

    except Exception as e:
        if config.debug_logging:
            import sys
            import traceback
            print(f"Agent error: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
        raise
