-- SQLite schema for Quality & Bug Intelligence.
-- Applied automatically at startup (all statements are idempotent).

-- One row per analyzed file in the project.
CREATE TABLE IF NOT EXISTS files (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    language    TEXT    NOT NULL CHECK (language IN ('js', 'py')),
    code        TEXT    NOT NULL,
    loc         INTEGER NOT NULL,
    score       INTEGER NOT NULL,
    grade       TEXT    NOT NULL,
    decisions   INTEGER NOT NULL,
    density     INTEGER NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- One row per issue found in a file. Deleting a file deletes its findings.
CREATE TABLE IF NOT EXISTS findings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id     INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    rule_id     TEXT    NOT NULL,
    line        INTEGER NOT NULL,
    code        TEXT    NOT NULL,
    category    TEXT    NOT NULL,
    title       TEXT    NOT NULL,
    severity    TEXT    NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    confidence  REAL    NOT NULL,
    risk        INTEGER NOT NULL,
    why         TEXT    NOT NULL,
    fix         TEXT    NOT NULL,
    fix_code    TEXT    NOT NULL,
    probs       TEXT    NOT NULL  -- JSON: probability of each severity
);

-- A snapshot of project quality, written after every change to the project.
CREATE TABLE IF NOT EXISTS scans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    score       INTEGER NOT NULL,
    files       INTEGER NOT NULL,
    issues      INTEGER NOT NULL,
    critical    INTEGER NOT NULL,
    high        INTEGER NOT NULL,
    medium      INTEGER NOT NULL,
    low         INTEGER NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_findings_file     ON findings(file_id);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_category ON findings(category);
