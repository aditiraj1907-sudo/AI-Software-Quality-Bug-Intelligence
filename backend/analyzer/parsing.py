"""Light-weight source parsing helpers shared by the rules.

This is not a full parser. It removes strings and comments so that rules do
not fire on text inside them, and it finds where functions and blocks end.
"""
from __future__ import annotations

import math
import re

_STRING = re.compile(r"""(["'`])(?:\\.|(?!\1).)*\1""")
_PY_COMMENT = re.compile(r"#.*$")
_JS_COMMENT = re.compile(r"//.*$")

FN_START = {
    "js": re.compile(r"\bfunction\b[^{]*\{\s*$|=>\s*\{\s*$"),
    "py": re.compile(r"^\s*(?:async\s+)?def\s"),
}


def round_half_up(x: float) -> int:
    return int(math.floor(x + 0.5))


def clean_line(line: str, lang: str) -> str:
    """Blank out string contents and drop the trailing comment."""
    s = _STRING.sub('""', line)
    return _PY_COMMENT.sub("", s) if lang == "py" else _JS_COMMENT.sub("", s)


def indent_of(s: str) -> int:
    return len(s) - len(s.lstrip())


def block_end(clean: list[str], i: int, lang: str) -> int:
    """Index of the last line of the block that starts on line i."""
    if lang == "py":
        base, last = indent_of(clean[i]), i
        for j in range(i + 1, len(clean)):
            if not clean[j].strip():
                continue
            if indent_of(clean[j]) <= base:
                break
            last = j
        return last
    depth, started = 0, False
    limit = min(len(clean), i + 300)
    for j in range(i, limit):
        for ch in clean[j]:
            if ch == "{":
                depth += 1
                started = True
            elif ch == "}":
                depth -= 1
        if started and depth <= 0:
            return j
    return limit - 1


def max_depth(clean: list[str], i: int, end: int, lang: str) -> int:
    """Deepest nesting level between lines i and end (the function body is level 1)."""
    if lang == "py":
        base, unit, deepest = indent_of(clean[i]), 0, 0
        for j in range(i + 1, end + 1):
            if not clean[j].strip():
                continue
            d = indent_of(clean[j]) - base
            if d > 0:
                unit = min(unit, d) if unit else d
                deepest = max(deepest, d)
        return round_half_up(deepest / unit) if unit else 0
    depth = deepest = 0
    for j in range(i, end + 1):
        for ch in clean[j]:
            if ch == "{":
                depth += 1
                deepest = max(deepest, depth)
            elif ch == "}":
                depth -= 1
    return deepest


_PY_HINTS = re.compile(
    r"^\s*(?:def|elif|except|class \w+.*:|from \w+ import|import \w+)\b|:\s*$|\bprint\s*\(|\binput\s*\("
    r"|\b(?:None|True|False)\b|^\s*#|\blen\s*\(",
    re.M,
)
_JS_HINTS = re.compile(r"\b(?:function|const|let|var)\b|=>|;\s*$|\bconsole\.|===|\{\s*$|^\s*\}", re.M)


def detect_language(code: str) -> str:
    """Guess 'py' or 'js' by counting language-specific hints."""
    py = len(_PY_HINTS.findall(code))
    js = len(_JS_HINTS.findall(code))
    return "py" if py > js else "js"


def language_from_name(name: str | None) -> str | None:
    if not name:
        return None
    lower = name.lower()
    if lower.endswith(".py"):
        return "py"
    if lower.endswith((".js", ".mjs", ".ts")):
        return "js"
    return None
