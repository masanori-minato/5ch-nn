"""Persist collected thread data to Supabase (threads + thread_snapshots)."""

from __future__ import annotations

import os
from datetime import datetime

from dotenv import load_dotenv
from supabase import Client, create_client

from collect import BoardResult

load_dotenv()


def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


def save_snapshot(
    client: Client,
    board_results: list[BoardResult],
    threads: dict,
    now: datetime,
) -> None:
    """Upsert thread identity rows, then append one snapshot row per thread
    for boards that were fetched successfully this run."""

    ok_results = [r for r in board_results if r.ok]

    thread_rows = [
        {
            "board_key": r.key,
            "dat_id": t.dat_id,
            "title": t.title,
            "url": t.url,
            "thread_created_at": t.created_at.isoformat(),
        }
        for r in ok_results
        for t in r.threads
    ]
    if not thread_rows:
        return

    upserted = (
        client.table("threads")
        .upsert(thread_rows, on_conflict="board_key,dat_id")
        .execute()
    )
    thread_id_by_key = {(row["board_key"], row["dat_id"]): row["id"] for row in upserted.data}

    collected_at = now.isoformat()
    snapshot_rows = []
    for r in ok_results:
        for t in r.threads:
            thread_id = thread_id_by_key.get((r.key, t.dat_id))
            entry = threads.get(f"{r.key}:{t.dat_id}")
            if thread_id is None or entry is None:
                continue
            snapshot_rows.append(
                {
                    "thread_id": thread_id,
                    "collected_at": collected_at,
                    "res_count": entry["res_count"],
                    "velocity": entry["velocity"],
                }
            )

    if snapshot_rows:
        client.table("thread_snapshots").insert(snapshot_rows).execute()
