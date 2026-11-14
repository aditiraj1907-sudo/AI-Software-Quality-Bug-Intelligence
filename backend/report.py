"""Builds the software quality report (Markdown) from the stored project."""
from __future__ import annotations

from datetime import date

ADVICE = {
    "Security": "Treat Security findings as release blockers: use parameterized queries, avoid eval and shell strings, escape output, and move secrets to environment variables.",
    "Logic": "Fix Logic findings next. They produce wrong results without any error message, so add a unit test for each one.",
    "Error handling": "Stop swallowing errors. Log them with context and handle each promise rejection and exception explicitly.",
    "Performance": "Run independent requests in parallel and look for repeated work inside loops.",
    "Resource management": "Use with-blocks or try/finally so files and connections always close.",
    "Maintainability": "Break up deeply nested or long functions and turn TODO notes into tracked issues.",
    "Code quality": "Add a linter (ESLint for JavaScript, Ruff for Python) to CI so style issues are caught automatically.",
}
LABEL = {"critical": "Critical", "high": "High", "medium": "Medium", "low": "Low"}
LANGUAGE = {"py": "Python", "js": "JavaScript"}


def build_markdown(files: list[dict], stats: dict, top_findings: list[dict], today: date | None = None) -> str:
    today = today or date.today()
    when = f"{today.day} {today.strftime('%B %Y')}"  # avoids %-d, which Windows does not support
    counts, issues = stats["counts"], stats["issues"]
    lines = [
        "# Software quality report",
        "",
        f"Generated {when} · {len(files)} file{'' if len(files) == 1 else 's'} · {stats['loc']} lines of code",
        "",
        "## Summary",
        "",
        f"Overall quality score: **{stats['score']}/100 (grade {stats['grade']})**. "
        f"{issues} issue{'' if issues == 1 else 's'} found: {counts['critical']} critical, {counts['high']} high, "
        f"{counts['medium']} medium, {counts['low']} low.",
        "",
    ]
    urgent = counts["critical"] + counts["high"]
    if urgent:
        lines += [f"**{urgent} issues are critical or high severity** and should be fixed before the next release.", ""]
    lines += ["## Files", "", "| File | Language | Lines | Issues | Score |", "| --- | --- | --- | --- | --- |"]
    for f in files:
        lines.append(f"| {f['name']} | {LANGUAGE[f['language']]} | {f['loc']} | {f['issues']} | {f['score']} ({f['grade']}) |")
    lines += ["", "## Issues by category", "", "| Category | Issues |", "| --- | --- |"]
    for category, n in stats["categories"].items():
        lines.append(f"| {category} | {n} |")
    lines += ["", "## Highest-risk issues", ""]
    for f in top_findings[:6]:
        lines.append(f"- **{LABEL[f['severity']]} · {f['title']}** in `{f['file']}:{f['line']}` (risk {f['risk']}). {f['fix']}")
    lines += ["", "## Recommendations", ""]
    advice = [ADVICE[c] for c in stats["categories"] if c in ADVICE]
    lines += [f"- {a}" for a in advice] or ["- No issues were found by the current rules. Keep running the scan in CI."]
    return "\n".join(lines)
