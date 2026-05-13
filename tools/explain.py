import json
import httpx
from groq_client import call, error_response
from prompts import EXPLAIN
import cache
async def explain_code(code: str, language: str = "python", audience: str = "junior") -> str:
    """
    Explains what code does - step by step and clearly.
    Args:
        code:     Code to explain.
        language: Programming language.
        audience: Target audience level - junior, middle, or senior.
    Returns:
        JSON with step-by-step explanation, key concepts, and gotchas.
    """
    if not code.strip():
        return error_response("Empty code provided.")

    key = cache.make_key("explain_code", code, language, audience)
    if hit := cache.get(key):
        return hit

    user = (
        f"Language: {language}\nAudience level: {audience}\n\n"
        f"Code:\n```{language}\n{code}\n```"

    )
    try:
        raw = await call(EXPLAIN, user)
        result = json.loads(raw)
    except httpx.HTTPStatusError as e:
        return error_response(f"Groq API error {e.response.status_code}", e.response.text[:300])
    except json.JSONDecodeError as e:
        return error_response("Groq returned invalid JSON", str(e))
    except ValueError as e:
        return error_response(str(e))
    out = json.dumps(result, ensure_ascii=True, indent=2)
    cache.set(key, out)
    return out

