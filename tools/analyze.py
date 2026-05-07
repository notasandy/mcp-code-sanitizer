import json
import httpx
from groq_client import call, error_response
from prompts import ANALYZE
import cache


async def analyze_code(code: str, language: str = "python", context: str = "") -> str:
    """
    Strict analysis of a code fragment using Groq LLM.

    Args:
        code:     Code fragment to review.
        language: Programming language (python, javascript, go, rust, ...).
        context:  Optional description — what the code does or where it came from.

    Returns:
        JSON with fields: issues, warnings, suggestions, score.
    """
    if not code.strip():
        return error_response("Empty code provided.")

    key = cache.make_key("analyze_code", code, language, context)
    if hit := cache.get(key):
        return hit

    context_block = f"\nContext: {context}" if context else ""
    user = f"Language: {language}{context_block}\n\nCode:\n```{language}\n{code}\n```"

    try:
        raw = await call(ANALYZE, user)
        result = json.loads(raw)
    except httpx.HTTPStatusError as e:
        return error_response(f"Groq API error {e.response.status_code}", e.response.text[:300])
    except json.JSONDecodeError as e:
        return error_response("Groq returned invalid JSON", str(e))
    except ValueError as e:
        return error_response(str(e))

    out = json.dumps(result, indent=2)
    cache.set(key, out)
    return out