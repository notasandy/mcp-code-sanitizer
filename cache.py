import hashlib
import time
from config import CACHE_TTL, CACHE_MAX

_store: dict[str, tuple[float, str]] = {}


def make_key(*parts: str) -> str:
    raw = "\x00".join(parts).encode()
    return hashlib.sha256(raw).hexdigest()


def get(key: str) -> str | None:
    entry = _store.get(key)
    if not entry:
        return None
    ts, value = entry
    if time.time() - ts < CACHE_TTL:
        return value
    del _store[key]
    return None


def set(key: str, value: str) -> None:
    if len(_store) >= CACHE_MAX:
        oldest = sorted(_store, key=lambda k: _store[k][0])
        for k in oldest[: CACHE_MAX // 4]:
            del _store[k]
    _store[key] = (time.time(), value)


def stats() -> dict:
    now = time.time()
    alive = sum(1 for ts, _ in _store.values() if now - ts < CACHE_TTL)
    return {"total": len(_store), "alive": alive, "ttl_seconds": CACHE_TTL}


def clear() -> int:
    count = len(_store)
    _store.clear()
    return count