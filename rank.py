"""Track per-thread reply velocity across runs and rank threads by it."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from collect import BoardResult

MIN_AGE_HOURS = 1 / 12  # 5 min floor for a brand-new thread's first velocity estimate
MIN_ELAPSED_HOURS = 1 / 120  # 30 sec floor before trusting a fresh delta

EMPTY_STATE = {"updated_at": None, "threads": {}}


def load_state(path: str) -> dict:
    if not os.path.exists(path):
        return {"updated_at": None, "threads": {}}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(path: str, state: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s)


def _hours_between(earlier: datetime, later: datetime) -> float:
    return (later - earlier).total_seconds() / 3600


def update_state(old_threads: dict, board_results: list[BoardResult], now: datetime) -> dict:
    new_threads: dict = {}

    for board in board_results:
        if not board.ok:
            # Fetch failed this cycle: carry this board's previous entries forward
            # unchanged rather than pruning them (a transient failure must not
            # silently wipe an entire board's ranking).
            for key, entry in old_threads.items():
                if entry["board"] == board.key:
                    new_threads[key] = entry
            continue

        for thread in board.threads:
            key = f"{board.key}:{thread.dat_id}"
            prev = old_threads.get(key)

            if prev is None:
                age_h = max(_hours_between(thread.created_at, now), MIN_AGE_HOURS)
                velocity = thread.res_count / age_h
                new_threads[key] = {
                    "board": board.key,
                    "title": thread.title,
                    "url": thread.url,
                    "created_at": _iso(thread.created_at),
                    "first_seen_at": _iso(now),
                    "last_seen_at": _iso(now),
                    "res_count": thread.res_count,
                    "last_res_count": thread.res_count,
                    "velocity": round(velocity, 2),
                }
            else:
                elapsed_h = _hours_between(_parse_iso(prev["last_seen_at"]), now)
                delta = thread.res_count - prev["res_count"]
                if elapsed_h >= MIN_ELAPSED_HOURS:
                    velocity = max(delta, 0) / elapsed_h
                else:
                    velocity = prev["velocity"]
                new_threads[key] = {
                    "board": board.key,
                    "title": thread.title,
                    "url": thread.url,
                    "created_at": prev["created_at"],
                    "first_seen_at": prev["first_seen_at"],
                    "last_seen_at": _iso(now),
                    "res_count": thread.res_count,
                    "last_res_count": thread.res_count,
                    "velocity": round(velocity, 2),
                }

    return new_threads


def top_n(threads: dict, n: int) -> list[dict]:
    return sorted(threads.values(), key=lambda t: t["velocity"], reverse=True)[:n]
