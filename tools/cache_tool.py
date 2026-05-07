import json
import cache


async def cache_info(clear: bool = False) -> str:
    """
    Shows cache statistics or clears the cache.

    Args:
        clear: True — clears the cache, False — shows statistics.

    Returns:
        JSON with cache stats or clear result.
    """
    if clear:
        removed = cache.clear()
        return json.dumps({"cleared": True, "removed_entries": removed}, indent=2)
    return json.dumps(cache.stats(), indent=2)