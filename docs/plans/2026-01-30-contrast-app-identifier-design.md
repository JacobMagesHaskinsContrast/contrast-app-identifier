# Contrast Application Identifier - Design Document

**Date**: 2026-01-30
**Author**: AI-assisted design session
**Status**: Approved for implementation

## Overview

The Contrast Application Identifier is a Pydantic AI agent that automatically identifies which Contrast Security application corresponds to a given code repository. It uses LLM reasoning to analyze repository structure, configuration files, and Contrast application metadata to determine the best match.

## Problem Statement

When working with multiple repositories and Contrast applications, it's challenging to programmatically determine which Contrast application corresponds to which repository. This is needed for:
- Automated security workflows in GitHub Actions
- Routing security findings to the correct team
- Validating repository-application associations
- Auto-tagging repositories with Contrast metadata

## Goals

1. **Accurate matching**: Identify the correct Contrast application with high confidence
2. **LLM-driven inference**: Use AI reasoning to handle ambiguous cases and multiple signals
3. **Multi-provider support**: Work with Azure OpenAI, Anthropic, AWS Bedrock, and Google Gemini
4. **GitHub workflow ready**: Run in CI/CD pipelines with Docker-based dependencies
5. **Structured output**: JSON output for programmatic consumption

## Non-Goals

- Real-time monitoring or continuous scanning
- Direct code modification or remediation
- Support for non-MCP Contrast integrations
- GUI or web interface

## Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI Entry Point                         │
│                       (main.py)                              │
└───────────────┬─────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agent Orchestrator                        │
│                      (agent.py)                              │
│  - Creates Pydantic AI agent                                 │
│  - Registers MCP toolsets                                    │
│  - Executes identification workflow                          │
└────┬──────────────────────────────────────────────┬─────────┘
     │                                                │
     ▼                                                ▼
┌─────────────────────┐                  ┌──────────────────────┐
│  LLM Provider       │                  │  MCP Toolsets        │
│  Factory            │                  │  (mcp_tools.py)      │
│  (providers.py)     │                  │                      │
│  - Azure OpenAI     │                  │  - Filesystem MCP    │
│  - Anthropic        │                  │  - Contrast MCP      │
│  - AWS Bedrock      │                  │                      │
│  - Google Gemini    │                  │                      │
└─────────────────────┘                  └──────────────────────┘
```

### Component Details

#### 1. CLI Entry Point (`main.py`)

**Responsibilities**:
- Parse command-line arguments (repository path, provider, output file, debug mode)
- Load configuration from environment variables
- Orchestrate agent execution
- Format and output JSON results
- Handle top-level errors and exit codes

**Interface**:
```bash
contrast-identify [OPTIONS] [REPO_PATH]

Options:
  --provider TEXT     LLM provider (azure, anthropic, bedrock, gemini)
  --output FILE       Output JSON file (default: stdout)
  --debug            Enable debug logging
  --help             Show help message
```

#### 2. Agent Configuration (`agent.py`)

**Responsibilities**:
- Create Pydantic AI Agent instance
- Configure agent instructions (system prompt)
- Register MCP toolsets
- Define structured output type (ApplicationMatch)
- Handle streaming and retries

**System Prompt**:
```
You are an expert at analyzing codebases and matching them to applications
in Contrast Security.

Your task: Identify which Contrast Application corresponds to the repository
at {repo_path}.

Process:
1. Explore the repository structure and read key files (package.json, pom.xml,
   build.gradle, README, etc.)
2. Extract project identifiers: name, artifactId, package names, technology stack
3. Search Contrast applications using search_applications tool
4. Compare repository characteristics with application metadata (name, tags,
   languages, routes)
5. If multiple candidates, use route coverage data to validate (compare
   extracted routes vs Contrast routes)
6. Return the best match with confidence level

Signals to consider:
- Project name in package.json, pom.xml, or similar
- Technology stack (Java/Maven, Node.js/npm, Python, etc.)
- Application name patterns (exact match, substring, similar)
- Route/endpoint patterns if available
- Repository structure and conventions

