import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "tickets.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer TEXT NOT NULL,
    message TEXT NOT NULL,
    category TEXT,
    priority TEXT,
    sentiment TEXT,
    team TEXT,
    summary TEXT,
    suggested_reply TEXT,
    ai_source TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
