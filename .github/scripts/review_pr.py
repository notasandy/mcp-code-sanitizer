"""
GitHub Action script: AI code review for pull requests.
- Gets changed files from the PR diff
- Sends each file to Groq for review
- Posts a structured comment on the PR
"""

import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error

# ── Config ────────────────────────────────────────────────────────────────────
GROQ_API_KEY  = os.environ["GROQ_API_KEY"]
GITHUB_TOKEN  = os.environ["GITHUB_TOKEN"]
REPO          = os.environ["REPO"]
PR_NUMBER     = os.environ["PR_NUMBER"]
BASE_SHA      = os.environ["BASE_SHA"]
HEAD_SHA      = os.environ["HEAD_SHA"]
GROQ_MODEL    = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_URL      = "https://api.groq.com/openai/v1/chat/completions"
GITHUB_API    = "https://api.github.com"

# Only review these extensions
REVIEWABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".go", ".rs", ".java", ".cs", ".cpp", ".c",
    ".rb", ".php", ".swift", ".kt", ".sh", ".sql",
}

MAX_FILE_CHARS = 8_000   # ~4k tokens — safe for free Groq tier
MAX_FILES      = 10      # don't review more than 10 files per PR

SYSTEM_PROMPT = """\
You are a strict senior code reviewer. Analyze the provided code diff and return ONLY valid JSON, no markdown.

Response format:
{
  "summary": "One sentence overall verdict",
  "score": <0-100>,
  "issues": [
    {
      "severity": "critical|high|medium|low",
      "line": <line number or null>,
      "title": "Short issue name",
      "description": "Detailed explanation",
      "fix": "Concrete fix or code example"
    }
  ],
  "warnings": [{"title": "...", "description": "..."}],
  "suggestions": ["improvement tip"]
}

Rules:
- Focus on NEW code in the diff (lines starting with +)
- issues: real bugs, security vulnerabilities, memory leaks, SQL injection, etc.
- warnings: code smells, anti-patterns
- suggestions: refactoring, performance, idioms
- score 100 = perfect code, 0 = dangerous
- Do NOT invent problems that don't exist
"""


# ── Groq call ─────────────────────────────────────────────────────────────────
def call_groq(diff: str, filename: str) -> dict:
    payload = json.dumps({
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"File: {filename}\n\nDiff:\n```\n{diff}\n```"},
        ],
        "temperature": 0.1,
        "max_tokens": 1500,
        "response_format": {"type": "json_object"},
    }).encode()

    req = urllib.request.Request(
        GROQ_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())

    raw = data["choices"][0]["message"]["content"]
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


# ── GitHub API ────────────────────────────────────────────────────────────────
def github_request(method: str, path: str, body: dict | None = None) -> dict:
    url  = f"{GITHUB_API}/{path}"
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def post_comment(body: str) -> None:
    github_request("POST", f"repos/{REPO}/issues/{PR_NUMBER}/comments", {"body": body})


def delete_old_bot_comments() -> None:
    """Remove previous bot review comments to avoid spam."""
    try:
        comments = github_request("GET", f"repos/{REPO}/issues/{PR_NUMBER}/comments")
        for c in comments:
            if c.get("user", {}).get("login") == "github-actions[bot]" and "🔍 AI Code Review" in c.get("body", ""):
                github_request("DELETE", f"repos/{REPO}/issues/comments/{c['id']}")
    except Exception:
        pass


# ── Get changed files from diff ───────────────────────────────────────────────
def get_changed_files() -> list[tuple[str, str]]:
    """Returns list of (filename, diff_content) for reviewable files."""
    result = subprocess.run(
        ["git", "diff", "--name-only", BASE_SHA, HEAD_SHA],
        capture_output=True, text=True, check=True,
    )
    files = [f.strip() for f in result.stdout.splitlines() if f.strip()]

    changed = []
    for filename in files[:MAX_FILES]:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in REVIEWABLE_EXTENSIONS:
            continue
        if not os.path.exists(filename):
            continue

        diff_result = subprocess.run(
            ["git", "diff", BASE_SHA, HEAD_SHA, "--", filename],
            capture_output=True, text=True,
        )
        diff = diff_result.stdout[:MAX_FILE_CHARS]
        if diff.strip():
            changed.append((filename, diff))

    return changed


