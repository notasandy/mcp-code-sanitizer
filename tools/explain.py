import json
import httpx
from groq_client import call, error_response
from prompts import EXPLAIN
import cache


async def explain_code(code: str, language: str = "python", audience: str = "junior") -> str:
    """
    Объясняет что делает код — пошагово и понятно.

    Args:
        code:     Код для объяснения.
        language: Язык программирования.
        audience: Уровень аудитории — junior, middle или senior.

    Returns:
        JSON с пошаговым объяснением, концепциями и подводными камнями.
    """
    if not code.strip():
        return error_response("Передан пустой код.")

    key = cache.make_key("explain_code", code, language, audience)
    if hit := cache.get(key):
        return hit

    user = (
        f"Язык: {language}\nУровень аудитории: {audience}\n\n"
        f"Код:\n```{language}\n{code}\n```"
    )

    try:
        raw = await call(EXPLAIN, user)
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