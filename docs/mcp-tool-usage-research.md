# MCP Tool Usage Research

Research conducted to identify which MCP tools are actually used by the app identifier agent.

## Test Results

| Test Case | Unique Tools Used | Input Tokens | Tool Calls |
|-----------|-------------------|--------------|------------|
| employee-management (Java, known app) | `fs__search_files`, `fs__read_text_file`, `contrast__search_applications` | 28,854 | 3 |
| contrast-app-identifier (Python, unknown) | `fs__read_multiple_files`, `contrast__search_applications` | 29,794 | 3 |
| platform-onboarding-spa (Node.js/React) | `fs__search_files`, `fs__list_directory`, `fs__read_text_file`, `contrast__search_applications` | 56,291 | 6 |
| aiml-services (Gradle multi-module) | `fs__search_files`, `fs__list_directory`, `fs__read_text_file`, `contrast__search_applications` | 53,786 | 8 |

## Tools Actually Used (5 of 27)

### Filesystem Tools (4 of 14)
- `fs__search_files` - Find config files (contrast_security.yaml, contrast.yaml)
- `fs__read_text_file` - Read config files (contrast yaml, pom.xml, package.json, pyproject.toml, settings.gradle.kts)
- `fs__read_multiple_files` - Batch read multiple config files
- `fs__list_directory` - List directory contents when searching for project files

### Contrast Tools (1 of 13)
- `contrast__search_applications` - Search Contrast API for matching applications

## Unused Tools (22 of 27)

### Filesystem (10 unused)
- read_file (deprecated)
- read_media_file
- write_file
- edit_file
- create_directory
- list_directory_with_sizes
- directory_tree
- move_file
- get_file_info
- list_allowed_directories

### Contrast (12 unused)
- get_route_coverage
- get_protect_rules
- get_vulnerability
- search_attacks
- get_scan_results
- search_vulnerabilities
- list_applications_by_cve
- list_vulnerability_types
- get_session_metadata
- search_app_vulnerabilities
- get_scan_project
- list_application_libraries

## Token Optimization Options

### Option 1: Filter MCP tools (easiest)

Use pydantic-ai's `.filtered()` to only expose needed tools:

```python
fs_server = MCPServerStdio(...)
fs_filtered = fs_server.filtered(
    lambda ctx, tool_def: tool_def.name in (
        'fs__search_files',
        'fs__read_text_file',
        'fs__read_multiple_files',
        'fs__list_directory'
    )
)

contrast_server = MCPServerStdio(...)
contrast_filtered = contrast_server.filtered(
    lambda ctx, tool_def: tool_def.name == 'contrast__search_applications'
)
```

### Option 2: Replace filesystem MCP with native tools (most efficient)

Skip MCP overhead entirely for simple file ops:

```python
@agent.tool_plain
def read_file(path: str) -> str:
    """Read a file from the repository."""
    return Path(path).read_text()

@agent.tool_plain
def list_directory(path: str) -> list[str]:
    """List files in a directory."""
    return os.listdir(path)
```

### Estimated Token Savings

| Approach | Estimated Input Tokens | Savings |
|----------|------------------------|---------|
| Current (27 tools) | ~30-55k | baseline |
| Option 1 (5 filtered tools) | ~10-15k | ~60-70% |
| Option 2 (native + 1 MCP) | ~5-8k | ~80% |

## Recommendation

Option 1 (filtering) is the safest first step - it preserves MCP compatibility while dramatically reducing token usage. Option 2 can be explored later if further optimization is needed.

---

## Implementation Results

Option 1 was implemented in `mcp_tools.py` using pydantic-ai's `.filtered()` method.

### Token Reduction Results

| Test Case | Before | After | Reduction |
|-----------|--------|-------|-----------|
| employee-management (Java, known app) | 28,854 | 7,286 | **75%** |
| contrast-app-identifier (Python, unknown) | 29,794 | 10,145 | **66%** |
| platform-onboarding-spa (Node.js/React) | 56,291 | 16,981 | **70%** |
| aiml-services (Gradle multi-module) | 53,786 | 17,198 | **68%** |

**Average reduction: ~70%**

### Implementation Notes

- Tool names in `tool_def.name` include the prefix (e.g., `fs__search_files` not `search_files`)
- Filter functions receive `(ctx, tool_def)` where `tool_def.name` is the prefixed name
- The filtered toolset is created by calling `.filtered()` on the MCPServerStdio instance
