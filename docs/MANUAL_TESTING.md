# Manual Testing Guide

This guide provides instructions for manually testing the Contrast Application Identifier against different repository types.

## Prerequisites

Before testing, ensure you have:

### 1. Valid Credentials

**LLM Provider** (choose one):
- **AWS Bedrock** (recommended):
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_REGION` (e.g., us-east-1)
- **Anthropic**:
  - `ANTHROPIC_API_KEY`
- **Azure OpenAI**:
  - `AZURE_OPENAI_ENDPOINT`
  - `AZURE_OPENAI_API_KEY`
  - `AZURE_OPENAI_DEPLOYMENT`
- **Google Gemini**:
  - `GOOGLE_GEMINI_API_KEY`

**Contrast Security**:
- `CONTRAST_HOST_NAME` (e.g., app.contrastsecurity.com)
- `CONTRAST_API_KEY`
- `CONTRAST_SERVICE_KEY`
- `CONTRAST_USERNAME`
- `CONTRAST_ORG_ID`

### 2. Test Repositories

Identify repositories of different technology stacks:
- **Java/Maven**: Spring Boot application, Maven-based project
- **Node.js**: Express/React application with package.json
- **Python**: Django/Flask application with requirements.txt or pyproject.toml
- **Other**: Ruby (Gemfile), Go (go.mod), .NET (*.csproj), etc.

## Testing Procedure

### Setup

1. **Install the tool**:
   ```bash
   cd contrast-app-identifier
   pip install -e .
   ```

2. **Configure environment**:
   ```bash
   # Copy and edit .env file
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Verify installation**:
   ```bash
   contrast-identify --help
   ```

### Test Cases

#### Test 1: Java/Maven Repository

**Example Repository**: `mcp-contrast` (Java/Maven MCP server)

1. **Run identification**:
   ```bash
   contrast-identify ~/path/to/java-repo
   ```

2. **Expected behavior**:
   - ✅ Agent detects Maven project (pom.xml)
   - ✅ Agent reads Java source files
   - ✅ Agent queries Contrast API for applications
   - ✅ Agent returns match with confidence score
   - ✅ JSON output includes:
     - `repository_path`
     - `matches` array with application details
     - `confidence_score` between 0 and 1
     - `reasoning` for the match

3. **Verify output**:
   ```json
   {
     "repository_path": "/path/to/repo",
     "matches": [
       {
         "application_name": "mcp-contrast",
         "application_id": "abc-123",
         "confidence_score": 0.95,
         "reasoning": "Repository contains pom.xml with matching artifact ID and group ID"
       }
     ]
   }
   ```

4. **Check for issues**:
   - [ ] Does it timeout? (increase `AGENT_TIMEOUT` if needed)
   - [ ] Does it fail to connect to Contrast? (check credentials)
   - [ ] Does it fail to read files? (check MCP filesystem server)
   - [ ] Is the match accurate?

#### Test 2: Node.js Repository

**Example Repository**: Any Express or React application with `package.json`

1. **Run identification**:
   ```bash
   contrast-identify ~/path/to/nodejs-repo
   ```

2. **Expected behavior**:
   - ✅ Agent detects Node.js project (package.json)
   - ✅ Agent reads JavaScript/TypeScript files
   - ✅ Agent queries Contrast API
   - ✅ Agent returns match based on package name or dependencies

3. **Verify output** follows same structure as Test 1

4. **Check for issues** (same as Test 1)

#### Test 3: Python Repository

**Example Repository**: Django or Flask application

1. **Run identification**:
   ```bash
   contrast-identify ~/path/to/python-repo
   ```

2. **Expected behavior**:
   - ✅ Agent detects Python project (setup.py, pyproject.toml, requirements.txt)
   - ✅ Agent reads Python source files
   - ✅ Agent queries Contrast API
   - ✅ Agent returns match based on package name or module structure

3. **Verify output** follows same structure as Test 1

