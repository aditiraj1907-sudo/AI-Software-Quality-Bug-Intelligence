"""SQLite data access. All SQL in the project lives in this file."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA_FILE = Path(__file__).with_name("schema.sql")
DEFAULT_DB = Path(__file__).with_name("bug_intelligence.db")


def db_path() -> Path:
    """Database location. Set QBI_DB to use another file (the tests do)."""
    return Path(os.environ.get("QBI_DB", DEFAULT_DB))


@contextmanager
def session():
    """One connection per unit of work: commits on success, rolls back on error."""
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with session() as conn:
        conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- files

def insert_file(conn, name: str, analysis: dict, code: str) -> int:
    cur = conn.execute(
        "INSERT INTO files (name, language, code, loc, score, grade, decisions, density) VALUES (?,?,?,?,?,?,?,?)",
        (name, analysis["language"], code, analysis["loc"], analysis["score"], analysis["grade"],
         analysis["decisions"], analysis["density"]),
    )
    file_id = cur.lastrowid
    conn.executemany(
        "INSERT INTO findings (file_id, rule_id, line, code, category, title, severity, confidence, risk, why, fix, fix_code, probs)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (file_id, f["ruleId"], f["line"], f["code"], f["category"], f["title"], f["severity"],
             f["confidence"], f["risk"], f["why"], f["fix"], f["fixCode"], json.dumps(f["probs"]))
            for f in analysis["findings"]
        ],
    )
    return file_id


def delete_file(conn, file_id: int) -> bool:
    return conn.execute("DELETE FROM files WHERE id = ?", (file_id,)).rowcount > 0


def clear_project(conn) -> None:
    conn.execute("DELETE FROM files")  # findings go with them (ON DELETE CASCADE)
    conn.execute("DELETE FROM scans")


def next_file_number(conn) -> int:
    return conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM files").fetchone()[0]


def count_files(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]


def count_scans(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]


def list_files(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT f.id, f.name, f.language, f.loc, f.score, f.grade, f.density, f.created_at,"
        " (SELECT COUNT(*) FROM findings x WHERE x.file_id = f.id) AS issues"
        " FROM files f ORDER BY f.id"
    ).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------- findings

def list_findings(conn, severity: str | None = None, category: str | None = None, file: str | None = None) -> list[dict]:
    where, args = [], []
    if severity:
        where.append("x.severity = ?")
        args.append(severity)
    if category:
        where.append("x.category = ?")
        args.append(category)
    if file:
        where.append("f.name = ?")
        args.append(file)
    sql = (
        "SELECT x.id, f.name AS file, x.rule_id, x.line, x.code, x.category, x.title, x.severity,"
        " x.confidence, x.risk, x.why, x.fix, x.fix_code, x.probs"
        " FROM findings x JOIN files f ON f.id = x.file_id"
        + (" WHERE " + " AND ".join(where) if where else "")
        + " ORDER BY x.risk DESC, f.id, x.line"
    )
    out = []
    for r in conn.execute(sql, args).fetchall():
        out.append(
            {
                "id": r["id"], "file": r["file"], "ruleId": r["rule_id"], "line": r["line"], "code": r["code"],
                "category": r["category"], "title": r["title"], "severity": r["severity"],
                "confidence": r["confidence"], "risk": r["risk"], "why": r["why"], "fix": r["fix"],
                "fixCode": r["fix_code"], "probs": json.loads(r["probs"]),
            }
        )
    return out


def severity_counts(conn) -> dict:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for r in conn.execute("SELECT severity, COUNT(*) AS n FROM findings GROUP BY severity"):
        counts[r["severity"]] = r["n"]
    return counts


def category_counts(conn) -> dict:
    rows = conn.execute("SELECT category, COUNT(*) AS n FROM findings GROUP BY category ORDER BY n DESC, category")
    return {r["category"]: r["n"] for r in rows}


def project_totals(conn) -> dict:
    """Lines of code and the line-weighted sum of file scores."""
    r = conn.execute("SELECT COALESCE(SUM(loc), 0) AS loc, COALESCE(SUM(score * loc), 0) AS weighted FROM files").fetchone()
    return {"loc": r["loc"], "weighted": r["weighted"]}


# ---------------------------------------------------------------- scans

def record_scan(conn, score: int, files: int, counts: dict) -> None:
    conn.execute(
        "INSERT INTO scans (score, files, issues, critical, high, medium, low) VALUES (?,?,?,?,?,?,?)",
        (score, files, sum(counts.values()), counts["critical"], counts["high"], counts["medium"], counts["low"]),
    )


def recent_scan_scores(conn, limit: int = 10) -> list[int]:
    rows = conn.execute("SELECT score FROM scans ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [r["score"] for r in reversed(rows)]
