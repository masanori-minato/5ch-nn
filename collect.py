"""Fetch and parse subject.txt thread lists from configured 5ch boards."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import requests
import yaml

SUBJECT_LINE_RE = re.compile(r"^(\d+)\.dat<>(.*) \((\d+)\)\s*$")


@dataclass
class Thread:
    dat_id: str
    title: str
    res_count: int
    url: str
    created_at: datetime


@dataclass
class BoardResult:
    key: str
    name: str
    ok: bool
    error: str | None = None
    threads: list[Thread] = field(default_factory=list)


def load_config(path: str = "boards.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _read_cgi_url(board_url: str, board_key: str, dat_id: str) -> str:
    origin = urlsplit(board_url)
    return f"{origin.scheme}://{origin.netloc}/test/read.cgi/{board_key}/{dat_id}/l50"


def parse_subject_txt(raw_text: str, board_key: str, board_url: str) -> tuple[list[Thread], int]:
    threads: list[Thread] = []
    skipped = 0
    now = datetime.now(timezone.utc)
    for line in raw_text.splitlines():
        if not line.strip():
            continue
        m = SUBJECT_LINE_RE.match(line)
        if not m:
            skipped += 1
            continue
        dat_id, title, res_count = m.group(1), m.group(2), int(m.group(3))
        created_at = datetime.fromtimestamp(int(dat_id), tz=timezone.utc)
        if created_at > now + timedelta(days=1):
            # 5ch pins site-wide notice/ad threads using deliberately far-future
            # dat_ids so they always sort first in legacy 2ch clients. These are
            # not real discussion threads, so they're excluded entirely.
            skipped += 1
            continue
        threads.append(
            Thread(
                dat_id=dat_id,
                title=title,
                res_count=res_count,
                url=_read_cgi_url(board_url, board_key, dat_id),
                created_at=created_at,
            )
        )
    return threads, skipped


def _fetch_subject_txt(session: requests.Session, board_url: str, timeout: int, max_retries: int) -> str:
    url = board_url.rstrip("/") + "/subject.txt"
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.content.decode("cp932", errors="replace")
        except Exception as exc:  # noqa: BLE001 - broad by design, board-level failure isolation
            last_exc = exc
            if attempt < max_retries:
                continue
    raise last_exc  # type: ignore[misc]


def fetch_all_boards(cfg: dict) -> list[BoardResult]:
    session = requests.Session()
    session.headers.update({"User-Agent": cfg["user_agent"]})

    timeout = cfg.get("timeout", 15)
    max_retries = cfg.get("max_retries", 1)
    request_delay = cfg.get("request_delay", 2)

    results: list[BoardResult] = []
    boards = cfg["boards"]
    for i, board in enumerate(boards):
        key, name, url = board["key"], board["name"], board["url"]
        try:
            raw_text = _fetch_subject_txt(session, url, timeout, max_retries)
            threads, skipped = parse_subject_txt(raw_text, key, url)
            print(f"[collect] {key}: {len(threads)} threads ({skipped} unparsed lines skipped)")
            results.append(BoardResult(key=key, name=name, ok=True, threads=threads))
        except Exception as exc:  # noqa: BLE001 - one board failing must not abort the run
            print(f"[collect] {key}: FAILED ({exc})")
            results.append(BoardResult(key=key, name=name, ok=False, error=str(exc)))

        if i < len(boards) - 1:
            time.sleep(request_delay)

    return results


if __name__ == "__main__":
    import json
    import sys

    config = load_config()
    board_results = fetch_all_boards(config)
    dump = [
        {
            "key": r.key,
            "name": r.name,
            "ok": r.ok,
            "error": r.error,
            "thread_count": len(r.threads),
            "sample": [
                {"dat_id": t.dat_id, "title": t.title, "res_count": t.res_count, "url": t.url}
                for t in r.threads[:3]
            ],
        }
        for r in board_results
    ]
    json.dump(dump, sys.stdout, ensure_ascii=False, indent=2)
    print()
