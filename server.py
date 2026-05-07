"""
mcp-code-sanitizer — MCP server for AI-powered code review using Groq.

Tools:
  analyze_code    — finds bugs and vulnerabilities in a code fragment
  compare_code    — compares two versions, detects regressions
  explain_code    — explains code step by step for junior/middle/senior
  generate_tests  — generates pytest/jest/... tests
  analyze_file    — analyzes a whole file from disk (with chunking)
  generate_report — builds a beautiful HTML report from analysis results
  cache_info      — cache statistics and clearing
"""

import sys
import io

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastmcp import FastMCP
from tools import (
    analyze_code, compare_code, explain_code,
    generate_tests, analyze_file, cache_info, generate_report,
)

mcp = FastMCP(
    name="code-sanitizer",
    instructions="A toolkit for strict AI-powered code review using Groq LLM.",
)

mcp.tool()(analyze_code)
mcp.tool()(compare_code)
mcp.tool()(explain_code)
mcp.tool()(generate_tests)
mcp.tool()(analyze_file)
mcp.tool()(cache_info)
mcp.tool()(generate_report)

if __name__ == "__main__":
    mcp.run(transport="stdio")