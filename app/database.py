import sqlite3
import os
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from app.config import settings

DB_PATH = str(settings.DB_PATH)
BACKUPS_DIR = settings.BASE_DIR / "backups"

DEFAULT_BANK_NAME = settings.DEFAULT_BANK_NAME
DEFAULT_BANK_CODE = settings.DEFAULT_BANK_CODE
DEFAULT_BANK_COURSE = settings.DEFAULT_BANK_COURSE
DEFAULT_POOL_COUNT = settings.DEFAULT_POOL_COUNT


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def create_database_backup(label: str = "auto", max_revisions: int = 7) -> Path | None:
    """Safely back up SQLite database to BACKUPS_DIR using the SQLite online backup API.
    
    Retains up to max_revisions latest backups and removes older snapshots.
    """
    if not os.path.exists(DB_PATH):
        return None

    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUPS_DIR / f"quiz_backup_{timestamp}_{label}.db"

    source_conn = sqlite3.connect(DB_PATH)
    target_conn = sqlite3.connect(str(backup_path))
    try:
        source_conn.backup(target_conn)
    finally:
        target_conn.close()
        source_conn.close()

    # Prune old backups, keeping latest max_revisions
    existing = sorted(BACKUPS_DIR.glob("quiz_backup_*.db"), key=os.path.getmtime, reverse=True)
    for old_file in existing[max_revisions:]:
        try:
            old_file.unlink()
        except OSError:
            pass

    return backup_path


