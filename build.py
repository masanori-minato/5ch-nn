"""One-shot orchestrator: collect -> rank -> render."""

from __future__ import annotations

import sys
from datetime import datetime, timezone

import collect
import rank
import render

STATE_PATH = "state/threads.json"
DOCS_PATH = "docs/index.html"


def main() -> int:
    cfg = collect.load_config()
    board_results = collect.fetch_all_boards(cfg)

    state = rank.load_state(STATE_PATH)
    now = datetime.now(timezone.utc)
    new_threads = rank.update_state(state.get("threads", {}), board_results, now)
    rank.save_state(STATE_PATH, {"updated_at": now.isoformat(), "threads": new_threads})

    top_n = cfg.get("top_n", 50)
    ranked = rank.top_n(new_threads, top_n)
    board_rankings = {
        board["key"]: rank.top_n(
            {k: v for k, v in new_threads.items() if v["board"] == board["key"]}, top_n
        )
        for board in cfg["boards"]
    }
    html_str = render.render_html(ranked, board_rankings, now, board_results)
    render.write_html(DOCS_PATH, html_str)

    ok = sum(1 for r in board_results if r.ok)
    print(f"[build] {ok}/{len(board_results)} boards OK, {len(new_threads)} threads tracked, "
          f"{len(ranked)} ranked in docs/index.html")

    if ok == 0:
        print("[build] all boards failed this run", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
