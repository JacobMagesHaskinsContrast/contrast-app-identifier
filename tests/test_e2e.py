"""End-to-end tests for application identification agent."""

import os
import pytest
import asyncio
from pathlib import Path


# Mark all tests in this module as e2e
pytestmark = [pytest.mark.asyncio, pytest.mark.e2e]


@pytest.fixture
def mcp_contrast_repo_path():
    """Path to mcp-contrast repository for testing."""
    home = Path.home()
    repo_path = home / "jacob-dev" / "mcp-contrast"

    if not repo_path.exists():
        pytest.skip(f"mcp-contrast repository not found at {repo_path}")

    return str(repo_path)


@pytest.fixture
def test_config(monkeypatch):
    """Configuration for E2E testing."""
    # Use environment variables if available, otherwise use test values
    monkeypatch.setenv("LLM_PROVIDER", os.getenv("LLM_PROVIDER", "bedrock"))
    monkeypatch.setenv("AWS_REGION", os.getenv("AWS_REGION", "us-east-1"))

    # AWS credentials
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", os.getenv("AWS_ACCESS_KEY_ID", "test-key"))
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY", "test-secret"))

    # Contrast credentials
    monkeypatch.setenv("CONTRAST_HOST_NAME", os.getenv("CONTRAST_HOST_NAME", "test.contrastsecurity.com"))
    monkeypatch.setenv("CONTRAST_API_KEY", os.getenv("CONTRAST_API_KEY", "test-api-key"))
    monkeypatch.setenv("CONTRAST_SERVICE_KEY", os.getenv("CONTRAST_SERVICE_KEY", "test-service-key"))
    monkeypatch.setenv("CONTRAST_USERNAME", os.getenv("CONTRAST_USERNAME", "test@test.com"))
    monkeypatch.setenv("CONTRAST_ORG_ID", os.getenv("CONTRAST_ORG_ID", "test-org"))

    from app_identifier.config import Config
    return Config()


def has_valid_contrast_credentials() -> bool:
    """Check if valid Contrast credentials are available."""
    required_vars = [
        "CONTRAST_HOST_NAME",
        "CONTRAST_API_KEY",
        "CONTRAST_SERVICE_KEY",
        "CONTRAST_USERNAME",
        "CONTRAST_ORG_ID",
    ]

    for var in required_vars:
        value = os.getenv(var, "")
        # Check if it's not a test/placeholder value
        if not value or value.startswith("test"):
            return False

    return True


def has_valid_llm_credentials() -> bool:
    """Check if valid LLM provider credentials are available."""
    provider = os.getenv("LLM_PROVIDER", "bedrock")

    if provider == "bedrock":
        access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
        return bool(access_key) and not access_key.startswith("test")
    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        return bool(api_key) and not api_key.startswith("test")
    elif provider == "azure":
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        return bool(endpoint) and bool(api_key)
    elif provider == "gemini":
        api_key = os.getenv("GOOGLE_GEMINI_API_KEY", "")
        return bool(api_key) and not api_key.startswith("test")

    return False


class TestE2EAgentSetup:
    """Tests for end-to-end agent setup."""

    async def test_agent_can_be_created(self, test_config, mcp_contrast_repo_path):
        """Test that agent can be instantiated with all components."""
        from app_identifier.mcp_tools import create_mcp_toolsets
        from app_identifier.providers import get_model
        from app_identifier.dependencies import AgentDependencies

        # Create MCP toolsets
        try:
            toolsets = await asyncio.wait_for(
                create_mcp_toolsets(test_config, mcp_contrast_repo_path),
                timeout=30.0
            )

            assert len(toolsets) == 2, "Should have filesystem and contrast toolsets"
            assert toolsets[0].tool_prefix == "fs_"
            assert toolsets[1].tool_prefix == "contrast_"

        except asyncio.TimeoutError:
            pytest.skip("MCP toolset creation timed out")
        except Exception as e:
            if "docker" in str(e).lower() or "npx" in str(e).lower():
                pytest.skip(f"Required dependency not available: {e}")
            raise

        # Create LLM model
        try:
            model = get_model(test_config)
            assert model is not None
        except Exception as e:
            # Expected to fail with test credentials
            if not has_valid_llm_credentials():
                pytest.skip(f"Valid LLM credentials not available: {e}")
            raise

        # Create dependencies
        deps = AgentDependencies(
            repository_path=mcp_contrast_repo_path,
            debug_mode=test_config.debug_logging,
        )

        assert deps.repository_path == mcp_contrast_repo_path
        assert isinstance(deps.debug_mode, bool)

    async def test_mcp_contrast_repo_structure(self, mcp_contrast_repo_path):
        """Test that mcp-contrast repository has expected structure."""
        repo = Path(mcp_contrast_repo_path)

        # Should be a Maven project
        assert (repo / "pom.xml").exists(), "Should have pom.xml"

        # Should have source directory
        src_dir = repo / "src"
        assert src_dir.exists(), "Should have src directory"

        # Should be a git repository
        assert (repo / ".git").exists(), "Should be a git repository"


@pytest.mark.skipif(
    not has_valid_contrast_credentials() or not has_valid_llm_credentials(),
    reason="Valid Contrast and LLM credentials required for full E2E test"
)
class TestE2EFullExecution:
    """Tests that require valid credentials to run full agent execution."""

    async def test_identify_mcp_contrast_application(self, test_config, mcp_contrast_repo_path):
        """Test full agent execution to identify mcp-contrast application."""
        from app_identifier.main import identify_application

        try:
            result = await asyncio.wait_for(
                identify_application(mcp_contrast_repo_path),
                timeout=test_config.agent_timeout
            )

            # Verify result structure
            assert result is not None
            assert hasattr(result, 'matches')
            assert hasattr(result, 'repository_path')
            assert result.repository_path == mcp_contrast_repo_path

            # Should have at least attempted to find matches
            assert result.matches is not None

            # If we got matches, verify they have expected structure
            if len(result.matches) > 0:
                match = result.matches[0]
                assert hasattr(match, 'application_name')
                assert hasattr(match, 'confidence_score')
                assert hasattr(match, 'reasoning')

                # Confidence should be between 0 and 1
                assert 0 <= match.confidence_score <= 1

        except asyncio.TimeoutError:
            pytest.fail(f"Agent execution timed out after {test_config.agent_timeout}s")
        except Exception as e:
            pytest.fail(f"Agent execution failed: {e}")
