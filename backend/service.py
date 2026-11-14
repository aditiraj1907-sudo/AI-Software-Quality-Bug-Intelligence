"""Application logic: analysis, the project (files + findings in the database), and the report."""
from __future__ import annotations

from pathlib import Path

from database import db
from ml.model import SEVERITIES, get_model

from . import report
from .analyzer import RULES, WEIGHT, analyze, detect_language, grade_of, language_from_name
from .analyzer.parsing import round_half_up

SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
SAMPLE_ORDER = ["checkout.js", "auth.py", "report_export.py", "cart.js", "utils.js"]

PRIOR_WEIGHT = 0.3  # share of a rule's own default severity in the final prediction
_rule_cache: dict[str, dict] = {}


# ------------------------------------------------------------ prediction

def predict_rule(rule) -> dict:
    """Severity for a rule: 70% ML model on the rule description, 30% the rule's default."""
    cached = _rule_cache.get(rule.id)
    if cached:
        return cached
    model_probs = get_model().severity_probs(rule.description)
    probs = {c: (1 - PRIOR_WEIGHT) * model_probs[c] + (PRIOR_WEIGHT if c == rule.severity else 0.0) for c in SEVERITIES}
    best = max(probs, key=probs.get)
    result = {
        "severity": best,
        "confidence": probs[best],
        "probs": probs,
        "risk": round_half_up(100 * sum(probs[c] * WEIGHT[c] for c in SEVERITIES)),
    }
    _rule_cache[rule.id] = result
    return result


def rules_overview() -> list[dict]:
    out = []
    for r in RULES:
        p = predict_rule(r)
        out.append(
            {
                "id": r.id, "title": r.title, "language": r.lang, "category": r.category,
                "defaultSeverity": r.severity, "predictedSeverity": p["severity"], "confidence": p["confidence"],
            }
        )
    return out


# -------------------------------------------------------------- analysis

def resolve_language(code: str, language: str, filename: str | None) -> str:
    if language in ("js", "py"):
        return language
    return language_from_name(filename) or detect_language(code)


def analyze_code(code: str, language: str = "auto", filename: str | None = None) -> dict:
    return analyze(code, resolve_language(code, language, filename), predict_rule)


# --------------------------------------------------------------- project

def _stats(conn) -> dict:
    totals = db.project_totals(conn)
    counts = db.severity_counts(conn)
    score = round_half_up(totals["weighted"] / totals["loc"]) if totals["loc"] else 100
    return {
        "score": score,
        "grade": grade_of(score),
        "loc": totals["loc"],
        "issues": sum(counts.values()),
        "counts": counts,
        "categories": db.category_counts(conn),
    }


def _snapshot(conn) -> None:
    stats = _stats(conn)
    db.record_scan(conn, stats["score"], db.count_files(conn), stats["counts"])


def project_state() -> dict:
    with db.session() as conn:
        return {"files": db.list_files(conn), "stats": _stats(conn), "history": db.recent_scan_scores(conn, 10)}


def add_file(code: str, language: str = "auto", filename: str | None = None) -> dict:
    lang = resolve_language(code, language, filename)
    result = analyze(code, lang, predict_rule)
    with db.session() as conn:
        name = (filename or "").strip() or f"snippet-{db.next_file_number(conn)}.{lang}"
        file_id = db.insert_file(conn, name, result, code)
        _snapshot(conn)
    return {"id": file_id, "name": name, "language": lang, "score": result["score"], "grade": result["grade"],
            "issues": len(result["findings"])}


def remove_file(file_id: int) -> bool:
    with db.session() as conn:
        removed = db.delete_file(conn, file_id)
        if removed:
            _snapshot(conn)
    return removed


def load_samples() -> list[dict]:
    out = []
    for name in SAMPLE_ORDER:
        path = SAMPLES_DIR / name
        if path.exists():
            out.append({"key": path.stem, "name": name, "language": language_from_name(name),
                        "code": path.read_text(encoding="utf-8")})
    return out


def reset_to_samples() -> None:
    with db.session() as conn:
        db.clear_project(conn)
        for s in load_samples():
            result = analyze(s["code"], s["language"], predict_rule)
            db.insert_file(conn, s["name"], result, s["code"])
            _snapshot(conn)  # one history point per file added: the trend shows quality as the project grows


def ensure_seeded() -> None:
    """Fill a brand-new database with the sample project (never touches existing data)."""
    with db.session() as conn:
        fresh = db.count_files(conn) == 0 and db.count_scans(conn) == 0
    if fresh:
        reset_to_samples()


def findings(severity: str | None, category: str | None, file: str | None) -> list[dict]:
    with db.session() as conn:
        return db.list_findings(conn, severity, category, file)


def build_report() -> dict:
    with db.session() as conn:
        files = db.list_files(conn)
        stats = _stats(conn)
        top = db.list_findings(conn)[:6]
    return {"markdown": report.build_markdown(files, stats, top), "files": len(files)}
