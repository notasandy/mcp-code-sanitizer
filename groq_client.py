import asyncio
import json
import re

import httpx

from config import GROQ_API_KEY, GROQ_API_URL, GROQ_MODEL

MAX_RETRIES = 4
MAX_TOKENS  = 2048


async def call(system: str, user: str, json_mode: bool = True) -> str:
    """Send a request to Groq. Automatically retries on 429 rate limit errors."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set. Add it to .env or set it as an environment variable.")

    payload: dict = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "temperature": 0.1,
        "max_tokens": MAX_TOKENS,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    response = None
    for attempt in range(MAX_RETRIES):
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                GROQ_API_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json=payload,
            )

        if response.status_code == 429 and attempt < MAX_RETRIES - 1:
            await asyncio.sleep(_parse_retry_after(response))
            continue

        response.raise_for_status()
        break

    raw: str = response.json()["choices"][0]["message"]["content"]
    return _strip_fences(raw)


def _parse_retry_after(response: httpx.Response) -> float:
    try:
        msg = response.json().get("error", {}).get("message", "")
        match = re.search(r"try again in ([0-9.]+)s", msg)
        if match:
            return float(match.group(1)) + 1.0
    except Exception:
        pass
    return 20.0


def _strip_fences(raw: str) -> str:
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    return re.sub(r"\s*```$", "", raw)


def error_response(msg: str, detail: str = "") -> str:
    return json.dumps({"error": msg, "detail": detail}, ensure_ascii=False)