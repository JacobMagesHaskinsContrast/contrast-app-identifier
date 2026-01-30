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
    from pydantic_ai.models.bedrock import BedrockModel
    import boto3

    # Create Bedrock client
    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name=config.aws_region,
        aws_access_key_id=config.aws_access_key_id,
        aws_secret_access_key=config.aws_secret_access_key,
    )

    # Return model instance
    return BedrockModel(
        model_name=config.bedrock_model_id,
        client=bedrock_client,
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