4. **Check for issues** (same as Test 1)

#### Test 4: Repository Without Match

**Purpose**: Verify agent handles cases where no application matches

1. **Run identification on repository not in Contrast**:
   ```bash
   contrast-identify ~/path/to/unknown-repo
   ```

2. **Expected behavior**:
   - ✅ Agent analyzes repository successfully
   - ✅ Agent queries Contrast API
   - ✅ Agent returns empty matches array or low confidence scores
   - ✅ Agent provides reasoning for no match

3. **Verify output**:
   ```json
   {
     "repository_path": "/path/to/repo",
     "matches": []
   }
   ```

#### Test 5: Performance Testing

**Purpose**: Verify agent completes in reasonable time

1. **Test with various repository sizes**:
   - Small repo (< 100 files)
   - Medium repo (100-1000 files)
   - Large repo (> 1000 files)

2. **Expected behavior**:
   - ✅ Completes within timeout (default 300s)
   - ✅ No memory issues
   - ✅ Provides progress feedback if available

## Common Issues

### Issue: Agent times out

**Solutions**:
- Increase `AGENT_TIMEOUT` environment variable
- Check network connectivity to Contrast API
- Verify MCP servers are responding

### Issue: No matches found when expected

**Solutions**:
- Verify Contrast credentials are correct
- Check that application exists in Contrast
- Review agent reasoning in output
- Enable debug logging: `DEBUG_LOGGING=true`

### Issue: MCP connection failures

**Solutions**:
- Ensure `npx` is installed (for filesystem MCP)
- Ensure Docker is running (for Contrast MCP)
- Check MCP server logs in debug mode

### Issue: Invalid JSON output

**Solutions**:
- Check for errors in stderr
- Ensure all required environment variables are set
- Try with `--debug` flag if available

## Testing Checklist

Use this checklist to track your testing progress:

- [ ] Java/Maven repository tested successfully
- [ ] Node.js repository tested successfully
- [ ] Python repository tested successfully
- [ ] Repository without match handled correctly
- [ ] Performance is acceptable (< 5 minutes for typical repo)
- [ ] Error messages are clear and actionable
- [ ] JSON output is valid and well-structured
- [ ] Confidence scores make sense
- [ ] Reasoning is understandable
- [ ] All required environment variables documented
- [ ] Tool works with all supported LLM providers:
  - [ ] AWS Bedrock
  - [ ] Anthropic
  - [ ] Azure OpenAI
  - [ ] Google Gemini

## Recording Results

After completing tests, document your findings:

### Test Results Template

```markdown
## Test Results - [Date]

**Tester**: [Your Name]
**Environment**: [OS, Python version]
**LLM Provider**: [Bedrock/Anthropic/Azure/Gemini]

### Java/Maven Test
- **Repository**: [repo name/path]
- **Result**: [Pass/Fail]
- **Match Accuracy**: [Correct/Incorrect]
- **Confidence Score**: [0.0-1.0]
- **Notes**: [Any issues or observations]

### Node.js Test
- **Repository**: [repo name/path]
- **Result**: [Pass/Fail]
- **Match Accuracy**: [Correct/Incorrect]
- **Confidence Score**: [0.0-1.0]
- **Notes**: [Any issues or observations]

### Python Test
- **Repository**: [repo name/path]
- **Result**: [Pass/Fail]
- **Match Accuracy**: [Correct/Incorrect]
- **Confidence Score**: [0.0-1.0]
- **Notes**: [Any issues or observations]

### Issues Encountered
[List any bugs or problems discovered]

### Recommendations
[Suggestions for improvements]
```

## Next Steps

After manual testing is complete:
1. Document all test results in this file or a new `TEST_RESULTS.md`
2. Create GitHub issues for any bugs found
3. Update README with any usage clarifications discovered during testing
4. Consider adding automated E2E tests for the most common scenarios
5. Share test results with the team
