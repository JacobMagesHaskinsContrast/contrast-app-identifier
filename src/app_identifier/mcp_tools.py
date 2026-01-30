"""
MCP toolset setup for filesystem and Contrast server integration.
"""

import asyncio
import os
from typing import List
from .config import Config


async def create_mcp_toolsets(config: Config, repo_path: str) -> List:
    """
    Create and connect to MCP servers for filesystem and Contrast access.

    Args:
        config: Application configuration
        repo_path: Repository path to provide filesystem access to

    Returns:
        List of connected MCP server instances

    Raises:
        Exception: If MCP server connection fails
    """
    from pydantic_ai.mcp import MCPServerStdio

    toolsets = []

    # Filesystem MCP Server
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
    toolsets.append(fs_server)

    # Contrast MCP Server (via Docker)
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
    toolsets.append(contrast_server)

    if config.debug_logging:
        import sys
        print("MCP servers created successfully", file=sys.stderr)

    return toolsets
