"""
Output models for application identification results.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ApplicationMatch(BaseModel):
    """Structured output for identified application."""

    application_id: str = Field(description="Contrast Application ID (UUID)")
    application_name: str = Field(description="Application display name in Contrast")
    confidence: str = Field(
        description="Confidence level: HIGH, MEDIUM, LOW"
    )
    reasoning: str = Field(
        description="Explanation of why this application was selected"
    )
    metadata: dict = Field(
        description="Additional app metadata (tags, language, etc.)"
    )


class IdentificationResult(BaseModel):
    """Top-level result structure."""

    success: bool
    repository_path: str
    match: Optional[ApplicationMatch] = None
    error: Optional[str] = None
    execution_time_ms: float
