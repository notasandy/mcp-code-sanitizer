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
    Compares two versions of code and evaluates whether the change is an improvement.

    Performs a structured diff analysis: identifies what improved, what regressed,
    and what changed neutrally. Returns a merge recommendation based on the findings.
    Useful for code review, refactoring validation, and AI-generated code verification.

    Behavior:
        - Sends both versions to Groq with a code review prompt focused on regressions
        - Detects improvements: better performance, fixed bugs, improved readability
        - Detects regressions: new bugs, security issues, reduced maintainability
        - Neutral changes: formatting, renaming, restructuring without quality impact
        - recommendation field maps to standard PR actions:
            "merge"             -- change is safe and beneficial
            "request_changes"   -- regressions found, must be fixed before merging
            "needs_discussion"  -- trade-offs present, team should decide
        - Results are cached by SHA256 hash of (code_before + code_after + language)
        - Returns valid JSON even on errors (with an "error" field)

    Args:
        code_before: The original version of the code (before changes).
                     Include complete function or class -- not just the diff.
        code_after:  The new version of the code (after changes).
                     Must be the same scope as code_before for accurate comparison.
        language:    Programming language of both versions.
                     Examples: "python", "javascript", "go", "typescript".
                     Defaults to "python".
        context:     Optional description of the intent behind the change.
                     Helps distinguish intentional trade-offs from bugs.
                     Example: "Optimized for memory usage at the cost of readability"

    Returns:
        JSON string with the following fields:
        - verdict (str): "improvement" | "regression" | "neutral change"
        - summary (str): One-sentence conclusion about the overall change
        - improvements (list): What got better, each with title and description
        - regressions (list): What got worse, each with severity, title, description
        - neutral_changes (list): Changes with no quality impact (strings)
        - score_before (int): Quality score of the original code (0-100)
        - score_after (int): Quality score of the new code (0-100)
        - recommendation (str): "merge" | "request_changes" | "needs_discussion"

    Usage guidelines:
        - Use before merging a PR to get an objective quality comparison
        - Pass context when the change is intentional (e.g., trading speed for memory)
        - Works best when code_before and code_after cover the same function/class scope
        - If score_after < score_before, check regressions before merging
        - Combine with analyze_code on code_after to get detailed issue breakdown

    Example:
        compare_code(
            code_before="def get(id): return db.query(f'SELECT * WHERE id={id}')",
            code_after="def get(id): return db.query('SELECT * WHERE id=?', [id])",
            language="python",
            context="Fixed SQL injection vulnerability"
        )
    """
    if not code_before.strip() or not code_after.strip():
        return error_response("Both code_before and code_after must be provided.")

    key = cache.make_key("compare_code", code_before, code_after, language, context)
    if hit := cache.get(key):
        return hit

    context_block = f"\nChange context: {context}" if context else ""
    user = (
        f"Language: {language}{context_block}\n\n"
        f"OLD CODE:\n```{language}\n{code_before}\n```\n\n"
        f"NEW CODE:\n```{language}\n{code_after}\n```"
    )

    try:
        raw = await call(COMPARE, user)
        result = json.loads(raw)
    except httpx.HTTPStatusError as e:
        return error_response(f"Groq API error {e.response.status_code}", e.response.text[:300])
    except json.JSONDecodeError as e:
        return error_response("Groq returned invalid JSON", str(e))
    except ValueError as e:
        return error_response(str(e))

    out = json.dumps(result, ensure_ascii=True, indent=2)
    cache.set(key, out)
    return out