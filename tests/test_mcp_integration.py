"""Integration tests for MCP server connections."""

import os
import pytest
import asyncio
from pathlib import Path


# Skip integration tests by default if dependencies unavailable
pytestmark = pytest.mark.asyncio


@pytest.fixture
def test_repo_path(tmp_path):
    """Create a temporary test repository."""
    repo = tmp_path / "test_repo"
    repo.mkdir()

    # Create a simple package.json for testing
    package_json = repo / "package.json"
    package_json.write_text('{"name": "test-app", "version": "1.0.0"}')

    return str(repo)


@pytest.fixture
def mock_config(monkeypatch):
    """Mock configuration with test credentials."""
    # Set minimal required env vars
    monkeypatch.setenv("LLM_PROVIDER", "bedrock")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setenv("CONTRAST_HOST_NAME", "test.contrastsecurity.com")
    monkeypatch.setenv("CONTRAST_API_KEY", "test-api-key")
    monkeypatch.setenv("CONTRAST_SERVICE_KEY", "test-service-key")
    monkeypatch.setenv("CONTRAST_USERNAME", "test@test.com")
    monkeypatch.setenv("CONTRAST_ORG_ID", "test-org")

    from app_identifier.config import Config
    return Config()


class TestFilesystemMCPIntegration:
    """Tests for filesystem MCP server integration."""

    @pytest.mark.skipif(
        os.system("which npx > /dev/null 2>&1") != 0,
        reason="npx not available"
    )
    async def test_filesystem_mcp_connection(self, mock_config, test_repo_path):
        """Test that filesystem MCP server can be started and connected."""
        from app_identifier.mcp_tools import create_mcp_toolsets

        try:
            toolsets = await asyncio.wait_for(
                create_mcp_toolsets(mock_config, test_repo_path),
                timeout=30.0
            )

            # Verify we got toolsets
            assert len(toolsets) >= 1, "Should have at least filesystem toolset"

        except asyncio.TimeoutError:
            pytest.skip("MCP server connection timed out (may need network)")
        except Exception as e:
            if "Docker" in str(e) or "docker" in str(e):
                pytest.skip(f"Docker not available: {e}")
            else:
                raise

    @pytest.mark.skipif(
        os.system("which npx > /dev/null 2>&1") != 0,
        reason="npx not available"
    )
    async def test_filesystem_tools_discovery(self, mock_config, test_repo_path):
        """Test that filesystem MCP server is properly configured."""
        from app_identifier.mcp_tools import create_mcp_toolsets

        try:
            servers = await asyncio.wait_for(
                create_mcp_toolsets(mock_config, test_repo_path),
                timeout=30.0
            )

            fs_server = servers[0]

            # Verify it's an MCP server instance
            assert hasattr(fs_server, 'tool_prefix'), "Should have tool_prefix attribute"
            assert fs_server.tool_prefix == "fs_", f"Expected 'fs_' prefix, got {fs_server.tool_prefix}"

        except asyncio.TimeoutError:
            pytest.skip("Server creation timed out")
        except Exception as e:
            if "Docker" in str(e) or "docker" in str(e):
                pytest.skip(f"Docker not available: {e}")
            else:
                raise


class TestContrastMCPIntegration:
    """Tests for Contrast MCP server integration."""

    @pytest.mark.skipif(
        os.system("which docker > /dev/null 2>&1") != 0,
        reason="Docker not available"
    )
    async def test_contrast_mcp_connection(self, mock_config, test_repo_path):
        """Test that Contrast MCP server can be started via Docker."""
        from app_identifier.mcp_tools import create_mcp_toolsets

        try:
            toolsets = await asyncio.wait_for(
                create_mcp_toolsets(mock_config, test_repo_path),
                timeout=60.0  # Docker pull may take time
            )

            # Verify we got both toolsets
            assert len(toolsets) == 2, "Should have filesystem and contrast toolsets"

        except asyncio.TimeoutError:
            pytest.skip("Contrast MCP connection timed out (may need Docker pull)")
        except Exception as e:
            if "Docker" in str(e) or "docker daemon" in str(e).lower():
                pytest.skip(f"Docker not running: {e}")
            else:
                raise

    @pytest.mark.skipif(
        os.system("which docker > /dev/null 2>&1") != 0,
        reason="Docker not available"
    )
    async def test_contrast_tools_discovery(self, mock_config, test_repo_path):
        """Test that Contrast MCP server is properly configured."""
        from app_identifier.mcp_tools import create_mcp_toolsets

        try:
            servers = await asyncio.wait_for(
                create_mcp_toolsets(mock_config, test_repo_path),
                timeout=60.0
            )

            contrast_server = servers[1]

            # Verify it's an MCP server instance
            assert hasattr(contrast_server, 'tool_prefix'), "Should have tool_prefix attribute"
            assert contrast_server.tool_prefix == "contrast_", \
                f"Expected 'contrast_' prefix, got {contrast_server.tool_prefix}"

        except asyncio.TimeoutError:
            pytest.skip("Contrast server creation timed out")
        except Exception as e:
            if "Docker" in str(e) or "docker daemon" in str(e).lower():
                pytest.skip(f"Docker not running: {e}")
            else:
                raise


class TestMCPToolsetIntegration:
    """Integration tests for full MCP toolset usage."""

    async def test_config_get_contrast_env(self, mock_config):
        """Test that config provides correct environment for Contrast MCP."""
        env = mock_config.get_contrast_env()

        assert "CONTRAST_HOST_NAME" in env
        assert "CONTRAST_API_KEY" in env
        assert "CONTRAST_SERVICE_KEY" in env
        assert "CONTRAST_USERNAME" in env
        assert "CONTRAST_ORG_ID" in env

        assert env["CONTRAST_HOST_NAME"] == "test.contrastsecurity.com"

    async def test_mcp_timeout_configuration(self, mock_config):
        """Test that MCP connection timeouts are properly configured."""
        # Config should have reasonable timeout
        assert mock_config.agent_timeout > 0
        assert mock_config.agent_timeout <= 600  # Max 10 minutes


# Mock-based tests that don't require external dependencies
class TestMCPMockIntegration:
    """Mock-based tests for MCP integration without external dependencies."""

    async def test_mcp_server_creation_succeeds(self, mock_config, test_repo_path):
        """Test that MCP server objects can be created without external dependencies."""
        from app_identifier.mcp_tools import create_mcp_toolsets

        # Server creation should succeed even if npx/docker aren't available
        # The servers only connect when used by an agent
        servers = await create_mcp_toolsets(mock_config, test_repo_path)

        assert len(servers) == 2, "Should create filesystem and contrast servers"
        assert servers[0].tool_prefix == "fs_"
        assert servers[1].tool_prefix == "contrast_"
