"""
Pydantic AI agent for identifying Contrast applications from repositories.
"""

from typing import Optional

from pydantic_ai import Agent, UsageLimits
from pydantic_ai.messages import ModelMessage

from .config import Config
from .dependencies import AgentDependencies
from .models import ApplicationMatch
from .providers import get_model
from .mcp_tools import create_mcp_toolsets

# Context management constants
MAX_MESSAGES_BEFORE_TRIM = 20  # Trim history when message count exceeds this
MESSAGES_TO_KEEP_AFTER_TRIM = 10  # Keep last N messages after trimming
MAX_MODEL_REQUESTS = 10  # Maximum model round-trips per run
MAX_TOOL_CALLS = 15  # Maximum tool invocations per run


def trim_old_messages(
    messages: list[ModelMessage],
) -> list[ModelMessage]:
    """
    Trim message history when it grows too long.

    Keeps the first message (system context) plus the most recent messages
    to maintain conversation coherence while managing context size.
    """
    if len(messages) > MAX_MESSAGES_BEFORE_TRIM:
        return messages[:1] + messages[-MESSAGES_TO_KEEP_AFTER_TRIM:]
    return messages


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

    # Create agent with instructions and context management
    agent = Agent(
        model=model,
        deps_type=AgentDependencies,
        output_type=ApplicationMatch,
        system_prompt=AGENT_INSTRUCTIONS.format(repo_path=repo_path),
        mcp_servers=toolsets,
        retries=2,
        history_processors=[trim_old_messages],
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
            usage_limits=UsageLimits(
                request_limit=MAX_MODEL_REQUESTS,
                tool_calls_limit=MAX_TOOL_CALLS,
            ),
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
