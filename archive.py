"""Archive per-thread reply-count history in SQLite and compute time-window rankings."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from collect import BoardResult

SCHEMA = """
CREATE TABLE IF NOT EXISTS threads (
  board TEXT NOT NULL,
  dat_id TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  PRIMARY KEY (board, dat_id)
);

CREATE TABLE IF NOT EXISTS observations (
  board TEXT NOT NULL,
  dat_id TEXT NOT NULL,
  hour_bucket INTEGER NOT NULL,
  res_count INTEGER NOT NULL,
  PRIMARY KEY (board, dat_id, hour_bucket)
);
CREATE INDEX IF NOT EXISTS idx_observations_bucket ON observations(hour_bucket);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def _hour_bucket(dt: datetime) -> int:
    return int(dt.replace(minute=0, second=0, microsecond=0).timestamp())


def record_observations(conn: sqlite3.Connection, board_results: list[BoardResult], now: datetime) -> None:
    bucket = _hour_bucket(now)
    for board in board_results:
        if not board.ok:
            continue
        for t in board.threads:
            conn.execute(
                "INSERT INTO threads(board, dat_id, title, url, created_at) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(board, dat_id) DO UPDATE SET title=excluded.title, url=excluded.url",
                (board.key, t.dat_id, t.title, t.url, int(t.created_at.timestamp())),
            )
            conn.execute(
                "INSERT INTO observations(board, dat_id, hour_bucket, res_count) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(board, dat_id, hour_bucket) DO UPDATE SET res_count=excluded.res_count",
                (board.key, t.dat_id, bucket, t.res_count),
            )


def prune(conn: sqlite3.Connection, now: datetime, retention_days: int) -> None:
    cutoff = _hour_bucket(now - timedelta(days=retention_days))
    conn.execute("DELETE FROM observations WHERE hour_bucket < ?", (cutoff,))
    conn.execute(
        "DELETE FROM threads WHERE NOT EXISTS ("
        "  SELECT 1 FROM observations"
        "  WHERE observations.board = threads.board AND observations.dat_id = threads.dat_id"
        ")"
    )


def compute_deltas(
    conn: sqlite3.Connection, board_results: list[BoardResult], now: datetime, window_hours: float
) -> list[dict]:
    """Reply-count increase over the trailing window for every currently-listed thread.

    Threads younger than the window (no observation at or before the cutoff) count
    from creation, i.e. their full current res_count.
    """
    cutoff = _hour_bucket(now - timedelta(hours=window_hours))
    rows: list[dict] = []
    for board in board_results:
        if not board.ok:
            continue
        for t in board.threads:
            row = conn.execute(
                "SELECT res_count FROM observations "
                "WHERE board = ? AND dat_id = ? AND hour_bucket <= ? "
                "ORDER BY hour_bucket DESC LIMIT 1",
                (board.key, t.dat_id, cutoff),
            ).fetchone()
            baseline = row[0] if row else 0
            delta = max(t.res_count - baseline, 0)
            rows.append(
                {
                    "board": board.key,
                    "title": t.title,
                    "url": t.url,
                    "res_count": t.res_count,
                    "delta": delta,
                }
            )
    return rows


def top_n_by_delta(rows: list[dict], n: int, board_key: str | None = None) -> list[dict]:
    filtered = rows if board_key is None else [r for r in rows if r["board"] == board_key]
    return sorted(filtered, key=lambda r: r["delta"], reverse=True)[:n]