Always explain your reasoning in the analysis.
```

#### 3. LLM Provider Factory (`providers.py`)

**Responsibilities**:
- Factory pattern for instantiating LLM providers
- Environment-based configuration
- Provider-specific error handling
- Unified interface: `get_model(provider_name: str) -> Model`

**Supported Providers**:

**Azure OpenAI**:
- Environment: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`
- Model initialization: Uses Azure-specific endpoint and deployment name

**Anthropic**:
- Environment: `ANTHROPIC_API_KEY`
- Model initialization: Direct API access to Claude models

**AWS Bedrock** (Primary target):
- Environment: `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `BEDROCK_MODEL_ID`
- Model initialization: Uses boto3 Bedrock client
- Default model: `anthropic.claude-sonnet-4-5-20250929-v1:0`

**Google Gemini**:
- Environment: `GOOGLE_API_KEY`, `GEMINI_MODEL`
- Model initialization: Vertex AI or direct API
- Default model: `gemini-1.5-pro`

#### 4. MCP Toolsets (`mcp_tools.py`)

**Filesystem MCP Server**:
- **Connection**: Spawns `npx @modelcontextprotocol/server-filesystem` as subprocess
- **Command**: `npx -y --cache /tmp/.npm-cache --prefer-offline @modelcontextprotocol/server-filesystem@2025.11.25 <repo-path>`
- **Scope**: Limited to repository directory for security
- **Tools provided**: `read_file`, `list_directory`, `search_files`
- **Timeouts**: 120s connection, 30s tool calls

**Contrast MCP Server**:
- **Connection**: Spawns Docker container via stdio
- **Command**: `docker run -i --rm contrast/mcp-contrast:latest -t stdio`
- **Environment variables**: `CONTRAST_HOST_NAME`, `CONTRAST_API_KEY`, `CONTRAST_SERVICE_KEY`, `CONTRAST_USERNAME`, `CONTRAST_ORG_ID`
- **Tools provided**: `search_applications`, `get_application`, `get_route_coverage`, `get_session_metadata`
- **Docker image**: `contrast/mcp-contrast:latest` (from Docker Hub)

**Tool Prefixing**:
- Filesystem tools: `fs_*` prefix
- Contrast tools: `contrast_*` prefix
- Prevents naming conflicts between toolsets

#### 5. Dependencies & Context (`dependencies.py`)

**AgentDependencies dataclass**:
```python
@dataclass
class AgentDependencies:
    """Dependencies injected into agent tools and prompts."""
    repository_path: str
    contrast_credentials: dict
    mcp_filesystem_handle: Any
    mcp_contrast_handle: Any
    debug_mode: bool = False
```

#### 6. Configuration (`config.py`)

**Environment Variables**:
```bash
# LLM Provider Selection
LLM_PROVIDER=bedrock  # Options: azure, anthropic, bedrock, gemini

# AWS Bedrock (when LLM_PROVIDER=bedrock)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-5-20250929-v1:0

# Azure OpenAI (when LLM_PROVIDER=azure)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=gpt-4

# Anthropic (when LLM_PROVIDER=anthropic)
ANTHROPIC_API_KEY=...

# Google Gemini (when LLM_PROVIDER=gemini)
GOOGLE_API_KEY=...
GEMINI_MODEL=gemini-1.5-pro

# Contrast Security
CONTRAST_HOST_NAME=example.contrastsecurity.com
CONTRAST_API_KEY=...
CONTRAST_SERVICE_KEY=...
CONTRAST_USERNAME=user@example.com
CONTRAST_ORG_ID=...

# Optional
AGENT_TIMEOUT=300  # seconds
DEBUG_LOGGING=false
```

#### 7. Output Models (`models.py`)

**Pydantic Models**:
```python
class ApplicationMatch(BaseModel):
    """Structured output for identified application."""
    application_id: str = Field(description="Contrast Application ID (UUID)")
    application_name: str = Field(description="Application display name")
    confidence: str = Field(description="Confidence level: HIGH, MEDIUM, LOW")
    reasoning: str = Field(description="Explanation of selection")
    metadata: dict = Field(description="Additional app metadata")

