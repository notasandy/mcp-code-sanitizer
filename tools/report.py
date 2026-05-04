import json
import math
from pathlib import Path

from groq_client import error_response

_SEVERITY_ORDER = ["critical", "high", "medium", "low"]

_CSS = """
:root {
  --bg:#0f1117; --surface:#1a1d2e; --surface2:#252840; --border:#2e3150;
  --text:#e2e8f0; --muted:#8892a4; --green:#2ed573; --yellow:#ffa502; --red:#ff4757;
  --critical:#ff4757; --high:#ff6b35; --medium:#ffa502; --low:#2ed573;
  --blue:#5352ed; --purple:#8c7ae6; --r:10px; --shadow:0 4px 24px rgba(0,0,0,.4);
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding:2rem 1rem}
.wrap{max-width:960px;margin:0 auto}

.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);box-shadow:var(--shadow)}
.card+.card{margin-top:1.25rem}

/* header */
.header{background:linear-gradient(135deg,var(--surface),var(--surface2));padding:2rem;border-radius:var(--r);margin-bottom:1.5rem;border:1px solid var(--border);box-shadow:var(--shadow)}
.header h1{font-size:1.6rem;font-weight:700}
.header h1 span{color:var(--purple)}
.meta{display:flex;gap:1.5rem;margin-top:.6rem;flex-wrap:wrap;font-size:.85rem;color:var(--muted)}
.meta b{color:var(--text)}
.score-row{display:flex;align-items:center;gap:2rem;margin-top:1.25rem}
.ring{position:relative;width:80px;height:80px;flex-shrink:0}
.ring svg{transform:rotate(-90deg)}
.ring-val{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:1.3rem;font-weight:800}
.verdict{font-size:1rem;line-height:1.6;color:var(--muted)}
.verdict b{color:var(--text)}

/* pills */
.pills{display:flex;gap:.75rem;margin-bottom:1.25rem;flex-wrap:wrap}
.pill{flex:1;min-width:110px;text-align:center;padding:.9rem 1rem;border-radius:var(--r);border:1px solid var(--border);background:var(--surface);box-shadow:var(--shadow)}
.pill .n{font-size:1.8rem;font-weight:800;line-height:1}
.pill .l{font-size:.72rem;color:var(--muted);margin-top:.3rem;text-transform:uppercase;letter-spacing:.05em}
.pill.critical .n{color:var(--critical)}
.pill.high .n{color:var(--high)}
.pill.medium .n{color:var(--medium)}
.pill.low .n{color:var(--low)}

/* section */
.sec-head{display:flex;align-items:center;gap:.6rem;padding:.9rem 1.25rem;font-weight:700;font-size:.95rem;border-bottom:1px solid var(--border);background:var(--surface2);border-radius:var(--r) var(--r) 0 0}
.sec-head .cnt{margin-left:auto;background:var(--border);border-radius:20px;padding:.1rem .55rem;font-size:.78rem;color:var(--muted)}

/* issue */
.issue{padding:1.1rem 1.25rem;border-bottom:1px solid var(--border)}
.issue:last-child{border-bottom:none}
.issue-top{display:flex;align-items:flex-start;gap:.75rem;margin-bottom:.5rem}
.badge{padding:.2rem .6rem;border-radius:4px;font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;flex-shrink:0}
.badge.critical{background:rgba(255,71,87,.15);color:var(--critical);border:1px solid rgba(255,71,87,.3)}
.badge.high{background:rgba(255,107,53,.15);color:var(--high);border:1px solid rgba(255,107,53,.3)}
.badge.medium{background:rgba(255,165,2,.15);color:var(--medium);border:1px solid rgba(255,165,2,.3)}
.badge.low{background:rgba(46,213,115,.15);color:var(--low);border:1px solid rgba(46,213,115,.3)}
.issue-title{font-weight:600;font-size:.95rem}
.issue-line{color:var(--muted);font-size:.8rem;margin-left:auto;flex-shrink:0}
.issue-desc{color:var(--muted);font-size:.88rem;line-height:1.6;margin-bottom:.6rem}
.fix-label{font-size:.72rem;color:var(--muted);margin-bottom:.35rem;text-transform:uppercase;letter-spacing:.05em}
.fix{background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:.7rem 1rem;font-family:monospace;font-size:.85rem;color:var(--green);white-space:pre-wrap;word-break:break-all}

/* warn / sug */
.warn,.sug{padding:.85rem 1.25rem;border-bottom:1px solid var(--border)}
.warn:last-child,.sug:last-child{border-bottom:none}
.warn-title{font-weight:600;font-size:.9rem;color:var(--medium);margin-bottom:.3rem}
.warn-desc,.sug-text{color:var(--muted);font-size:.87rem;line-height:1.5}
.sug-text::before{content:"→ ";color:var(--blue);font-weight:700}

.empty{padding:1.5rem;text-align:center;color:var(--muted);font-size:.9rem}
.empty::before{content:"✓ ";color:var(--green)}

.footer{text-align:center;color:var(--muted);font-size:.8rem;margin-top:2rem;padding-top:1rem;border-top:1px solid var(--border)}
"""


def _score_color(score: int) -> str:
    if score >= 80:
        return "#2ed573"
    if score >= 60:
        return "#ffa502"
    return "#ff4757"


