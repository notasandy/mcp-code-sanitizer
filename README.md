# 🔍 mcp-code-sanitizer

> A strict AI-powered code reviewer that runs your code through Groq LLM directly from Claude Desktop, Cursor, or any MCP-compatible agent.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![FastMCP](https://img.shields.io/badge/FastMCP-3.x-purple)
![Groq](https://img.shields.io/badge/Groq-Free_API-orange)
![License](https://img.shields.io/badge/License-MIT-green)

```
Claude Desktop  ──MCP──►  code-sanitizer  ──REST──►  Groq API
                            (server.py)               (llama-3.3-70b)
```

---

## ✨ Features

| Tool | Description |
|---|---|
| `analyze_code` | Strict code review — bugs, vulnerabilities, score 0–100 |
| `compare_code` | Compares two versions, finds regressions, recommends merge/request_changes |
| `explain_code` | Step-by-step explanation for junior/middle/senior audience |
| `generate_tests` | Generates pytest/jest/go test with happy path, edge cases, security tests |
| `analyze_file` | Analyzes a whole file from disk with parallel chunking |
| `generate_report` | Builds a beautiful HTML report from any analysis result |
| `cache_info` | Cache statistics and clearing |

### Example response

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

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/mcp-code-sanitizer
cd mcp-code-sanitizer
```

### 2. Create virtual environment and install dependencies

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Add your Groq API key

Get a free key at [console.groq.com/keys](https://console.groq.com/keys)

```bash
cp .env.example .env
# Open .env and set GROQ_API_KEY=gsk_...
```

### 4. Test the server

```bash
python server.py
```

Silence means it's working — the server is listening for MCP requests via stdio.

---

## 🔌 Connect to Claude Desktop

Find your config file and add the `mcpServers` section:

| OS | Config path |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

```json
{
  "mcpServers": {
    "code-sanitizer": {
      "command": "/full/path/to/venv/bin/python",
      "args": ["/full/path/to/server.py"],
      "env": {
        "GROQ_API_KEY": "gsk_your_key_here"
      }
    }
  }
}
```

Restart Claude Desktop — you'll see the 🔧 icon in chat.

---

## 🔌 Connect to Cursor

Create `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "code-sanitizer": {
      "command": "/full/path/to/venv/bin/python",
      "args": ["/full/path/to/server.py"],
      "env": {"GROQ_API_KEY": "gsk_your_key_here"}
    }
  }
}
```

---

## 🧪 Testing via MCP Inspector

```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
fastmcp dev inspector server.py
```

A browser UI opens with full tool testing interface.

---

## 💬 Usage in chat

After connecting to Claude Desktop, just write:

```
Review this code for vulnerabilities:

def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)
```

Or explicitly call a tool:

```
Use analyze_file on /path/to/my_script.py
Generate tests for this function: ...
Compare these two versions and tell me if it got better: ...
```

---

## 🏗️ Architecture

```
mcp-code-sanitizer/
├── server.py          # FastMCP entry point (39 lines)
├── config.py          # Constants — keys, limits, mappings
├── groq_client.py     # Groq API client with auto-retry on rate limits
├── cache.py           # In-memory cache with TTL
├── prompts.py         # System prompts for all tools
└── tools/
    ├── analyze.py     # analyze_code
    ├── compare.py     # compare_code
    ├── explain.py     # explain_code
    ├── tests.py       # generate_tests
    ├── file_tool.py   # analyze_file (chunking + parallel analysis)
    ├── cache_tool.py  # cache_info
    └── report.py      # generate_report (HTML)
```

---

## ⚙️ Configuration

All settings via environment variables or `.env`:

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | — | Required. Get at console.groq.com |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model |
| `CACHE_TTL` | `3600` | Cache TTL in seconds |
| `CACHE_MAX` | `200` | Max cache entries |

### Available Groq models

| Model | Speed | Quality |
|---|---|---|
| `llama-3.3-70b-versatile` | ⚡⚡ | ⭐⭐⭐⭐⭐ (default) |
| `llama-3.1-8b-instant` | ⚡⚡⚡ | ⭐⭐⭐ |
| `mixtral-8x7b-32768` | ⚡⚡ | ⭐⭐⭐⭐ |

---

## 📦 Requirements

```
fastmcp>=2.3.0
httpx>=0.27.0
python-dotenv>=1.0.0
```

---

## 🤝 Contributing

PRs and Issues are welcome! Especially interested in:

- Support for other LLM providers (OpenAI, Anthropic)
- New tools (security audit, dependency check, complexity analysis)
- Prompt improvements

---

## 📄 License

MIT — do whatever you want. A GitHub star would be appreciated ⭐

---

## 🔗 Links

- [FastMCP docs](https://gofastmcp.com)
- [Groq Console](https://console.groq.com)
- [MCP specification](https://modelcontextprotocol.io)
- [Smithery — MCP server catalog](https://smithery.ai)