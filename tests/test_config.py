"""Tests for configuration loading."""

import pytest
import os


def test_config_requires_contrast_credentials(monkeypatch):
    """Test that Config raises error when Contrast credentials missing."""
    from app_identifier.config import Config

    # Clear all Contrast env vars
    for var in ["CONTRAST_HOST_NAME", "CONTRAST_API_KEY", "CONTRAST_SERVICE_KEY",
                "CONTRAST_USERNAME", "CONTRAST_ORG_ID"]:
        monkeypatch.delenv(var, raising=False)

    # Set LLM provider to avoid that error
    monkeypatch.setenv("LLM_PROVIDER", "bedrock")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")

    with pytest.raises(ValueError, match="CONTRAST_HOST_NAME"):
        Config()


def test_config_validates_provider(monkeypatch):
    """Test that Config validates provider-specific credentials."""
    from app_identifier.config import Config

    # Set required Contrast vars
    monkeypatch.setenv("CONTRAST_HOST_NAME", "test.com")
    monkeypatch.setenv("CONTRAST_API_KEY", "test")
    monkeypatch.setenv("CONTRAST_SERVICE_KEY", "test")
    monkeypatch.setenv("CONTRAST_USERNAME", "test@test.com")
    monkeypatch.setenv("CONTRAST_ORG_ID", "test")

    # Set invalid provider
    monkeypatch.setenv("LLM_PROVIDER", "invalid")

    with pytest.raises(ValueError, match="Unknown LLM provider"):
        Config()