def _ring(score: int) -> str:
    color = _score_color(score)
    r = 34
    circ = 2 * math.pi * r
    dash = circ * score / 100
    return (
        f'<div class="ring">'
        f'<svg width="80" height="80" viewBox="0 0 80 80">'
        f'<circle cx="40" cy="40" r="{r}" fill="none" stroke="#2e3150" stroke-width="8"/>'
        f'<circle cx="40" cy="40" r="{r}" fill="none" stroke="{color}" stroke-width="8" '
        f'stroke-dasharray="{dash:.1f} {circ:.1f}" stroke-linecap="round"/>'
        f'</svg>'
        f'<div class="ring-val" style="color:{color}">{score}</div>'
        f'</div>'
    )


def _issue_card(issue: dict) -> str:
    sev   = issue.get("severity", "low")
    line  = f'line {issue["line"]}' if issue.get("line") else ""
    fix   = issue.get("fix", "")
    fix_html = f'<div class="fix-label">Исправление</div><div class="fix">{fix}</div>' if fix else ""
    return (
        f'<div class="issue">'
        f'<div class="issue-top">'
        f'<span class="badge {sev}">{sev}</span>'
        f'<span class="issue-title">{issue.get("title", "")}</span>'
        f'<span class="issue-line">{line}</span>'
        f'</div>'
        f'<div class="issue-desc">{issue.get("description", "")}</div>'
        f'{fix_html}'
        f'</div>'
    )


def _section(icon: str, title: str, items_html: str, count: int) -> str:
    return (
        f'<div class="card">'
        f'<div class="sec-head">{icon} {title}<span class="cnt">{count}</span></div>'
        f'{items_html}'
        f'</div>'
    )


def build_html(data: dict, source_name: str = "") -> str:
    score       = data.get("score", 0)
    summary     = data.get("summary", "")
    issues      = data.get("issues", [])
    warnings    = data.get("warnings", [])
    suggestions = data.get("suggestions", [])
    stats       = data.get("stats", {})
    filename    = data.get("file", source_name)
    lang        = data.get("language", "")
    lines       = data.get("lines", "")

    meta = "".join([
        f'<span><b>{filename}</b></span>' if filename else "",
        f'<span>Язык: <b>{lang}</b></span>' if lang else "",
        f'<span>Строк: <b>{lines}</b></span>' if lines else "",
    ])

    header = (
        f'<div class="header">'
        f'<h1>Code Sanitizer <span>Report</span></h1>'
        f'<div class="meta">{meta}</div>'
        f'<div class="score-row">'
        f'{_ring(score)}'
        f'<div class="verdict"><b>Вердикт:</b> {summary}</div>'
        f'</div></div>'
    )

    pills = "".join(
        f'<div class="pill {s}"><div class="n">{stats.get(s, 0)}</div><div class="l">{s}</div></div>'
        for s in _SEVERITY_ORDER
    ) if stats else ""

    sorted_issues = sorted(issues, key=lambda x: _SEVERITY_ORDER.index(x.get("severity", "low")))
    issues_html   = "".join(_issue_card(i) for i in sorted_issues) or '<div class="empty">Проблем не найдено</div>'
    warns_html    = "".join(
        f'<div class="warn"><div class="warn-title">{w.get("title","")}</div>'
        f'<div class="warn-desc">{w.get("description","")}</div></div>'
        for w in warnings
    ) or '<div class="empty">Предупреждений нет</div>'
    sugs_html = "".join(
        f'<div class="sug"><div class="sug-text">{s}</div></div>'
        for s in suggestions
    ) or '<div class="empty">Рекомендаций нет</div>'

    body = (
        header
        + (f'<div class="pills">{pills}</div>' if pills else "")
        + _section("🔴", "Проблемы", issues_html, len(issues))
        + _section("⚠️", "Предупреждения", warns_html, len(warnings))
        + _section("💡", "Рекомендации", sugs_html, len(suggestions))
        + '<div class="footer">Generated by <b>mcp-code-sanitizer</b> · Powered by Groq</div>'
    )

    return (
        f'<!DOCTYPE html><html lang="ru"><head>'
        f'<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>Code Sanitizer — {filename or "Отчёт"}</title>'
        f'<style>{_CSS}</style></head>'
        f'<body><div class="wrap">{body}</div></body></html>'
    )


async def generate_report(
    analysis_json: str,
    output_path: str = "",
    source_name: str = "",
) -> str:
    """
    Генерирует красивый HTML-отчёт из результата analyze_code / analyze_file.

    Args:
        analysis_json: JSON-строка из analyze_code или analyze_file.
        output_path:   Путь для сохранения HTML (необязательно).
        source_name:   Название файла/фрагмента для заголовка.

    Returns:
        JSON с полями html и saved_to.
    """
    try:
        data = json.loads(analysis_json)
    except json.JSONDecodeError as e:
        return error_response("Невалидный JSON в analysis_json", str(e))

    html     = build_html(data, source_name=source_name)
    saved_to = ""

    if output_path:
        out = Path(output_path).expanduser().resolve()
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(html, encoding="utf-8")
            saved_to = str(out)
        except OSError as e:
            return error_response("Не удалось сохранить файл", str(e))

    return json.dumps({"html": html, "saved_to": saved_to, "length": len(html)}, ensure_ascii=False)