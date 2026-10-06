from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    created_at TEXT NOT NULL,
    photo_count INTEGER NOT NULL DEFAULT 0,
    process_seconds REAL,
    summary_json TEXT
);

CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    rel_path TEXT NOT NULL,
    scene TEXT,
    role TEXT,
    sharpness REAL,
    exposure REAL,
    score REAL,
    face_count INTEGER DEFAULT 0,
    status TEXT NOT NULL,
    reason TEXT,
    duplicate_of INTEGER,
    section TEXT,
    album_order INTEGER
);

CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL,
    label TEXT NOT NULL,
    photo_count INTEGER NOT NULL,
    cover_path TEXT
);

CREATE TABLE IF NOT EXISTS faces (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL,
    photo_id INTEGER NOT NULL,
    person_id INTEGER,
    x INTEGER,
    y INTEGER,
    w INTEGER,
    h INTEGER
);

CREATE INDEX IF NOT EXISTS idx_photos_event ON photos(event_id, status);
CREATE INDEX IF NOT EXISTS idx_faces_event ON faces(event_id);
CREATE INDEX IF NOT EXISTS idx_people_event ON people(event_id);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def session() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