class IdentificationResult(BaseModel):
    """Top-level result structure."""
    success: bool
    repository_path: str
    match: Optional[ApplicationMatch] = None
    error: Optional[str] = None
    execution_time_ms: float
```

## Application Identification Logic

### Execution Flow

**Phase 1: Repository Analysis**
1. Agent uses `fs_list_directory` to explore repository structure
2. Identifies project type (Java/Maven, Node.js, Python, etc.)
3. Reads key configuration files:
   - `package.json` (Node.js)
   - `pom.xml` (Java/Maven)
   - `build.gradle` / `build.gradle.kts` (Java/Gradle)
   - `pyproject.toml` (Python)
   - `README.md` (general info)
4. Extracts project identifiers:
   - Project name
   - Version
   - Technology stack
   - Dependencies
5. Optionally searches for API route patterns:
   - Java: `@GetMapping`, `@PostMapping`, `@RequestMapping`
   - Node.js: `router.get`, `app.post`, Express routes
   - Python: `@app.route`, FastAPI endpoints

**Phase 2: Application Search**
1. Agent uses `contrast_search_applications` with extracted project name
2. Optionally filters by:
   - Technology/language (e.g., `language=Java`)
   - Tags if known
3. Retrieves list of candidate applications with metadata:
   - Application ID
   - Display name and short name
   - Tags
   - Language/technology

**Phase 3: Candidate Evaluation**
1. For each candidate, agent compares:
   - **Name similarity**: Exact match, substring match, Levenshtein distance
   - **Technology match**: Language and framework alignment
   - **Tags/metadata**: Relevance to repository characteristics
2. If multiple strong candidates exist:
   - Agent uses `contrast_get_route_coverage` to fetch route data
   - Compares extracted repository routes vs Contrast routes
   - Route overlap increases confidence score
3. Agent assigns confidence level:
   - **HIGH** (>90%): Exact name match + technology match + route validation
   - **MEDIUM** (70-90%): Strong name similarity + technology match
   - **LOW** (<70%): Weak signals, multiple candidates, or no route validation

**Phase 4: Result Output**
1. Agent returns structured ApplicationMatch with:
   - Best matching application ID and name
   - Confidence level
   - Reasoning (explanation of decision)
   - Application metadata
2. System wraps in IdentificationResult with execution time

### Example Reasoning

**High Confidence Example**:
```
Repository analysis:
- pom.xml artifactId: "mcp-contrast"
- Technology: Java 17, Spring Boot 3.4.5, Maven
- Extracted routes: /api/vulnerabilities, /api/applications

Contrast search results:
- Found 3 applications with "mcp" in name
- "mcp-contrast" exact match on name
- Technology: Java, Spring Boot (matches)
- Route coverage includes /api/vulnerabilities, /api/applications (100% overlap)

