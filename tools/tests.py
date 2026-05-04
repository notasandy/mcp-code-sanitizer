import json
import httpx
from groq_client import call, error_response
from prompts import TESTS
import cache


async def generate_tests(code: str, language: str = "python", framework: str = "") -> str:
    """
    Генерирует тесты для переданного кода.

    Args:
        code:      Код для тестирования.
        language:  Язык программирования.
        framework: Фреймворк (опционально — pytest, jest, unittest и т.д.).

    Returns:
        JSON с тест-кейсами, кодом тестов и оценкой покрытия.
    """
    if not code.strip():
        return error_response("Передан пустой код.")

    key = cache.make_key("generate_tests", code, language, framework)
    if hit := cache.get(key):
        return hit

    framework_block = f"\nИспользуй фреймворк: {framework}" if framework else ""
    user = f"Язык: {language}{framework_block}\n\nКод:\n```{language}\n{code}\n```"

    try:
        raw = await call(TESTS, user)
        result = json.loads(raw)
    except httpx.HTTPStatusError as e:
        return error_response(f"Groq API ошибка {e.response.status_code}", e.response.text[:300])
    except json.JSONDecodeError as e:
        return error_response("Groq вернул невалидный JSON", str(e))
    except ValueError as e:
        return error_response(str(e))

    out = json.dumps(result, ensure_ascii=False, indent=2)
    cache.set(key, out)
    return out