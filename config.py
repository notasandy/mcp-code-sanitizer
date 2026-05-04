import os

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

CHUNK_SIZE = 6_000   # ~12k токенов на запрос
CACHE_TTL  = int(os.getenv("CACHE_TTL", "3600"))
CACHE_MAX  = int(os.getenv("CACHE_MAX", "200"))

EXTENSION_MAP: dict[str, str] = {
    ".py": "python",   ".js": "javascript", ".ts": "typescript",
    ".jsx": "javascript", ".tsx": "typescript", ".go": "go",
    ".rs": "rust",     ".java": "java",      ".cs": "csharp",
    ".cpp": "cpp",     ".c": "c",            ".rb": "ruby",
    ".php": "php",     ".swift": "swift",    ".kt": "kotlin",
    ".sh": "bash",     ".sql": "sql",        ".yaml": "yaml",
    ".yml": "yaml",    ".json": "json",      ".html": "html",
    ".css": "css",
}

SEVERITY_ORDER = ["critical", "high", "medium", "low"]
SEVERITY_WEIGHTS = {"critical": 20, "high": 10, "medium": 5, "low": 2}