# ── Format comment ────────────────────────────────────────────────────────────
SEVERITY_EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
SCORE_EMOJI    = lambda s: "🟢" if s >= 80 else "🟡" if s >= 60 else "🔴"


def format_file_review(filename: str, review: dict) -> str:
    score   = review.get("score", 0)
    issues  = review.get("issues", [])
    warns   = review.get("warnings", [])
    sugs    = review.get("suggestions", [])
    summary = review.get("summary", "")

    lines = [
        f"#### `{filename}` {SCORE_EMOJI(score)} Score: **{score}/100**",
        f"> {summary}",
        "",
    ]

    if issues:
        for issue in sorted(issues, key=lambda x: ["critical","high","medium","low"].index(x.get("severity","low"))):
            sev   = issue.get("severity", "low")
            emoji = SEVERITY_EMOJI.get(sev, "⚪")
            line  = f" (line {issue['line']})" if issue.get("line") else ""
            lines.append(f"**{emoji} {sev.upper()} — {issue.get('title','')}**{line}")
            lines.append(f"{issue.get('description','')}")
            if issue.get("fix"):
                lines.append(f"```\n{issue['fix']}\n```")
            lines.append("")

    if warns:
        lines.append("**⚠️ Warnings**")
        for w in warns:
            lines.append(f"- **{w.get('title','')}** — {w.get('description','')}")
        lines.append("")

    if sugs:
        lines.append("**💡 Suggestions**")
        for s in sugs:
            lines.append(f"- {s}")
        lines.append("")

    return "\n".join(lines)


def format_full_comment(file_reviews: list[tuple[str, dict]]) -> str:
    total_issues = sum(len(r.get("issues", [])) for _, r in file_reviews)
    avg_score    = sum(r.get("score", 0) for _, r in file_reviews) // max(len(file_reviews), 1)
    files_count  = len(file_reviews)

    header = [
        "## 🔍 AI Code Review",
        "",
        f"Reviewed **{files_count} file(s)** · "
        f"Average score: **{avg_score}/100** {SCORE_EMOJI(avg_score)} · "
        f"Total issues: **{total_issues}**",
        "",
        "---",
        "",
    ]

    body = []
    for filename, review in file_reviews:
        body.append(format_file_review(filename, review))
        body.append("---")
        body.append("")

    footer = [
        "<sub>Generated by [mcp-code-sanitizer](https://github.com/notasandy/mcp-code-sanitizer) "
        "powered by Groq 🤖</sub>",
    ]

    return "\n".join(header + body + footer)


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    print("Getting changed files...")
    changed = get_changed_files()

    if not changed:
        print("No reviewable files changed. Skipping.")
        return

    print(f"Reviewing {len(changed)} file(s)...")
    file_reviews = []

    for filename, diff in changed:
        print(f"  → {filename}")
        try:
            review = call_groq(diff, filename)
            file_reviews.append((filename, review))
        except Exception as e:
            print(f"  ✗ Error reviewing {filename}: {e}")
            file_reviews.append((filename, {
                "score": 0, "summary": f"Review failed: {e}",
                "issues": [], "warnings": [], "suggestions": [],
            }))

    print("Posting comment...")
    delete_old_bot_comments()
    comment = format_full_comment(file_reviews)
    post_comment(comment)
    print("Done! ✓")

    # Fail the check if any critical issues found
    has_critical = any(
        i.get("severity") == "critical"
        for _, r in file_reviews
        for i in r.get("issues", [])
    )
    if has_critical:
        print("::error::Critical issues found in PR. Please fix before merging.")
        sys.exit(1)


if __name__ == "__main__":
    main()