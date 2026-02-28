"""
database.py — SQLite job tracker (zero cost, runs locally)
"""
import sqlite3
import os
from datetime import datetime
from config import DB_PATH


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            title            TEXT    NOT NULL,
            company          TEXT,
            location         TEXT,
            url              TEXT    UNIQUE,
            platform         TEXT,
            employment_type  TEXT,
            description      TEXT,
            posted_date      TEXT,

            -- AI scoring fields
            fit_score        INTEGER DEFAULT 0,
            role_match       TEXT,
            matching_skills  TEXT,
            missing_skills   TEXT,
            key_requirement  TEXT,
            ai_summary       TEXT,

            -- Tracking
            date_found       TEXT,
            status           TEXT DEFAULT 'Shortlisted',
            notified         INTEGER DEFAULT 0,
            notes            TEXT,
            created_at       TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS run_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at       TEXT,
            jobs_found   INTEGER,
            jobs_scored  INTEGER,
            jobs_kept    INTEGER,
            email_sent   INTEGER DEFAULT 0
        );
        """)
    print("[DB] Database initialised.")


def job_exists(url: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM jobs WHERE url = ?", (url,)).fetchone()
        return row is not None


def insert_job(job: dict) -> int | None:
    """Insert a new job. Returns row id or None if duplicate."""
    if job_exists(job.get("url", "")):
        return None
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO jobs
              (title, company, location, url, platform, employment_type,
               description, posted_date, date_found)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            job.get("title", ""), job.get("company", ""),
            job.get("location", ""), job.get("url", ""),
            job.get("platform", ""), job.get("employment_type", "Full-time"),
            job.get("description", ""), job.get("posted_date", ""),
            datetime.today().strftime("%Y-%m-%d")
        ))
        return cur.lastrowid


def update_score(job_id: int, score_data: dict):
    with get_conn() as conn:
        conn.execute("""
            UPDATE jobs SET
                fit_score       = ?,
                role_match      = ?,
                matching_skills = ?,
                missing_skills  = ?,
                key_requirement = ?,
                ai_summary      = ?
            WHERE id = ?
        """, (
            score_data.get("fit_score", 0),
            score_data.get("role_match", ""),
            ", ".join(score_data.get("matching_skills", [])),
            ", ".join(score_data.get("missing_skills", [])),
            score_data.get("key_requirement", ""),
            score_data.get("summary", ""),
            job_id
        ))


def get_todays_shortlist(min_score: int = 6) -> list:
    today = datetime.today().strftime("%Y-%m-%d")
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM jobs
            WHERE date_found = ?
              AND fit_score  >= ?
              AND notified   = 0
            ORDER BY fit_score DESC
        """, (today, min_score)).fetchall()
        return [dict(r) for r in rows]


def mark_notified(job_ids: list[int]):
    if not job_ids:
        return
    placeholders = ",".join("?" * len(job_ids))
    with get_conn() as conn:
        conn.execute(f"UPDATE jobs SET notified=1 WHERE id IN ({placeholders})", job_ids)


def log_run(jobs_found, jobs_scored, jobs_kept, email_sent=0):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO run_log (run_at, jobs_found, jobs_scored, jobs_kept, email_sent)
            VALUES (?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), jobs_found, jobs_scored, jobs_kept, email_sent))


def get_stats() -> dict:
    with get_conn() as conn:
        total   = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        today   = conn.execute("SELECT COUNT(*) FROM jobs WHERE date_found=?",
                               (datetime.today().strftime("%Y-%m-%d"),)).fetchone()[0]
        avg     = conn.execute("SELECT AVG(fit_score) FROM jobs WHERE fit_score > 0").fetchone()[0]
        by_plat = conn.execute("SELECT platform, COUNT(*) FROM jobs GROUP BY platform").fetchall()
        return {
            "total": total, "today": today,
            "avg_score": round(avg or 0, 1),
            "by_platform": {r[0]: r[1] for r in by_plat}
        }


if __name__ == "__main__":
    init_db()
    print("Stats:", get_stats())
