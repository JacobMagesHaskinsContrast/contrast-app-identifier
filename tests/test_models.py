"""Tests for output models."""

import pytest
from app_identifier.models import ApplicationMatch, IdentificationResult


def test_application_match_serialization():
    """Test ApplicationMatch can be serialized to JSON."""
    match = ApplicationMatch(
        application_id="test-uuid",
        application_name="test-app",
        confidence="HIGH",
        reasoning="Test reasoning",
        metadata={"language": "Python"},
    )

    json_str = match.model_dump_json()
    assert "test-uuid" in json_str
    assert "test-app" in json_str


def test_identification_result_with_match():
    """Test IdentificationResult with successful match."""
    match = ApplicationMatch(
        application_id="test-uuid",
        application_name="test-app",
        confidence="HIGH",
        reasoning="Test",
        metadata={},
    )

    result = IdentificationResult(
        success=True,
        repository_path="/test/path",
        match=match,
        execution_time_ms=1234.56,
    )

    assert result.success
    assert result.match is not None
    assert result.error is None


def test_identification_result_no_match():
    """Test IdentificationResult with no match."""
    result = IdentificationResult(
        success=False,
        repository_path="/test/path",
        error="No match found",
        execution_time_ms=1234.56,
    )

    assert not result.success
    assert result.match is None
    assert result.error == "No match found"
