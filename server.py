"""
mcp-code-sanitizer — MCP-сервер для ревью кода через Groq.

Инструменты:
  analyze_code    — находит баги и уязвимости в фрагменте кода
  compare_code    — сравнивает две версии, оценивает регрессии
  explain_code    — объясняет код пошагово для junior/middle/senior
  generate_tests  — генерирует pytest/jest/... тесты
  analyze_file    — анализирует целый файл с диска (с чанкингом)
  generate_report — строит красивый HTML-отчёт из результата анализа
  cache_info      — статистика кэша и его очистка
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastmcp import FastMCP
from tools import (
    analyze_code, compare_code, explain_code,
    generate_tests, analyze_file, cache_info, generate_report,
)

mcp = FastMCP(
    name="code-sanitizer",
    instructions="Набор инструментов для строгого ревью кода через Groq LLM.",
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