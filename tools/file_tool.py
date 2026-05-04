import asyncio
import json
from pathlib import Path

import httpx

import cache
from config import CHUNK_SIZE, EXTENSION_MAP, SEVERITY_ORDER, SEVERITY_WEIGHTS
from groq_client import call, error_response
from prompts import FILE_CHUNK, FILE_SUMMARY

MAX_FILE_SIZE_KB = 500


def _split_into_chunks(code: str) -> list[tuple[int, str]]:
    """Разбивает код на чанки по целым строкам → [(start_line, text), ...]."""
    chunks, current, current_len, start = [], [], 0, 1
    for i, line in enumerate(code.splitlines(), 1):
        current.append(line)
        current_len += len(line) + 1
        if current_len >= CHUNK_SIZE:
            chunks.append((start, "\n".join(current)))
            start, current, current_len = i + 1, [], 0
    if current:
        chunks.append((start, "\n".join(current)))
    return chunks


def _compute_score(issues: list[dict]) -> int:
    penalty = sum(SEVERITY_WEIGHTS.get(i.get("severity", "low"), 0) for i in issues)
    return max(0, 100 - penalty)


def _build_single_result(filename: str, lang: str, total_lines: int, result: dict) -> dict:
    issues = result.get("issues", [])
    stats = {s: sum(1 for i in issues if i.get("severity") == s) for s in SEVERITY_ORDER}
    return {
        "file": filename, "language": lang, "lines": total_lines,
        "summary": result.get("summary", "Анализ завершён"),
        "score": _compute_score(issues),
        "issues": issues,
        "warnings": result.get("warnings", []),
        "suggestions": result.get("suggestions", []),
        "stats": stats,
    }


def _merge_chunk_results(filename: str, lang: str, total_lines: int, chunk_results: list[dict]) -> dict:
    all_issues      = [i for r in chunk_results for i in r.get("issues", [])]
    all_warnings    = [w for r in chunk_results for w in r.get("warnings", [])]
    all_suggestions = list(dict.fromkeys(s for r in chunk_results for s in r.get("suggestions", [])))
    stats = {s: sum(1 for i in all_issues if i.get("severity") == s) for s in SEVERITY_ORDER}
    return {
        "file": filename, "language": lang, "lines": total_lines,
        "summary": f"Найдено {len(all_issues)} проблем в файле",
        "score": _compute_score(all_issues),
        "issues": sorted(all_issues, key=lambda x: SEVERITY_ORDER.index(x.get("severity", "low"))),
        "warnings": all_warnings,
        "suggestions": all_suggestions,
        "stats": stats,
    }


async def analyze_file(file_path: str, language: str = "", context: str = "") -> str:
    """
    Анализирует целый файл с кодом на диске.
    Автоматически определяет язык по расширению.
    Большие файлы разбиваются на чанки и анализируются параллельно.

    Args:
        file_path: Абсолютный путь к файлу.
        language:  Язык (если не задан — определяется по расширению).
        context:   Описание что делает файл (необязательно).

    Returns:
        JSON с issues, warnings, suggestions, score, stats.
    """
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        return error_response(f"Файл не найден: {file_path}")
    if not path.is_file():
        return error_response(f"Это не файл: {file_path}")

    size_kb = path.stat().st_size / 1024
    if size_kb > MAX_FILE_SIZE_KB:
        return error_response(
            f"Файл слишком большой ({size_kb:.0f} КБ). Максимум — {MAX_FILE_SIZE_KB} КБ.",
            "Передай фрагмент через analyze_code.",
        )

    try:
        code = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return error_response("Не удалось прочитать файл", str(e))

    if not code.strip():
        return error_response("Файл пустой.")

    key = cache.make_key("analyze_file", str(path), str(path.stat().st_mtime), language, context)
    if hit := cache.get(key):
        return hit

    lang        = language.strip() or EXTENSION_MAP.get(path.suffix.lower(), "text")
    filename    = path.name
    total_lines = code.count("\n") + 1
    chunks      = _split_into_chunks(code)

    semaphore = asyncio.Semaphore(3)

    async def _analyze_chunk(num: int, start: int, text: str) -> dict:
        system = FILE_CHUNK.format(chunk_num=num, total=len(chunks))
        ctx    = f"\nКонтекст: {context}" if context else ""
        user   = (
            f"Файл: {filename} | Язык: {lang}{ctx}\n"
            f"Строки {start}–{start + text.count(chr(10))}\n\n"
            f"```{lang}\n{text}\n```"
        )
        async with semaphore:
            raw = await call(system, user)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"issues": [], "warnings": [], "suggestions": []}

    try:
        results = await asyncio.gather(*[
            _analyze_chunk(i + 1, start, text)
            for i, (start, text) in enumerate(chunks)
        ])
    except httpx.HTTPStatusError as e:
        return error_response(f"Groq API ошибка {e.response.status_code}", e.response.text[:300])
    except ValueError as e:
        return error_response(str(e))

    if len(chunks) == 1:
        final = _build_single_result(filename, lang, total_lines, results[0])
    else:
        # Для больших файлов пробуем свести через Groq, fallback — локальный merge
        merged = _merge_chunk_results(filename, lang, total_lines, list(results))
        try:
            system = FILE_SUMMARY.format(filename=filename, language=lang, lines=total_lines)
            user   = f"Результаты анализа {len(chunks)} частей:\n\n{json.dumps(merged, ensure_ascii=False)}"
            raw    = await call(system, user)
            final  = json.loads(raw)
        except Exception:
            final  = merged

    out = json.dumps(final, ensure_ascii=False, indent=2)
    cache.set(key, out)
    return out