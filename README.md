# Contrast Application Identifier

A Pydantic AI agent that automatically identifies which Contrast Security application corresponds to a given code repository.

## Overview

This tool uses LLM reasoning to analyze repository structure, configuration files, and Contrast application metadata to determine the best match between a repository and a Contrast application.

## Features

- **Multi-LLM Support**: Works with Azure OpenAI, Anthropic, AWS Bedrock, and Google Gemini
- **Intelligent Matching**: Uses AI reasoning to handle ambiguous cases and multiple signals
- **MCP Integration**: Leverages Model Context Protocol for filesystem and Contrast API access
- **GitHub Workflow Ready**: Designed for CI/CD pipelines with Docker-based dependencies
- **Structured Output**: JSON output for programmatic consumption

## Prerequisites

- Python 3.10 or higher
- Docker (for Contrast MCP server)
- Node.js and npm (for filesystem MCP server)
- Contrast Security API credentials
- LLM provider credentials (AWS Bedrock, Azure OpenAI, Anthropic, or Google Gemini)

## Installation

```bash
# Clone the repository
git clone https://github.com/JacobMagesHaskinsContrast/contrast-app-identifier.git
cd contrast-app-identifier

# Install dependencies
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

## Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and configure your credentials:
   - Set `LLM_PROVIDER` to your preferred provider (bedrock, azure, anthropic, gemini)
   - Add credentials for your chosen LLM provider
   - Add your Contrast Security credentials

## Usage

### Basic Usage

```bash
# Identify application for current directory
contrast-identify

# Specify repository path
contrast-identify /path/to/repo

# Output to file
contrast-identify --output result.json

# Enable debug logging
contrast-identify --debug
```

### Example Output

```json
{
  "success": true,
  "repository_path": "/path/to/repo",
  "match": {
    "application_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "application_name": "my-application",
    "confidence": "HIGH",
    "reasoning": "Exact match on artifactId 'my-app' in pom.xml...",
    "metadata": {
      "language": "Java",
      "tags": ["backend", "api"]
    }
  },
  "execution_time_ms": 4523.45
}
```

### GitHub Workflow Integration

```yaml
- name: Identify Contrast Application
  env:
    LLM_PROVIDER: bedrock
    AWS_REGION: us-east-1
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    CONTRAST_HOST_NAME: ${{ secrets.CONTRAST_HOST_NAME }}
    CONTRAST_API_KEY: ${{ secrets.CONTRAST_API_KEY }}
    CONTRAST_SERVICE_KEY: ${{ secrets.CONTRAST_SERVICE_KEY }}
    CONTRAST_USERNAME: ${{ secrets.CONTRAST_USERNAME }}
    CONTRAST_ORG_ID: ${{ secrets.CONTRAST_ORG_ID }}
  run: |
    pip install git+https://github.com/JacobMagesHaskinsContrast/contrast-app-identifier.git
    contrast-identify --output app-match.json
```

## How It Works

1. **Repository Analysis**: The agent explores the repository structure and reads key configuration files (package.json, pom.xml, etc.)
2. **Application Search**: Searches Contrast applications using extracted project identifiers
3. **Candidate Evaluation**: Compares repository characteristics with application metadata
4. **Result Output**: Returns the best match with confidence level and reasoning

See [Design Document](docs/plans/2026-01-30-contrast-app-identifier-design.md) for detailed architecture.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with debug logging
contrast-identify --debug
```

## Testing

### Automated Tests

The project includes comprehensive test coverage:

```bash
# Run all tests
pytest -v

# Run specific test categories
pytest tests/test_mcp_integration.py  # MCP integration tests
pytest tests/test_e2e.py              # End-to-end tests
pytest -m e2e                          # E2E tests only

# Run with coverage
pytest --cov=app_identifier --cov-report=term-missing
```

### Manual Testing

For manual testing across different repository types (Java/Maven, Node.js, Python), see the [Manual Testing Guide](docs/MANUAL_TESTING.md).

The manual testing guide includes:
- Step-by-step testing procedures
- Test cases for different technology stacks
- Troubleshooting common issues
- Results documentation template

## License

[License details to be added]

## Contributing

[Contribution guidelines to be added]
