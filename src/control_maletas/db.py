import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1

_SCHEMA_V1 = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    starts_at TEXT,
    ends_at TEXT,
    license_id TEXT,
    active INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE zones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    capacity INTEGER NOT NULL,
    UNIQUE(event_id, code)
);

CREATE TABLE locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id INTEGER NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    occupied INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    full_name_norm TEXT NOT NULL,
    dni TEXT NOT NULL,
    phone TEXT,
    notes TEXT,
    ticket_code TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE(event_id, ticket_code)
);

CREATE TABLE luggage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    ticket_code TEXT NOT NULL,
    description TEXT,
    location_id INTEGER REFERENCES locations(id),
    status TEXT NOT NULL DEFAULT 'stored' CHECK (status IN ('stored','delivered')),
    stored_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    delivered_at TEXT
);

CREATE TABLE licenses (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    event_name TEXT,
    starts_at TEXT,
    ends_at TEXT,
    max_people INTEGER,
    raw_file TEXT NOT NULL,
    activated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX idx_people_dni ON people(event_id, dni);
CREATE INDEX idx_people_name ON people(full_name_norm);
CREATE INDEX idx_luggage_ticket ON luggage(ticket_code);
CREATE INDEX idx_luggage_person ON luggage(person_id);
"""

_MIGRATIONS = {1: _SCHEMA_V1}


def connect(path: str | Path = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn


def _current_version(conn: sqlite3.Connection) -> int:
    has = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='meta'"
    ).fetchone()
    if not has:
        return 0
    row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    return int(row["value"]) if row else 0


def migrate(conn: sqlite3.Connection) -> None:
    version = _current_version(conn)
    for target in range(version + 1, SCHEMA_VERSION + 1):
        conn.executescript(_MIGRATIONS[target])
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version', ?)",
                (str(target),),
            )
