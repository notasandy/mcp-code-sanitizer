import json
import httpx
from groq_client import call, error_response
from prompts import COMPARE
import cache


async def compare_code(
    code_before: str, code_after: str,
    language: str = "python", context: str = "",
) -> str:
    """
    Compares two versions of code and evaluates the quality of changes.

    Args:
        code_before: Old version of the code.
        code_after:  New version of the code.
        language:    Programming language.
        context:     Description of what changed and why (optional).

    Returns:
        JSON with improvements, regressions, verdict, recommendation.
    """
    if not code_before.strip() or not code_after.strip():
        return error_response("Both code_before and code_after must be provided.")

    key = cache.make_key("compare_code", code_before, code_after, language, context)
    if hit := cache.get(key):
        return hit

    context_block = f"\nChange context: {context}" if context else ""
    user = (
        f"Language: {language}{context_block}\n\n"
        f"OLD CODE:\n```{language}\n{code_before}\n```\n\n"
        f"NEW CODE:\n```{language}\n{code_after}\n```"
    )

    try:
        raw = await call(COMPARE, user)
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