import json
import cache


async def cache_info(clear: bool = False) -> str:
    """
    Показывает статистику кэша или очищает его.

    Args:
        clear: True — очищает кэш, False — показывает статистику.

    Returns:
        JSON со статистикой или результатом очистки.
    """
    if clear:
        removed = cache.clear()
        return json.dumps({"cleared": True, "removed_entries": removed}, ensure_ascii=False, indent=2)
    return json.dumps(cache.stats(), ensure_ascii=False, indent=2)