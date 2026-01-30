"""
LLM provider factory for multi-provider support.
"""

from typing import Any
from pydantic_ai.models import Model
from .config import Config


def get_model(config: Config) -> Model:
    """
    Factory function to create LLM model based on configuration.

    Args:
        config: Application configuration with provider settings

    Returns:
        Configured Model instance for the specified provider

    Raises:
        ValueError: If provider is unknown or credentials are missing
    """
    provider = config.llm_provider.lower()

    if provider == "bedrock":
        return _create_bedrock_model(config)
    elif provider == "azure":
        return _create_azure_model(config)
    elif provider == "anthropic":
        return _create_anthropic_model(config)
    elif provider == "gemini":
        return _create_gemini_model(config)
    else:
        raise ValueError(
            f"Unknown provider: {provider}. "
            f"Valid options: bedrock, azure, anthropic, gemini"
        )


def _create_bedrock_model(config: Config) -> Model:
    """Create AWS Bedrock model."""
    from pydantic_ai.models.bedrock import BedrockConverseModel
    import os

    # Set AWS credentials and region in environment
    if config.aws_access_key_id:
        os.environ["AWS_ACCESS_KEY_ID"] = config.aws_access_key_id
    if config.aws_secret_access_key:
        os.environ["AWS_SECRET_ACCESS_KEY"] = config.aws_secret_access_key
    if config.aws_region:
        os.environ["AWS_DEFAULT_REGION"] = config.aws_region

    # Return model instance
    return BedrockConverseModel(
        model_name=config.bedrock_model_id,
    )


def _create_azure_model(config: Config) -> Model:
    """Create Azure OpenAI model."""
    from pydantic_ai.models.openai import OpenAIModel

    # Azure OpenAI uses OpenAI SDK with azure endpoint
    return OpenAIModel(
        model_name=config.azure_openai_deployment,
        base_url=config.azure_openai_endpoint,
        api_key=config.azure_openai_api_key,
    )


def _create_anthropic_model(config: Config) -> Model:
    """Create Anthropic model."""
    from pydantic_ai.models.anthropic import AnthropicModel

    return AnthropicModel(
        model_name="claude-sonnet-4-5",  # or configurable
        api_key=config.anthropic_api_key,
    )


def _create_gemini_model(config: Config) -> Model:
    """Create Google Gemini model."""
    from pydantic_ai.models.gemini import GeminiModel

    return GeminiModel(
        model_name=config.gemini_model,
        api_key=config.google_api_key,
    )
