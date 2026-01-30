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
You are an expert at analyzing codebases and matching them to applications in Contrast Security.

Your task: Identify which Contrast Application corresponds to the repository at {repo_path}.

Process:
1. Explore the repository structure and read key files (package.json, pom.xml, build.gradle, README, etc.)
2. Extract project identifiers: name, artifactId, package names, technology stack
3. Search Contrast applications using contrast_search_applications tool
4. Compare repository characteristics with application metadata (name, tags, languages, routes)
5. If multiple candidates exist, use contrast_get_route_coverage to validate (compare extracted routes vs Contrast routes)
6. Return the best match with confidence level

Signals to consider:
- Project name in package.json, pom.xml, or similar config files
- Technology stack (Java/Maven, Node.js/npm, Python, etc.)
- Application name patterns (exact match, substring, similar naming)
- Route/endpoint patterns if available in source code
- Repository structure and conventions

Confidence levels:
- HIGH (>90%): Exact name match + technology match + route validation
- MEDIUM (70-90%): Strong name similarity + technology match
- LOW (<70%): Weak signals, multiple candidates, or missing validation

Always explain your reasoning in detail.
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
        result_type=ApplicationMatch,
        system_prompt=AGENT_INSTRUCTIONS.format(repo_path=repo_path),
        toolsets=toolsets,
        retries=2,
    )

    # Run agent with timeout
    try:
        result = await asyncio.wait_for(
            agent.run(
                user_prompt=(
                    f"Identify the Contrast application that corresponds to "
                    f"the repository at {repo_path}. Analyze the repository "
                    f"structure and files, then search for matching Contrast "
                    f"applications."
                ),
                deps=deps,
            ),
            timeout=config.agent_timeout,
        )

        if config.debug_logging:
            import sys
            print(f"Agent result: {result.data}", file=sys.stderr)
            print(f"Agent usage: {result.usage()}", file=sys.stderr)

        return result.data

    except asyncio.TimeoutError:
        raise TimeoutError(
            f"Agent timed out after {config.agent_timeout}s. "
            f"Consider increasing AGENT_TIMEOUT."
        )
    except Exception as e:
        if config.debug_logging:
            import sys
            import traceback
            print(f"Agent error: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
        raise
