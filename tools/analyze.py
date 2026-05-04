import json
import httpx
from groq_client import call, error_response
from prompts import ANALYZE
import cache


async def analyze_code(code: str, language: str = "python", context: str = "") -> str:
    """
    Строгий анализ фрагмента кода через Groq LLM.

    Args:
        code:     Фрагмент кода для проверки.
        language: Язык программирования (python, javascript, go, rust, …).
        context:  Необязательное описание — что делает код, откуда взят.

    Returns:
        JSON с полями issues, warnings, suggestions, score.
    """
    if not code.strip():
        return error_response("Передан пустой код.")

    key = cache.make_key("analyze_code", code, language, context)
    if hit := cache.get(key):
        return hit

    context_block = f"\nКонтекст: {context}" if context else ""
    user = f"Язык: {language}{context_block}\n\nКод:\n```{language}\n{code}\n```"

    try:
        raw = await call(ANALYZE, user)
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