@contextmanager
def get_db():
    """Context manager for database connections.
    
    Automatically commits on normal block exit, rolls back on any exception,
    and guarantees connection closure.
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    create_database_backup("startup")
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS banks (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL UNIQUE,
            code         TEXT    NOT NULL UNIQUE,   -- prefix of paper codes, e.g. CD -> CD-2026-1
            subject_name TEXT    DEFAULT '',
            course_code  TEXT    DEFAULT '',
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS pools (
            bank_id  INTEGER NOT NULL,
            pool_no  INTEGER NOT NULL,
            name     TEXT    DEFAULT '',
            PRIMARY KEY (bank_id, pool_no)
        );

        CREATE TABLE IF NOT EXISTS questions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            text          TEXT    NOT NULL,
            option_a      TEXT    DEFAULT '',
            option_b      TEXT    DEFAULT '',
            option_c      TEXT    DEFAULT '',
            option_d      TEXT    DEFAULT '',
            correct_opt   TEXT    DEFAULT '',
            pool_id       INTEGER NOT NULL CHECK(pool_id >= 1),
            topic         TEXT,
            times_used    INTEGER DEFAULT 0,
            question_type TEXT    DEFAULT 'objective',
            marks         INTEGER DEFAULT 2,
            bank_id       INTEGER DEFAULT 1,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS papers (
            uid           TEXT    PRIMARY KEY,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
            questions     TEXT    NOT NULL,   -- JSON: list of question snapshots
            answer_key    TEXT    NOT NULL,   -- JSON: {q_index: correct_opt_text}
            paper_no      INTEGER DEFAULT 0,
            subject_name  TEXT    DEFAULT 'Compiler Design',
            course_code   TEXT    DEFAULT 'NCSC302',
            duration      TEXT    DEFAULT '30 Minutes',
            instructions  TEXT    DEFAULT '(i) Tick the correct option for each question (ii) All questions carry 2 marks each',
            paper_type    TEXT    DEFAULT 'objective',
            exam_title    TEXT    DEFAULT 'Quiz 1',
            max_marks     TEXT    DEFAULT '10 (2 marks per question)',
            is_randomized INTEGER DEFAULT 1,
            exam_date     TEXT    DEFAULT '03-Sept-2026',
            marks_per_question TEXT DEFAULT '',
            bank_id       INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS student_results (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no     TEXT    NOT NULL,
            paper_uid   TEXT    NOT NULL REFERENCES papers(uid),
            score       INTEGER NOT NULL,
            breakdown   TEXT    NOT NULL,   -- JSON per-question detail
            entered_by  TEXT    DEFAULT 'TA',
            entered_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(roll_no, paper_uid)
        );
    """)

    conn.commit()

    # ── Default bank (all pre-existing data belongs here) ────────────────
    if not conn.execute("SELECT 1 FROM banks LIMIT 1").fetchone():
        conn.execute(
            "INSERT INTO banks (id, name, code, subject_name, course_code) VALUES (1, ?, ?, ?, ?)",
            (DEFAULT_BANK_NAME, DEFAULT_BANK_CODE, DEFAULT_BANK_NAME, DEFAULT_BANK_COURSE),
        )
        conn.commit()

    # ── Migration: questions table (legacy columns, 5-pool CHECK, bank_id) ─
    q_cols = [row[1] for row in conn.execute("PRAGMA table_info(questions)").fetchall()]
    q_sql = (conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='questions'")
             .fetchone()[0] or "")
    needs_rebuild = ("BETWEEN 1 AND 5" in q_sql) or ("bank_id" not in q_cols) or ("difficulty" in q_cols)

    if needs_rebuild:
        sel_type = "COALESCE(question_type, 'objective')" if "question_type" in q_cols else "'objective'"
        sel_marks = "COALESCE(marks, 2)" if "marks" in q_cols else "2"
        sel_bank = "COALESCE(bank_id, 1)" if "bank_id" in q_cols else "1"
        conn.executescript(f"""
            DROP TABLE IF EXISTS questions_new;
            CREATE TABLE questions_new (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                text          TEXT    NOT NULL,
                option_a      TEXT    DEFAULT '',
                option_b      TEXT    DEFAULT '',
                option_c      TEXT    DEFAULT '',
                option_d      TEXT    DEFAULT '',
                correct_opt   TEXT    DEFAULT '',
                pool_id       INTEGER NOT NULL CHECK(pool_id >= 1),
                topic         TEXT,
                times_used    INTEGER DEFAULT 0,
                question_type TEXT    DEFAULT 'objective',
                marks         INTEGER DEFAULT 2,
                bank_id       INTEGER DEFAULT 1,
                created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO questions_new (id, text, option_a, option_b, option_c, option_d,
                correct_opt, pool_id, topic, times_used, question_type, marks, bank_id, created_at)
            SELECT id, text, option_a, option_b, option_c, option_d,
                correct_opt, pool_id, topic, times_used,
                {sel_type}, {sel_marks}, {sel_bank}, created_at
            FROM questions;
            DROP TABLE questions;
            ALTER TABLE questions_new RENAME TO questions;
        """)

    # ── Migration: papers columns ─────────────────────────────────────────
    paper_cols = [row[1] for row in conn.execute("PRAGMA table_info(papers)").fetchall()]
    if "paper_no" not in paper_cols:
        conn.execute("ALTER TABLE papers ADD COLUMN paper_no INTEGER DEFAULT 0")
        existing = conn.execute(
            "SELECT uid FROM papers ORDER BY created_at ASC, rowid ASC"
        ).fetchall()
        for i, row in enumerate(existing, start=1):
            conn.execute("UPDATE papers SET paper_no = ? WHERE uid = ?", (i, row[0]))

    if "subject_name" not in paper_cols:
        conn.execute("ALTER TABLE papers ADD COLUMN subject_name TEXT DEFAULT 'Compiler Design'")
    if "course_code" not in paper_cols:
        conn.execute("ALTER TABLE papers ADD COLUMN course_code TEXT DEFAULT 'NCSC302'")
    if "duration" not in paper_cols:
        conn.execute("ALTER TABLE papers ADD COLUMN duration TEXT DEFAULT '30 Minutes'")
    if "instructions" not in paper_cols:
        conn.execute("ALTER TABLE papers ADD COLUMN instructions TEXT DEFAULT '(i) Tick the correct option for each question (ii) All questions carry 2 marks each'")
    if "paper_type" not in paper_cols:
        conn.execute("ALTER TABLE papers ADD COLUMN paper_type TEXT DEFAULT 'objective'")
    if "exam_title" not in paper_cols:
        conn.execute("ALTER TABLE papers ADD COLUMN exam_title TEXT DEFAULT 'Quiz 1'")
    if "max_marks" not in paper_cols:
        conn.execute("ALTER TABLE papers ADD COLUMN max_marks TEXT DEFAULT '10 (2 marks per question)'")
    if "is_randomized" not in paper_cols:
        conn.execute("ALTER TABLE papers ADD COLUMN is_randomized INTEGER DEFAULT 1")
    if "exam_date" not in paper_cols:
        conn.execute("ALTER TABLE papers ADD COLUMN exam_date TEXT DEFAULT '03-Sept-2026'")
    if "marks_per_question" not in paper_cols:
        conn.execute("ALTER TABLE papers ADD COLUMN marks_per_question TEXT DEFAULT ''")
    if "bank_id" not in paper_cols:
        conn.execute("ALTER TABLE papers ADD COLUMN bank_id INTEGER DEFAULT 1")

    # ── Migration: questions columns (difficulty & co_tag) ─────────────────
    q_cols = [row[1] for row in conn.execute("PRAGMA table_info(questions)").fetchall()]
    if "difficulty" not in q_cols:
        conn.execute("ALTER TABLE questions ADD COLUMN difficulty TEXT DEFAULT 'MEDIUM'")
    if "co_tag" not in q_cols:
        conn.execute("ALTER TABLE questions ADD COLUMN co_tag TEXT DEFAULT ''")

    conn.commit()

    # ── Pools: make sure every pool in use is registered ──────────────────
    conn.execute(
        """INSERT OR IGNORE INTO pools (bank_id, pool_no, name)
           SELECT DISTINCT bank_id, pool_id, 'Pool ' || pool_id FROM questions"""
    )
    if needs_rebuild:
        # Legacy databases had a fixed set of 5 pools: keep them all available.
        for n in range(1, DEFAULT_POOL_COUNT + 1):
            conn.execute(
                "INSERT OR IGNORE INTO pools (bank_id, pool_no, name) VALUES (1, ?, ?)",
                (n, f"Pool {n}"),
            )
    for bank in conn.execute("SELECT id FROM banks").fetchall():
        has_pool = conn.execute("SELECT 1 FROM pools WHERE bank_id=? LIMIT 1", (bank[0],)).fetchone()
        if not has_pool:
            for n in range(1, DEFAULT_POOL_COUNT + 1):
                conn.execute(
                    "INSERT INTO pools (bank_id, pool_no, name) VALUES (?, ?, ?)",
                    (bank[0], n, f"Pool {n}"),
                )

    conn.commit()
    conn.close()
