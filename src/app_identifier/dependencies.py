"""
Agent dependencies for dependency injection into tools.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class AgentDependencies:
    """Dependencies injected into agent tools and prompts."""

    repository_path: str
    debug_mode: bool = False
