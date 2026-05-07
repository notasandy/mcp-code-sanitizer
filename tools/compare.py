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
    Сравнивает две версии кода и оценивает качество изменений.

    Args:
        code_before: Старая версия кода.
        code_after:  Новая версия кода.
        language:    Язык программирования.
        context:     Описание что и зачем изменялось.

    Returns:
        JSON с improvements, regressions, verdict, recommendation.
    """
    if not code_before.strip() or not code_after.strip():
        return error_response("Нужно передать обе версии кода: code_before и code_after.")

    key = cache.make_key("compare_code", code_before, code_after, language, context)
    if hit := cache.get(key):
        return hit

    context_block = f"\nКонтекст изменений: {context}" if context else ""
    user = (
        f"Язык: {language}{context_block}\n\n"
        f"СТАРЫЙ КОД:\n```{language}\n{code_before}\n```\n\n"
        f"НОВЫЙ КОД:\n```{language}\n{code_after}\n```"
    )

    try:
        raw = await call(COMPARE, user)
        result = json.loads(raw)
    except httpx.HTTPStatusError as e:
        return error_response(f"Groq API ошибка {e.response.status_code}", e.response.text[:300])
    except json.JSONDecodeError as e:
        return error_response("Groq вернул невалидный JSON", str(e))
    except ValueError as e:
        return error_response(str(e))

    out = json.dumps(result, ensure_ascii=True, indent=2)
    cache.set(key, out)
    return out
