# Contrast Application Identifier - Project Walkthrough

## The Problem We're Solving

Imagine you're looking at a code repository on GitHub. You know this repository has been scanned by Contrast Security, but you're not sure which Contrast application it corresponds to. Maybe the repository is called "backend-services" but the Contrast application is named "ecommerce-api". Or perhaps the repository has been renamed over time, but the Contrast application name stayed the same.

**The challenge**: How do you automatically figure out which Contrast application matches which repository?

This is where the Contrast Application Identifier comes in. It's an AI agent that looks at a repository, examines Contrast applications, and intelligently determines the best match.

## A User's Journey

Let's follow Sarah, a DevOps engineer, as she uses this tool:

### Sarah's Problem

Sarah has just cloned a repository called `payment-processor` to her laptop. She needs to check its Contrast Security findings, but when she logs into Contrast, she sees dozens of applications. Which one is it?

- Is it "PaymentProcessor"?
- Is it "payment-service"?
- Is it "ecommerce-payments"?
- Or something completely different?

### Using the Tool

Sarah opens her terminal and runs:

```bash
contrast-identify /path/to/payment-processor
```

Behind the scenes, the tool springs into action:

1. **Repository Analysis**: The agent explores Sarah's repository
   - Finds a `pom.xml` file (it's a Java Maven project!)
   - Reads the artifact ID: `payment-processor`
   - Reads the group ID: `com.company.payments`
   - Notes it's a Spring Boot application

2. **Contrast Query**: The agent connects to Contrast Security
   - Searches for applications with similar names
   - Finds 5 potential matches

3. **Intelligent Matching**: The AI agent reasons through the candidates
   - "This one has artifact ID `payment-processor` - exact match!"
   - "This one is tagged 'payments' and written in Java - good signals"
   - "This one is called 'ecommerce-payments' and has the same group ID"

4. **Result**: 30 seconds later, Sarah gets her answer:

```json
{
  "repository_path": "/Users/sarah/payment-processor",
  "matches": [
    {
      "application_name": "payment-processor",
      "application_id": "a1b2c3d4-...",
      "confidence_score": 0.95,
      "reasoning": "Exact match on Maven artifactId 'payment-processor'.
                    Group ID 'com.company.payments' matches application
                    metadata. Language and framework align."
    }
  ]
}
```

Sarah now knows with 95% confidence that this repository corresponds to the "payment-processor" application in Contrast. Problem solved!

## How It Actually Works

Let's peek under the hood to see how this magic happens.

### The Architecture: Three Key Pieces

The system has three main components working together:

#### 1. The Brain (Pydantic AI Agent)

At the heart is a Pydantic AI agent - think of it as a smart assistant that can:
- Read files and understand code structure
- Query APIs and process responses
- Reason about ambiguous situations
- Make decisions with confidence scores

**Why Pydantic AI?**
- Type-safe structured outputs (we always get valid JSON)
- Built-in support for multiple LLM providers (AWS Bedrock, Anthropic, Azure, Gemini)
- Tool integration via Model Context Protocol (MCP)

The agent lives in `src/app_identifier/agent.py` and has a system prompt that tells it:
> "You are an expert at identifying which Contrast Security application corresponds to a given repository by analyzing code structure, configuration files, and application metadata."

#### 2. The Eyes (MCP Servers)

The agent needs to see two things:
- **The repository**: Files, folders, configuration
- **Contrast applications**: What's available, their names, metadata

This is where Model Context Protocol (MCP) comes in. Think of MCP as giving the agent superpowers:

**Filesystem MCP Server** (`fs_` tools):
- Runs via npx and Node.js
- Gives the agent access to read repository files
- The agent can ask: "What's in this directory?" or "Read this pom.xml file"

**Contrast MCP Server** (`contrast_` tools):
- Runs via Docker
- Connects to Contrast Security API
- The agent can ask: "What applications exist?" or "Get details for this app"

Both servers are created in `src/app_identifier/mcp_tools.py` using `MCPServerStdio`:

```python
# Filesystem access
fs_server = MCPServerStdio(
    command="npx",
    args=["@modelcontextprotocol/server-filesystem@2025.11.25", repo_path],
    tool_prefix="fs_",
)

# Contrast API access
contrast_server = MCPServerStdio(
    command="docker",
    args=["run", "-i", "--rm", "contrast/mcp-contrast:latest"],
    env=contrast_credentials,
    tool_prefix="contrast_",
)
```

#### 3. The Configuration (Multi-Provider Support)

Different teams use different LLM providers. Some use AWS Bedrock, others use Anthropic directly, some have Azure OpenAI. The tool supports all of them!

**Provider Factory** (`src/app_identifier/providers.py`):

```python
def get_model(config: Config) -> Model:
    provider = config.llm_provider.lower()

    if provider == "bedrock":
        return BedrockConverseModel(model_name=config.bedrock_model_id)
    elif provider == "anthropic":
        return AnthropicModel(model_name="claude-sonnet-4.5")
    # ... and so on
```

Configuration comes from environment variables (`.env` file), making it easy to use in CI/CD:

```bash
LLM_PROVIDER=bedrock
AWS_REGION=us-east-1
CONTRAST_HOST_NAME=app.contrastsecurity.com
# ... etc
```

### The Flow: Step by Step

Let's trace exactly what happens when you run `contrast-identify /path/to/repo`:

1. **Startup** (`src/app_identifier/main.py`):
   ```python
   async def identify_application(repo_path: str):
       # Load configuration from environment
       config = Config()

       # Create LLM provider
       model = get_model(config)

       # Create MCP toolsets
       toolsets = await create_mcp_toolsets(config, repo_path)

       # Create agent with tools
       agent = create_agent(model, toolsets)
   ```

2. **Agent Invocation**:
   ```python
   # Run the agent with our question
   result = await agent.run(
       "Analyze this repository and identify the matching Contrast application",
       deps=AgentDependencies(repository_path=repo_path)
   )
   ```

3. **Agent Reasoning** (this is the cool part!):

   The agent starts thinking:
   - "I should explore the repository structure"
   - Calls `fs_list_directory` → sees pom.xml, src/, target/
   - "It's a Maven project! Let me read pom.xml"
   - Calls `fs_read_file(pom.xml)` → extracts artifact ID

   - "Now I need to search Contrast applications"
   - Calls `contrast_list_applications` → gets list of apps
   - "Let me check each candidate..."
   - Calls `contrast_get_application_details` for top matches

   - "This one has matching artifact ID and language. High confidence!"
   - Constructs structured response with reasoning

4. **Structured Output**:

   Thanks to Pydantic, the agent's response is automatically validated:

   ```python
   class ApplicationMatch(BaseModel):
       application_name: str
       application_id: str
       confidence_score: float  # Must be 0.0-1.0
       reasoning: str

   class IdentificationResult(BaseModel):
       repository_path: str
       matches: List[ApplicationMatch]
   ```

   If the agent tries to return invalid data (like `confidence_score: "high"`), Pydantic catches it and forces the agent to fix it.

5. **Output**:
   ```python
   # Convert to JSON and print
   print(result.output.model_dump_json(indent=2))
   ```

### Real-World Example: mcp-contrast Repository

Let's see how it handles a real repository. The `mcp-contrast` project is a Java Maven application that provides a Contrast MCP server.

**Repository Structure**:
```
mcp-contrast/
├── pom.xml                    # Maven configuration
│   <artifactId>mcp-contrast</artifactId>
│   <groupId>com.contrastsecurity</groupId>
├── src/main/java/            # Java source code
├── README.md                  # Documentation
└── Dockerfile                 # Docker configuration
```

**Agent's Analysis**:

1. **Repository signals**:
   - Maven project (pom.xml exists)
   - Artifact ID: "mcp-contrast"
   - Group ID: "com.contrastsecurity"
   - Language: Java
   - Has Docker configuration

2. **Contrast applications** (hypothetical):
   - Application A: "mcp-contrast-server" (Java)
   - Application B: "mcp-server" (Python)
   - Application C: "contrast-mcp" (Java)

3. **Agent reasoning**:
   ```
   Application A ("mcp-contrast-server"):
   - Name similarity: HIGH (contains "mcp-contrast")
   - Language match: YES (Java)
   - Artifact ID similarity: HIGH
   → Confidence: 0.85

   Application B ("mcp-server"):
   - Name similarity: MEDIUM
   - Language match: NO (Python vs Java)
   - Artifact ID similarity: LOW
   → Confidence: 0.35

   Application C ("contrast-mcp"):
   - Name similarity: HIGH (reversed word order)
   - Language match: YES (Java)
   - Artifact ID similarity: MEDIUM
   → Confidence: 0.70
   ```

4. **Result**: Application A wins with 85% confidence!

## Testing Strategy: Three Layers

We have a comprehensive testing strategy to ensure reliability:

### Layer 1: Unit Tests (`tests/test_config.py`, `tests/test_models.py`)

These test individual components in isolation:

```python
def test_config_validates_provider():
    """Ensure config rejects invalid LLM providers"""
    with pytest.raises(ValidationError):
        Config(llm_provider="invalid-provider")
```

**What they test**:
- Configuration validation
- Model serialization/deserialization
- Provider factory logic

**Why important**: Catch bugs in individual pieces before they interact.

### Layer 2: Integration Tests (`tests/test_mcp_integration.py`)

These test MCP server connections:

```python
async def test_filesystem_mcp_connection(mock_config, test_repo_path):
    """Verify filesystem MCP server starts and connects"""
    toolsets = await create_mcp_toolsets(mock_config, test_repo_path)

    assert len(toolsets) >= 1
    assert toolsets[0].tool_prefix == "fs_"
```

**What they test**:
- MCP server creation and configuration
- Tool prefix setup
- Graceful handling when npx/docker unavailable

**Why important**: MCP is a critical external dependency. These tests caught the `MCPToolset` vs `MCPServerStdio` bug!

### Layer 3: End-to-End Tests (`tests/test_e2e.py`)

These test the full agent setup against a real repository:

```python
async def test_agent_can_be_created(test_config, mcp_contrast_repo_path):
    """Verify full agent can be instantiated with all components"""
    # Create MCP toolsets
    toolsets = await create_mcp_toolsets(test_config, mcp_contrast_repo_path)

    # Create LLM model
    model = get_model(test_config)

    # Create dependencies
    deps = AgentDependencies(repository_path=mcp_contrast_repo_path)

    # All components work together!
```

**What they test**:
- Full agent setup works end-to-end
- Real repository structure is valid
- Components integrate correctly

**Why important**: Integration tests might pass, but E2E tests verify the whole system works together.

**Smart skipping**: Tests skip gracefully when credentials aren't available:

```python
@pytest.mark.skipif(
    not has_valid_contrast_credentials(),
    reason="Valid Contrast credentials required"
)
async def test_identify_application():
    # Only runs with real credentials
```

## CI/CD: Automated Quality Gates

Every push to GitHub triggers our CI pipeline (`.github/workflows/ci.yml`):

### Job 1: Test Matrix

```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12"]
```

Tests run on three Python versions in parallel:
- Python 3.10 (older, broad compatibility)
- Python 3.11 (stable, widely used)
- Python 3.12 (latest, forward compatibility)

### Job 2: Lint & Quality

```yaml
- name: Run ruff
  run: ruff check src/ tests/ --output-format=github
  continue-on-error: true
```

Runs code quality checks:
- **ruff**: Fast Python linter
- **black**: Code formatter
- **mypy**: Type checker

These continue on error (warnings don't fail the build) but surface issues for review.

### Job 3: Example Usage

```yaml
- name: Show help
  run: contrast-identify --help

- name: Example usage
  run: echo "Example: contrast-identify /path/to/repo"
```

Demonstrates the tool works and provides documentation.

**Why separate jobs?** They run in parallel! Tests complete faster.

## Key Design Decisions

### Why Pydantic AI?

1. **Type Safety**: Pydantic validates all agent outputs
   - No more "confidence: 'very high'" when you need a float
   - Guaranteed valid JSON structure

2. **Multi-Provider**: One codebase, four LLM providers
   - Teams choose their preferred provider
   - Easy to add new providers

3. **Tool Integration**: MCP support built-in
   - Clean separation of concerns
   - Agent focuses on reasoning, tools handle access

### Why MCP (Model Context Protocol)?

1. **Standardization**: Industry standard for AI tool access
   - Filesystem MCP server maintained by Anthropic
   - Contrast MCP server can be reused by other tools

2. **Isolation**: Each tool runs in its own process
   - Filesystem access sandboxed via npx
   - Contrast API access isolated in Docker
   - Security boundaries maintained

3. **Reusability**: Other AI agents can use the same MCP servers
   - Not locked into this specific agent
   - Build an ecosystem

### Why Environment-Based Configuration?

1. **CI/CD Friendly**: GitHub Secrets → environment variables → tool
   ```yaml
   env:
     CONTRAST_API_KEY: ${{ secrets.CONTRAST_API_KEY }}
   ```

2. **No Hardcoded Secrets**: Never commit credentials
   - `.env` file is gitignored
   - `.env.example` shows structure

3. **Flexibility**: Easy to override per-environment
   - Dev, staging, production use different credentials
   - No code changes needed

## Common Scenarios

### Scenario 1: Exact Match

**Repository**: `payment-service`
**Contrast App**: "payment-service"
**Result**: 95% confidence, instant match

The agent finds:
- Exact name match
- Language matches (both Java)
- Artifact ID matches

Easy win!

### Scenario 2: Ambiguous Match

**Repository**: `backend-api`
**Contrast Apps**:
- "backend-api-v2"
- "backend-services"
- "api-backend"

The agent reasons:
- Checks artifact IDs in pom.xml
- Looks for route patterns in code
- Examines package names
- Compares deployment tags

Returns top 2 matches with reasoning for each.

### Scenario 3: No Match

**Repository**: `new-feature-branch`
**Contrast**: No matching applications

The agent:
- Searches thoroughly
- Finds no strong signals
- Returns empty matches with explanation:
  "This repository appears to be a development branch. No deployed Contrast applications found with matching characteristics."

### Scenario 4: Multi-Module Repository

**Repository**: Monorepo with 10 services
**Challenge**: Which service matches which app?

**Future enhancement**: Agent could:
- Detect monorepo structure
- Analyze each module separately
- Return multiple matches for different modules

## What Makes This Tool Special?

### 1. AI Reasoning vs. Simple Matching

Traditional approach:
```python
if repo_name == app_name:
    return "Match!"
else:
    return "No match"
```

This tool's approach:
- Understands synonyms ("api" vs "service")
- Handles variations ("payment-processor" vs "PaymentProcessor")
- Considers multiple signals (name + language + structure)
- Explains its reasoning

### 2. Extensibility

Want to add support for a new LLM provider?

```python
# Add to providers.py
def _create_new_provider(config: Config) -> Model:
    from pydantic_ai.models.new import NewModel
    return NewModel(api_key=config.new_provider_api_key)
```

Want to add a new MCP tool?

```python
# Add to mcp_tools.py
new_server = MCPServerStdio(
    command="your-command",
    args=["your", "args"],
    tool_prefix="new_",
)
```

### 3. Production Ready

- **Error handling**: Timeouts, connection failures, invalid credentials
- **Logging**: Debug mode for troubleshooting
- **Testing**: 14 automated tests + manual testing guide
- **CI/CD**: Automated quality gates on every push
- **Documentation**: README, design doc, testing guide, this walkthrough!

## Using It in Practice

### As a Developer

```bash
# Clone a repo
git clone https://github.com/company/mystery-service

# Identify it
cd mystery-service
contrast-identify .

# Get the app ID, query Contrast for findings
```

### In GitHub Actions

```yaml
- name: Find Contrast Application
  id: identify
  run: |
    result=$(contrast-identify .)
    app_id=$(echo "$result" | jq -r '.matches[0].application_id')
    echo "app_id=$app_id" >> $GITHUB_OUTPUT

- name: Check Vulnerabilities
  run: |
    contrast-cli scan ${{ steps.identify.outputs.app_id }}
```

### As a Script

```python
import subprocess
import json

result = subprocess.run(
    ["contrast-identify", "/path/to/repo"],
    capture_output=True,
    text=True
)

data = json.loads(result.stdout)
if data["matches"]:
    app_id = data["matches"][0]["application_id"]
    print(f"Found application: {app_id}")
```

## The Development Journey

This project went from idea to production-ready in one day, thanks to:

1. **Planning First** (`/istari-plan`):
   - Clear design document
   - Architecture decisions made upfront
   - Test strategy defined

2. **Test-Driven Development** (`/istari-work`):
   - Tests written before/during implementation
   - Caught bugs early (MCPToolset → MCPServerStdio)
   - Refactored with confidence

3. **Quality Gates**:
   - UBS security scanning
   - Multiple code reviews
   - Comprehensive testing

4. **Documentation**:
   - README for users
   - Design doc for developers
   - Testing guide for QA
   - This walkthrough for understanding!

## Future Enhancements

Potential improvements:

1. **Caching**: Remember previous matches to speed up repeated queries
2. **Monorepo Support**: Handle repositories with multiple services
3. **Learning**: Improve matching based on user feedback
4. **Fuzzy Matching**: Better handling of typos and variations
5. **Web Interface**: GUI for non-technical users
6. **Batch Mode**: Process multiple repositories at once

## Conclusion

The Contrast Application Identifier is more than just a name-matching tool. It's an intelligent agent that:

- **Understands context**: Code structure, naming conventions, project types
- **Reasons intelligently**: Combines multiple signals, handles ambiguity
- **Explains itself**: Provides confidence scores and reasoning
- **Integrates easily**: Works with existing tools and workflows
- **Scales**: Multiple LLM providers, MCP standards, CI/CD ready

It transforms a manual, error-prone process (which Contrast app is this?) into an automated, confident answer in seconds.

**From this**:
```
You: *manually searches Contrast for 10 minutes*
You: *tries 3 different application names*
You: *asks team on Slack*
Teammate: "I think it's the 'backend-v2' one?"
You: *still not sure*
```

**To this**:
```bash
$ contrast-identify .
{
  "matches": [{
    "application_name": "backend-v2",
    "confidence_score": 0.92,
    "reasoning": "Exact match on Maven artifactId..."
  }]
}
# Done in 30 seconds, 92% confident!
```

That's the power of AI agents + thoughtful engineering!
