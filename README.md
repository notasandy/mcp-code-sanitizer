<!-- mcp-name: io.github.notasandy/mcp-code-sanitizer -->
# mcp-code-sanitizer

> Strict AI-powered code reviewer for Claude Desktop, Cursor, VS Code, and Claude Code CLI.
> Finds bugs, vulnerabilities, and security issues — powered by Groq (free API).

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![PyPI](https://img.shields.io/pypi/v/mcp-code-sanitizer?color=blue)
![FastMCP](https://img.shields.io/badge/FastMCP-2.x-purple)
![Groq](https://img.shields.io/badge/Groq-Free_API-orange)
![License](https://img.shields.io/badge/License-MIT-green)

```
Claude / Cursor / VS Code  ──MCP──►  code-sanitizer  ──REST──►  Groq API
                                        (server.py)              (llama-3.3-70b)
```

![demo](demo.svg)

---

## Features

| Tool | What it does |
|---|---|
| `analyze_code` | Strict review — bugs, security issues, score 0–100 |
| `compare_code` | Compares two versions, detects regressions, recommends merge/request_changes |
| `explain_code` | Step-by-step explanation for junior / middle / senior audience |
| `generate_tests` | Generates pytest / jest / go test — happy path, edge cases, security |
| `analyze_file` | Analyzes a whole file from disk with parallel chunking |
| `generate_report` | Builds an HTML report from any analysis result |
| `cache_info` | Cache statistics and clearing |

### Example output

```json
{
  "summary": "Critical SQL injection and secret exposed in logs",
  "score": 23,
  "issues": [
    {
      "severity": "critical",
      "line": 2,
      "title": "SQL Injection",
      "description": "f-string directly interpolates user_id into query",
      "fix": "cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))"
    }
  ],
  "warnings": [{"title": "No exception handling", "description": "..."}],
  "suggestions": ["Consider using an ORM instead of raw SQL"]
}
```

---

## Installation

> **Prerequisite:** Get a free Groq API key at [console.groq.com/keys](https://console.groq.com/keys) — no credit card required.

### Claude Code CLI

```bash
claude mcp add code-sanitizer -e GROQ_API_KEY=gsk_your_key -- uvx mcp-code-sanitizer
```

### Claude Desktop

| OS | Config file |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

```json
{
  "mcpServers": {
    "code-sanitizer": {
      "command": "uvx",
      "args": ["mcp-code-sanitizer"],
      "env": {
        "GROQ_API_KEY": "gsk_your_key_here"
      }
    }
  }
}
```

### Cursor

Create `.cursor/mcp.json` in your project (or `~/.cursor/mcp.json` globally):

```json
{
  "mcpServers": {
    "code-sanitizer": {
      "command": "uvx",
      "args": ["mcp-code-sanitizer"],
      "env": {
        "GROQ_API_KEY": "gsk_your_key_here"
      }
    }
  }
}
```

### VS Code

Requires VS Code 1.99+ with GitHub Copilot. Create `.vscode/mcp.json` in your project:

```json
{
  "servers": {
    "code-sanitizer": {
      "command": "uvx",
      "args": ["mcp-code-sanitizer"],
      "env": {
        "GROQ_API_KEY": "gsk_your_key_here"
      }
    }
  }
}
```

Or add globally via **Ctrl+Shift+P → "MCP: Add Server"**.

> **Don't have `uvx`?** Install it with `pip install uv`, then use the commands above.

---

## Manual install (alternative)

If you prefer cloning the repo:

```bash
git clone https://github.com/notasandy/mcp-code-sanitizer
cd mcp-code-sanitizer
pip install -r requirements.txt
cp .env.example .env   # add your GROQ_API_KEY
python server.py
```

Then point the client config to:
```json
{
  "command": "python",
  "args": ["/full/path/to/server.py"],
  "env": { "GROQ_API_KEY": "gsk_your_key_here" }
}
```

---

## GitHub Action — automatic PR review

Add AI code review to any repository in 5 lines.
The action posts a structured comment on every PR with score, issues, and fix suggestions.

```yaml
# .github/workflows/ai-review.yml
name: AI Code Review
on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: notasandy/mcp-code-sanitizer@v1
        with:
          groq_api_key: ${{ secrets.GROQ_API_KEY }}
```

Add `GROQ_API_KEY` to your repository secrets → **Settings → Secrets → Actions**.

The action automatically:
- Reviews only changed files (up to 10 per PR)
- Posts a score and structured issue list as a PR comment
- Fails the check if critical issues are found

---

## Usage in chat

After connecting, just write naturally:

```
Review this code for vulnerabilities:

def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)
```

Or call tools explicitly:

```
analyze_file /path/to/my_script.py
generate_tests for this function: ...
compare_code — before vs after refactor, did it get better?
generate_report and save to /tmp/report.html
```

---

## Architecture

```
mcp-code-sanitizer/
├── server.py          # FastMCP entry point
├── config.py          # Constants — keys, limits, extension map
├── groq_client.py     # Async Groq client with auto-retry on 429
├── cache.py           # In-memory LRU cache with TTL
├── prompts.py         # System prompts for all tools
└── tools/
    ├── analyze.py     # analyze_code
    ├── compare.py     # compare_code
    ├── explain.py     # explain_code
    ├── tests.py       # generate_tests
    ├── file_tool.py   # analyze_file — chunking + parallel analysis
    ├── cache_tool.py  # cache_info
    └── report.py      # generate_report — HTML output
```

---

## Configuration

All settings via `.env` or environment variables:

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | — | **Required.** Get at console.groq.com |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model to use |
| `CACHE_TTL` | `3600` | Cache TTL in seconds |
| `CACHE_MAX` | `200` | Max cached entries |

### Available Groq models

| Model | Speed | Quality |
|---|---|---|
| `llama-3.3-70b-versatile` | Fast | Best (default) |
| `llama-3.1-8b-instant` | Fastest | Good |
| `mixtral-8x7b-32768` | Fast | Great |

---

## Contributing

PRs and Issues are welcome. Most wanted:

- Support for other LLM providers (OpenAI, Anthropic)
- New tools: dependency audit, complexity score, docstring generator
- Prompt improvements and new language support

---

## License

MIT — do whatever you want. A star would be appreciated.

---

## Links

- [PyPI](https://pypi.org/project/mcp-code-sanitizer/)
- [Groq Console — free API key](https://console.groq.com)
- [FastMCP docs](https://gofastmcp.com)
- [MCP specification](https://modelcontextprotocol.io)
- [Smithery](https://smithery.ai/server/io.github.notasandy/mcp-code-sanitizer)
- [MCP Registry](https://registry.modelcontextprotocol.io)
