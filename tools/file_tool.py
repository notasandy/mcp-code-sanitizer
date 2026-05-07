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
    """Split code into chunks by whole lines → [(start_line, text), ...]."""
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
        "summary": result.get("summary", "Analysis complete."),
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
        "summary": f"Found {len(all_issues)} issue(s) across the file.",
        "score": _compute_score(all_issues),
        "issues": sorted(all_issues, key=lambda x: SEVERITY_ORDER.index(x.get("severity", "low"))),
        "warnings": all_warnings,
        "suggestions": all_suggestions,
        "stats": stats,
    }


async def analyze_file(file_path: str, language: str = "", context: str = "") -> str:
    """
    Analyzes a whole code file from disk.
    Automatically detects language by file extension.
    Large files are split into chunks and analyzed in parallel.

    Args:
        file_path: Absolute path to the file.
        language:  Language override (auto-detected from extension if not set).
        context:   Description of what the file does (optional).

    Returns:
        JSON with issues, warnings, suggestions, score, stats.
    """
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        return error_response(f"File not found: {file_path}")
    if not path.is_file():
        return error_response(f"Not a file: {file_path}")

    size_kb = path.stat().st_size / 1024
    if size_kb > MAX_FILE_SIZE_KB:
        return error_response(
            f"File too large ({size_kb:.0f} KB). Maximum is {MAX_FILE_SIZE_KB} KB.",
            "Use analyze_code with a smaller fragment instead.",
        )

    try:
        code = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return error_response("Failed to read file", str(e))

    if not code.strip():
        return error_response("File is empty.")

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
        ctx    = f"\nContext: {context}" if context else ""
        user   = (
            f"File: {filename} | Language: {lang}{ctx}\n"
            f"Lines {start}–{start + text.count(chr(10))}\n\n"
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
        return error_response(f"Groq API error {e.response.status_code}", e.response.text[:300])
    except ValueError as e:
        return error_response(str(e))

    if len(chunks) == 1:
        final = _build_single_result(filename, lang, total_lines, results[0])
    else:
        merged = _merge_chunk_results(filename, lang, total_lines, list(results))
        try:
            system = FILE_SUMMARY.format(filename=filename, language=lang, lines=total_lines)
            user   = f"Analysis results from {len(chunks)} parts:\n\n{json.dumps(merged, ensure_ascii=True)}"
            raw    = await call(system, user)
            final  = json.loads(raw)
        except Exception:
            final  = merged

    out = json.dumps(final, ensure_ascii=True, indent=2)
    cache.set(key, out)
    return out
