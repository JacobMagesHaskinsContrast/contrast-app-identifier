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
        List of connected MCPToolset instances

    Raises:
        Exception: If MCP server connection fails
    """
    from pydantic_ai.tools.mcp import MCPToolset, StdioServerParameters

    toolsets = []

    # Filesystem MCP Server
    fs_toolset = MCPToolset(
        server=StdioServerParameters(
            command="npx",
            args=[
                "-y",
                "--cache", "/tmp/.npm-cache",
                "--prefer-offline",
                "@modelcontextprotocol/server-filesystem@2025.11.25",
                repo_path,
            ],
        ),
        timeout=120.0,
        tool_prefix="fs_",
    )
    toolsets.append(fs_toolset)

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

    contrast_toolset = MCPToolset(
        server=StdioServerParameters(
            command="docker",
            args=contrast_args,
            env=env,
        ),
        timeout=120.0,
        tool_prefix="contrast_",
    )
    toolsets.append(contrast_toolset)

    if config.debug_logging:
        print("MCP toolsets created successfully", file=__import__('sys').stderr)

    return toolsets