Confidence: HIGH
Reasoning: Exact match on artifactId 'mcp-contrast' in pom.xml. Technology
stack (Java/Maven/Spring Boot) matches Contrast application metadata. Route
patterns extracted from codebase match 100% with Contrast route coverage data.
```

## Error Handling

### Connection Errors

**MCP Connection Failures**:
- **Filesystem MCP**: Retry 3 times with exponential backoff (1s, 2s, 4s)
- **Contrast MCP**: Retry 3 times with exponential backoff
- Clear error messages distinguishing which MCP server failed
- Exit code 1 with descriptive JSON error

**Docker Unavailability**:
- Detect Docker daemon not running
- Provide helpful error message: "Docker is required for Contrast MCP server"
- Suggest fallback: Download JAR from releases if Docker unavailable

### API Errors

**Contrast API Errors**:
- 401/403: Invalid credentials → "Authentication failed. Check CONTRAST_API_KEY and CONTRAST_SERVICE_KEY"
- 404: Organization not found → "Organization not found. Check CONTRAST_ORG_ID"
- 429: Rate limiting → Exponential backoff with retry
- 500+: Server error → Retry with backoff

**LLM Provider Errors**:
- Authentication failures per provider (clear error per provider type)
- Quota/rate limit errors → "LLM quota exceeded. Check provider billing/limits"
- Retry transient network failures (configurable retries, default 2)

### Agent Execution Errors

**Timeout Handling**:
- Default timeout: 5 minutes (configurable via `AGENT_TIMEOUT`)
- If timeout reached: Return partial result with LOW confidence
- Error message: "Agent timed out after 300s. Partial result may be inaccurate."

**No Match Found**:
- Success: false
- Error: "No matching Contrast application found. Searched N applications but none matched repository characteristics."
- Exit code 2 (distinct from error exit code 1)

**Debug Logging**:
- `--debug` flag enables agent reasoning logs to stderr
- Shows tool calls, LLM responses, intermediate reasoning
- Does not pollute stdout JSON output

## Output Format

### Success Case

```json
{
  "success": true,
  "repository_path": "/Users/jacob/projects/mcp-contrast",
  "match": {
    "application_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "application_name": "contrast-mcp",
    "confidence": "HIGH",
    "reasoning": "Exact match on artifactId 'mcp-contrast' in pom.xml. Technology stack (Java/Maven/Spring Boot) matches Contrast application metadata. Route patterns extracted from codebase match 100% with Contrast route coverage data.",
    "metadata": {
      "language": "Java",
      "tags": ["backend", "mcp-server"],
      "short_name": "mcp-contrast"
    }
  },
  "execution_time_ms": 4523.45
}
```

### No Match Case

```json
{
  "success": false,
  "repository_path": "/Users/jacob/projects/unknown-repo",
  "match": null,
  "error": "No matching Contrast application found. Searched 15 applications but none matched repository characteristics.",
  "execution_time_ms": 3102.12
}
```

### Error Case

```json
{
  "success": false,
  "repository_path": "/Users/jacob/projects/repo",
  "match": null,
  "error": "Failed to connect to Contrast MCP server: Docker daemon not running",
  "execution_time_ms": 1234.56
}
```

## Project Structure

```
contrast-app-identifier/
├── src/
│   └── app_identifier/
│       ├── __init__.py
│       ├── main.py              # CLI entry point
│       ├── agent.py             # Agent creation & execution
│       ├── providers.py         # LLM provider factory
│       ├── mcp_tools.py         # MCP toolset setup
│       ├── dependencies.py      # AgentDependencies class
│       ├── config.py            # Configuration loading
│       └── models.py            # Pydantic output models
├── tests/
│   ├── test_agent.py
│   ├── test_providers.py
│   ├── test_mcp_integration.py
│   ├── test_e2e.py
│   └── fixtures/
│       ├── mock_repos/          # Test repositories
│       │   ├── java_maven/
│       │   ├── nodejs_npm/
│       │   └── python_poetry/
│       └── vcr_cassettes/       # Recorded API responses
├── docs/
│   └── plans/
│       └── 2026-01-30-contrast-app-identifier-design.md
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── LICENSE
```

## Dependencies

**pyproject.toml**:
```toml
[project]
name = "contrast-app-identifier"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "pydantic-ai[openai,anthropic,bedrock,vertexai,mcp]>=0.1.0",
    "pydantic>=2.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-mock>=3.10",
    "vcrpy>=4.2",
]

[project.scripts]
contrast-identify = "app_identifier.main:main"
```

## Testing Strategy

### Unit Tests

**Provider Factory** (`test_providers.py`):
- Test each LLM provider instantiation with mock credentials
- Verify correct model configuration
- Test error handling for missing credentials
- Mock external API calls

**Configuration** (`test_config.py`):
- Test environment variable loading
- Test missing required variables raise errors
- Test default values

**Models** (`test_models.py`):
- Test Pydantic validation
- Test JSON serialization

### Integration Tests

**MCP Connection** (`test_mcp_integration.py`):
- Test filesystem MCP server connection (requires npx)
- Test Contrast MCP server connection (requires Docker + credentials)
- Mock tests when dependencies unavailable
- Verify tool discovery and invocation

**End-to-End** (`test_e2e.py`):
- Test against known repository (e.g., mcp-contrast repo)
- Verify correct application identification
- Requires: Contrast credentials, LLM provider credentials
- Optional: run only in CI with secrets

### Test Data

**Mock Repositories**:
- Minimal test repos in `tests/fixtures/mock_repos/`:
  - Java/Maven with pom.xml
  - Node.js with package.json
  - Python with pyproject.toml

**Recorded Responses**:
- VCR.py for recording/replaying HTTP interactions
- Deterministic tests without live API calls

## GitHub Workflow Integration

### Example Workflow

```yaml
name: Identify Contrast Application

