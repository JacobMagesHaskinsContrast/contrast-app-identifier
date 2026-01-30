"""
Configuration loading from environment variables.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


class Config:
    """Application configuration loaded from environment."""

    # LLM Provider
    llm_provider: str

    # AWS Bedrock
    aws_region: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    bedrock_model_id: Optional[str] = None

    # Azure OpenAI
    azure_openai_endpoint: Optional[str] = None
    azure_openai_api_key: Optional[str] = None
    azure_openai_deployment: Optional[str] = None

    # Anthropic
    anthropic_api_key: Optional[str] = None

    # Google Gemini
    google_api_key: Optional[str] = None
    gemini_model: Optional[str] = None

    # Contrast Security
    contrast_host_name: str
    contrast_api_key: str
    contrast_service_key: str
    contrast_username: str
    contrast_org_id: str

    # Optional
    agent_timeout: int = 300
    debug_logging: bool = False

    def __init__(self):
        """Load configuration from environment variables."""
        # LLM Provider
        self.llm_provider = os.getenv("LLM_PROVIDER", "bedrock")

        # AWS Bedrock
        self.aws_region = os.getenv("AWS_REGION")
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.bedrock_model_id = os.getenv(
            "BEDROCK_MODEL_ID",
            "anthropic.claude-sonnet-4-5-20250929-v1:0"
        )

        # Azure OpenAI
        self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

        # Anthropic
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

        # Google Gemini
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

        # Contrast Security (required)
        self.contrast_host_name = self._require_env("CONTRAST_HOST_NAME")
        self.contrast_api_key = self._require_env("CONTRAST_API_KEY")
        self.contrast_service_key = self._require_env("CONTRAST_SERVICE_KEY")
        self.contrast_username = self._require_env("CONTRAST_USERNAME")
        self.contrast_org_id = self._require_env("CONTRAST_ORG_ID")

        # Optional
        self.agent_timeout = int(os.getenv("AGENT_TIMEOUT", "300"))
        self.debug_logging = os.getenv("DEBUG_LOGGING", "false").lower() == "true"

        # Validate provider-specific config
        self._validate_provider_config()

    def _require_env(self, var_name: str) -> str:
        """Get required environment variable or raise error."""
        value = os.getenv(var_name)
        if not value:
            raise ValueError(
                f"Required environment variable {var_name} is not set. "
                f"Please configure it in .env or environment."
            )
        return value

    def _validate_provider_config(self):
        """Validate that required credentials exist for selected provider."""
        if self.llm_provider == "bedrock":
            if not self.aws_region or not self.aws_access_key_id or not self.aws_secret_access_key:
                raise ValueError(
                    "AWS Bedrock requires: AWS_REGION, AWS_ACCESS_KEY_ID, "
                    "AWS_SECRET_ACCESS_KEY"
                )
        elif self.llm_provider == "azure":
            if not self.azure_openai_endpoint or not self.azure_openai_api_key or not self.azure_openai_deployment:
                raise ValueError(
                    "Azure OpenAI requires: AZURE_OPENAI_ENDPOINT, "
                    "AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT"
                )
        elif self.llm_provider == "anthropic":
            if not self.anthropic_api_key:
                raise ValueError("Anthropic requires: ANTHROPIC_API_KEY")
        elif self.llm_provider == "gemini":
            if not self.google_api_key:
                raise ValueError("Google Gemini requires: GOOGLE_API_KEY")
        else:
            raise ValueError(
                f"Unknown LLM provider: {self.llm_provider}. "
                f"Valid options: bedrock, azure, anthropic, gemini"
            )

    def get_contrast_env(self) -> dict:
        """Get Contrast credentials as environment dict for MCP server."""
        return {
            "CONTRAST_HOST_NAME": self.contrast_host_name,
            "CONTRAST_API_KEY": self.contrast_api_key,
            "CONTRAST_SERVICE_KEY": self.contrast_service_key,
            "CONTRAST_USERNAME": self.contrast_username,
            "CONTRAST_ORG_ID": self.contrast_org_id,
        }
