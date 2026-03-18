import logging
import sqlite3

from lastperson07.runtime import DATA_DIR

log = logging.getLogger(__name__)

_DB = DATA_DIR / "lastperson07.db"


def _connect():
    conn = sqlite3.connect(_DB, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def lastperson07_db_init():
    with _connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS sessions "
            "(uid INTEGER PRIMARY KEY, session TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS captions "
            "(uid INTEGER PRIMARY KEY, caption TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS users "
            "(uid INTEGER PRIMARY KEY, first_seen INTEGER NOT NULL DEFAULT (strftime('%s','now')))"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS downloads "
            "(uid INTEGER PRIMARY KEY, count INTEGER NOT NULL DEFAULT 0)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS batch_limits "
            "(uid INTEGER PRIMARY KEY, limit_val INTEGER NOT NULL DEFAULT 50)"
        )
    log.info("DB ready: %s", _DB)


# ── user registry ─────────────────────────────────────────────────────────────

def lastperson07_register_user(uid: int):
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (uid) VALUES (?)", (uid,)
        )


def lastperson07_get_user_count() -> int:
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
    return row[0] if row else 0


def lastperson07_get_all_uids() -> list[int]:
    with _connect() as conn:
        rows = conn.execute("SELECT uid FROM users").fetchall()
    return [r[0] for r in rows]


# ── download tracking ─────────────────────────────────────────────────────────

def lastperson07_increment_downloads(uid: int, count: int = 1):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO downloads (uid, count) VALUES (?, ?) "
            "ON CONFLICT(uid) DO UPDATE SET count = count + excluded.count",
            (uid, count),
        )


def lastperson07_get_total_downloads() -> int:
    with _connect() as conn:
        row = conn.execute("SELECT SUM(count) FROM downloads").fetchone()
    return row[0] or 0


def lastperson07_get_user_downloads(uid: int) -> int:
    with _connect() as conn:
        row = conn.execute("SELECT count FROM downloads WHERE uid = ?", (uid,)).fetchone()
    return row[0] if row else 0


# ── batch limit ───────────────────────────────────────────────────────────────

def lastperson07_save_batch_limit(uid: int, limit_val: int):
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO batch_limits (uid, limit_val) VALUES (?, ?)",
            (uid, limit_val),
        )


def lastperson07_load_batch_limit(uid: int) -> int:
    """Returns user's batch limit. 0 = unlimited."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT limit_val FROM batch_limits WHERE uid = ?", (uid,)
        ).fetchone()
    return row[0] if row else 50


def lastperson07_save_session(uid: int, session: str):
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sessions (uid, session) VALUES (?, ?)",
            (uid, session),
        )


def lastperson07_load_session(uid: int):
    with _connect() as conn:
        row = conn.execute(
            "SELECT session FROM sessions WHERE uid = ?",
            (uid,),
        ).fetchone()
    return row[0] if row else None


def lastperson07_delete_session(uid: int):
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE uid = ?", (uid,))

def lastperson07_save_caption(uid: int, caption: str):
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO captions (uid, caption) VALUES (?, ?)",
            (uid, caption),
        )

def lastperson07_load_caption(uid: int):
    with _connect() as conn:
        row = conn.execute(
            "SELECT caption FROM captions WHERE uid = ?",
            (uid,),
        ).fetchone()
    return row[0] if row else None

def lastperson07_delete_caption(uid: int):
    with _connect() as conn:
        conn.execute("DELETE FROM captions WHERE uid = ?", (uid,))
