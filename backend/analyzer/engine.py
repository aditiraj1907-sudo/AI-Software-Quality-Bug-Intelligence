"""Runs the rules over a piece of source code and scores the result."""
from __future__ import annotations

import math
import re
from typing import Callable

from .parsing import clean_line, round_half_up
from .rules import RULES, Context, Rule

SEVERITIES = ("critical", "high", "medium", "low")
PENALTY = {"critical": 15, "high": 9, "medium": 4, "low": 1.5}
WEIGHT = {"critical": 1.0, "high": 0.72, "medium": 0.42, "low": 0.14}

_DECISIONS = {
    "py": re.compile(r"\b(?:if|elif|for|while|except|and|or)\b"),
    "js": re.compile(r"\b(?:if|for|while|case|catch)\b|&&|\|\||\?(?![.?])"),
}

# (rule) -> {"severity", "confidence", "probs", "risk"}
RulePredictor = Callable[[Rule], dict]


def grade_of(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 55:
        return "D"
    return "F"


def analyze(code: str, lang: str, predict_rule: RulePredictor) -> dict:
    """Analyze `code` written in `lang` ('js' or 'py').

    `predict_rule` supplies the predicted severity for each rule, so the
    analyzer does not depend on how that prediction is made.
    """
    raw = code.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    clean = [clean_line(line, lang) for line in raw]
    ctx = Context(raw, clean, lang)

    findings = []
    for rule in RULES:
        if rule.lang not in ("any", lang):
            continue
        for i, line in enumerate(raw):
            if not line.strip():
                continue
            try:
                hit = rule.test(clean[i], line, i, ctx)
            except Exception:
                hit = False  # a rule must never break the whole scan
            if not hit:
                continue
            pred = predict_rule(rule)
            findings.append(
                {
                    "ruleId": rule.id,
                    "line": i + 1,
                    "code": line.strip(),
                    "category": rule.category,
                    "title": rule.title,
                    "why": rule.why,
                    "fix": rule.fix,
                    "fixCode": rule.fix_code,
                    "severity": pred["severity"],
                    "confidence": pred["confidence"],
                    "probs": pred["probs"],
                    "risk": pred["risk"],
                }
            )
    findings.sort(key=lambda f: (-f["risk"], f["line"]))

    loc = sum(1 for line in clean if line.strip())
    decisions = len(_DECISIONS[lang].findall("\n".join(clean)))
    penalty = sum(PENALTY[f["severity"]] for f in findings)
    score = max(0, min(100, round_half_up(100 * math.exp(-penalty / max(loc, 30) * 1.1))))

    counts = {s: 0 for s in SEVERITIES}
    categories: dict[str, int] = {}
    for f in findings:
        counts[f["severity"]] += 1
        categories[f["category"]] = categories.get(f["category"], 0) + 1

    return {
        "language": lang,
        "loc": loc,
        "score": score,
        "grade": grade_of(score),
        "decisions": decisions,
        "density": round_half_up(decisions / loc * 100) if loc else 0,
        "counts": counts,
        "categories": categories,
        "findings": findings,
    }
