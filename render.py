"""Render the ranked thread list into a single static docs/index.html page."""

from __future__ import annotations

import html
from datetime import datetime, timedelta, timezone

from collect import BoardResult

JST = timezone(timedelta(hours=9))

STYLE = """
body { font-family: "Hiragino Sans", "Yu Gothic", sans-serif; background: #f4f4f4; color: #222;
       max-width: 880px; margin: 0 auto; padding: 16px; }
h1 { font-size: 1.4rem; margin-bottom: 4px; }
.meta { color: #666; font-size: 0.85rem; margin-bottom: 16px; }
ol { list-style: none; margin: 0; padding: 0; }
li { background: #fff; border: 1px solid #ddd; border-radius: 4px; padding: 10px 12px; margin-bottom: 6px;
     display: flex; gap: 10px; align-items: baseline; }
.rank { color: #999; font-weight: bold; min-width: 2em; }
.tag { background: #e8f0fe; color: #1a56db; font-size: 0.75rem; padding: 2px 6px; border-radius: 3px;
       white-space: nowrap; }
.title { flex: 1; }
.title a { color: #222; text-decoration: none; }
.title a:hover { text-decoration: underline; }
.stats { color: #888; font-size: 0.8rem; white-space: nowrap; }
footer { margin-top: 24px; color: #999; font-size: 0.8rem; border-top: 1px solid #ddd; padding-top: 10px; }
footer ul { padding-left: 1.2em; }
"""


def _fmt_jst(dt: datetime) -> str:
    return dt.astimezone(JST).strftime("%Y-%m-%d %H:%M JST")


def _board_status_lines(board_results: list[BoardResult]) -> list[str]:
    lines = []
    for r in board_results:
        status = "OK" if r.ok else f"FAILED ({html.escape(r.error or '')})"
        lines.append(f"{html.escape(r.name)}: {status}")
    return lines


def render_html(ranked: list[dict], generated_at: datetime, board_results: list[BoardResult]) -> str:
    board_names = {r.key: r.name for r in board_results}
    ok_count = sum(1 for r in board_results if r.ok)

    rows = []
    for i, t in enumerate(ranked, start=1):
        tag = html.escape(board_names.get(t["board"], t["board"]))
        # 5ch titles embed literal numeric character refs (e.g. "&#12317;") for
        # glyphs Shift_JIS can't represent. Round-trip through unescape+escape so
        # those render as intended while any literal <, >, & etc. stay safely escaped.
        title = html.escape(html.unescape(t["title"]))
        url = html.escape(t["url"])
        rows.append(
            f"""<li>
  <span class="rank">{i}</span>
  <span class="tag">{tag}</span>
  <span class="title"><a href="{url}" target="_blank" rel="noopener">{title}</a></span>
  <span class="stats">{t['res_count']}レス &middot; {t['velocity']:.1f}/h</span>
</li>"""
        )

    status_lines = "".join(f"<li>{s}</li>" for s in _board_status_lines(board_results))

    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>5ch-nn</title>
<style>{STYLE}</style>
</head>
<body>
<h1>5ch-nn 勢いランキング</h1>
<p class="meta">更新: {_fmt_jst(generated_at)}（15分毎に自動更新） / 板: {ok_count}/{len(board_results)} OK</p>
<ol>
{"".join(rows)}
</ol>
<footer>
<p>個人が趣味で作成した非公式のまとめサイトです。各スレッドへのリンク先は5ch.netの該当板です。</p>
<p>板ステータス:</p>
<ul>{status_lines}</ul>
</footer>
</body>
</html>
"""


def write_html(path: str, html_str: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_str)