on:
  workflow_dispatch:
  push:
    branches: [main]

jobs:
  identify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install contrast-app-identifier
        run: |
          pip install git+https://github.com/JacobMagesHaskinsContrast/contrast-app-identifier.git

      - name: Identify application
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
          contrast-identify --output app-match.json
          cat app-match.json

      - name: Upload result
        uses: actions/upload-artifact@v4
        with:
          name: application-match
          path: app-match.json
```

### Use Cases in Workflows

- **Auto-tagging**: Tag repositories with Contrast Application ID
- **Security routing**: Route findings to correct team based on application
- **Validation**: Verify repository matches expected Contrast application
- **Workflow triggering**: Trigger workflows based on application metadata (tags, criticality)

## Security Considerations

### Data Privacy

- **Contrast vulnerability data**: Sensitive information exposed to LLM
- **Repository code**: Source code sent to LLM for analysis
- **Recommendations**:
  - Only use with LLM providers that guarantee data isolation
  - Avoid public consumer LLM sites (ChatGPT, Gemini free tier)
  - Use enterprise services with contractual privacy (AWS Bedrock, Azure OpenAI)
  - Review LLM provider data handling policies

### Credentials Management

- All credentials via environment variables (never hardcoded)
- GitHub Secrets for workflow credentials
- `.env` files excluded from version control (`.gitignore`)
- Provide `.env.example` template

### MCP Server Security

- Filesystem MCP scoped to repository directory only
- Contrast MCP runs in isolated Docker container
- No persistent state or credential storage in containers

## Implementation Plan

### Phase 1: Core Infrastructure
1. Set up repository structure
2. Implement configuration loading (`config.py`)
3. Implement LLM provider factory (`providers.py`)
4. Implement output models (`models.py`)

### Phase 2: MCP Integration
1. Implement MCP toolset setup (`mcp_tools.py`)
2. Test filesystem MCP connection
3. Test Contrast MCP connection via Docker
4. Implement dependency injection (`dependencies.py`)

### Phase 3: Agent Logic
1. Implement agent creation and configuration (`agent.py`)
2. Write system prompt and instructions
3. Implement execution workflow
4. Add retry logic and error handling

### Phase 4: CLI & Output
1. Implement CLI entry point (`main.py`)
2. Add argument parsing
3. Implement JSON output formatting
4. Add debug logging mode

### Phase 5: Testing
1. Write unit tests (providers, config, models)
2. Write integration tests (MCP connections)
3. Write end-to-end tests (full workflow)
4. Set up CI/CD with GitHub Actions

### Phase 6: Documentation & Release
1. Write README with usage examples
2. Document configuration options
3. Create example workflows
4. Prepare for initial release

## Future Enhancements

- **Multi-repository analysis**: Identify applications across multiple repos
- **Confidence tuning**: Machine learning to improve confidence scoring
- **Cache results**: Store previous matches to speed up repeated runs
- **Additional signals**: Git history, commit patterns, contributor analysis
- **Web UI**: Simple web interface for manual verification
- **Contrast metadata enrichment**: Write identified app ID back to repository (git tag, .contrast file)

## Open Questions

None remaining - design approved for implementation.

## References

- [Pydantic AI Documentation](https://ai.pydantic.dev)
- [Pydantic AI Examples](~/jacob-dev/research/pydantic_ai/)
- [Contrast MCP Server](https://github.com/Contrast-Security-OSS/mcp-contrast)
- [MCP Filesystem Server](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem)
- [Contrast AI SmartFix Action](~/jacob-dev/contrast-ai-smartfix-action)
