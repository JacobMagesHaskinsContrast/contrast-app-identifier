"""
MCP toolset setup for filesystem and Contrast server integration.

Tool filtering is applied to reduce token usage - only tools actually used
by the agent are exposed. See docs/mcp-tool-usage-research.md for details.
"""

import os
from typing import List
from .config import Config

# Tools actually used by the agent (based on empirical testing)
# Names include prefix as that's how they appear in tool_def.name
FILESYSTEM_TOOLS = frozenset({
    "fs__search_files",
    "fs__read_text_file",
    "fs__read_multiple_files",
    "fs__list_directory",
})

CONTRAST_TOOLS = frozenset({
    "contrast__search_applications",
})


async def create_mcp_toolsets(config: Config, repo_path: str) -> List:
    """
    Create and connect to MCP servers for filesystem and Contrast access.

    Args:
        config: Application configuration
        repo_path: Repository path to provide filesystem access to

    Returns:
        List of connected MCP server instances (filtered to only needed tools)

    Raises:
        Exception: If MCP server connection fails
    """
    from pydantic_ai.mcp import MCPServerStdio

    toolsets = []

    # Filesystem MCP Server (filtered to only needed tools)
    fs_server = MCPServerStdio(
        command="npx",
        args=[
            "-y",
            "--cache", "/tmp/.npm-cache",
            "--prefer-offline",
            "@modelcontextprotocol/server-filesystem@2025.11.25",
            repo_path,
        ],
        tool_prefix="fs_",
    )
    fs_filtered = fs_server.filtered(
        lambda ctx, tool_def: tool_def.name in FILESYSTEM_TOOLS
    )
    toolsets.append(fs_filtered)

    # Contrast MCP Server via Docker (filtered to only needed tools)
    contrast_env = config.get_contrast_env()
    contrast_args = [
        "run", "-i", "--rm",
        "-e", "CONTRAST_HOST_NAME",
        "-e", "CONTRAST_API_KEY",
        "-e", "CONTRAST_SERVICE_KEY",
        "-e", "CONTRAST_USERNAME",
        "-e", "CONTRAST_ORG_ID",
        "contrast/mcp-contrast:latest",
        "-t", "stdio"
    ]

    # Set environment for subprocess
    env = os.environ.copy()
    env.update(contrast_env)

    contrast_server = MCPServerStdio(
        command="docker",
        args=contrast_args,
        env=env,
        tool_prefix="contrast_",
    )
    contrast_filtered = contrast_server.filtered(
        lambda ctx, tool_def: tool_def.name in CONTRAST_TOOLS
    )
    toolsets.append(contrast_filtered)

    if config.debug_logging:
        import sys
        print("MCP servers created successfully", file=sys.stderr)

    return toolsets
