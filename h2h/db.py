"""SQLite-хранилище H2H: туры и очки участников."""
from __future__ import annotations

import sqlite3
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS tours (
    number      INTEGER PRIMARY KEY,
    api_id      TEXT NOT NULL,
    status      TEXT NOT NULL,
    finished_at TEXT
);
CREATE TABLE IF NOT EXISTS scores (
    tour   INTEGER NOT NULL,
    player TEXT    NOT NULL,
    score  INTEGER NOT NULL,
    PRIMARY KEY (tour, player)
);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert_tour(conn: sqlite3.Connection, number: int, api_id: str,
                status: str, finished_at: str | None) -> None:
    conn.execute(
        """INSERT INTO tours(number, api_id, status, finished_at) VALUES(?,?,?,?)
           ON CONFLICT(number) DO UPDATE SET
               api_id=excluded.api_id,
               status=excluded.status,
               finished_at=excluded.finished_at""",
        (number, api_id, status, finished_at),
    )


def upsert_scores(conn: sqlite3.Connection, tour: int, scores: dict[str, int]) -> None:
    conn.executemany(
        """INSERT INTO scores(tour, player, score) VALUES(?,?,?)
           ON CONFLICT(tour, player) DO UPDATE SET score=excluded.score""",
        [(tour, player, score) for player, score in scores.items()],
    )


def tour_scores(conn: sqlite3.Connection, tour: int) -> dict[str, int]:
    rows = conn.execute("SELECT player, score FROM scores WHERE tour=?", (tour,))
    return {r["player"]: r["score"] for r in rows}


def finished_tours(conn: sqlite3.Connection) -> list[int]:
    rows = conn.execute("SELECT number FROM tours WHERE status='FINISHED' ORDER BY number")
    return [r["number"] for r in rows]


def tour_status(conn: sqlite3.Connection, tour: int) -> str | None:
    row = conn.execute("SELECT status FROM tours WHERE number=?", (tour,)).fetchone()
    return row["status"] if row else None


def tour_finished_at(conn: sqlite3.Connection, tour: int) -> datetime | None:
    row = conn.execute("SELECT finished_at FROM tours WHERE number=?", (tour,)).fetchone()
    if not row or not row["finished_at"]:
        return None
    return datetime.fromisoformat(row["finished_at"].replace("Z", "+00:00"))


def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )

