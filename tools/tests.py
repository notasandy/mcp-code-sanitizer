import json
import httpx
from groq_client import call, error_response
from prompts import TESTS
import cache


async def generate_tests(code: str, language: str = "python", framework: str = "") -> str:
    """
    Generates tests for the provided code.

    Args:
        code:      Code to generate tests for.
        language:  Programming language.
        framework: Test framework (optional — pytest, jest, unittest, etc.).

    Returns:
        JSON with test cases, runnable test code, and coverage estimate.
    """
    if not code.strip():
        return error_response("Empty code provided.")

    key = cache.make_key("generate_tests", code, language, framework)
    if hit := cache.get(key):
        return hit

    framework_block = f"\nUse framework: {framework}" if framework else ""
    user = f"Language: {language}{framework_block}\n\nCode:\n```{language}\n{code}\n```"

    try:
        raw = await call(TESTS, user)
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
