"""Render the ranked thread list into a single static docs/index.html page."""

from __future__ import annotations

import base64
import html
import re
from datetime import datetime, timedelta, timezone

from collect import BoardResult

JST = timezone(timedelta(hours=9))

# Thread titles end with the poster ("記者") in brackets, e.g. "... [861717324]"
# or "... [おっさん友の会★]". That label is what the NG list matches against.
AUTHOR_RE = re.compile(r"\[([^\[\]]+)\]\s*$")

# "Ikioi bars" favicon: three bars rising in height and in the same
# v-cool/v-mild/v-hot blues used for velocity below, so the tab icon and the
# ranking list read as one system.
FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" class="logo" viewBox="0 0 32 32">
<rect x="0" y="0" width="32" height="32" rx="7" fill="#eaf1fc"/>
<rect x="6.5" y="16" width="5" height="9" rx="1.4" fill="#86b6ef"/>
<rect x="13.5" y="11" width="5" height="14" rx="1.4" fill="#3987e5"/>
<rect x="20.5" y="6" width="5" height="19" rx="1.4" fill="#0d366b"/>
</svg>"""
FAVICON_HREF = "data:image/svg+xml;base64," + base64.b64encode(FAVICON_SVG.encode("utf-8")).decode("ascii")

STYLE = """
:root {
  color-scheme: light;
  --bg: #f4f4f4; --fg: #222; --muted: #666; --footer-fg: #999;
  --card-bg: #fff; --card-border: #ddd; --rank: #999;
  --tag-bg: #e8f0fe; --tag-fg: #1a56db;
  --link: #222;
  --res-bg: #fdece4; --res-fg: #a8431a;
  --v-hot: #0d366b; --v-warm: #1c5cab; --v-mild: #3987e5; --v-cool: #86b6ef;
  --tab-bg: #fff; --tab-border: #ddd; --tab-fg: #444;
  --tab-active-bg: #1a56db; --tab-active-border: #1a56db; --tab-active-fg: #fff;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --bg: #14171d; --fg: #e4e6eb; --muted: #9099a8; --footer-fg: #7b8291;
    --card-bg: #1c212b; --card-border: #2b3140; --rank: #6b7280;
    --tag-bg: #1c3a5e; --tag-fg: #8fc0ff;
    --link: #e4e6eb;
    --res-bg: #3a2418; --res-fg: #ff9d6c;
    --v-hot: #8fc0ff; --v-warm: #5b9de8; --v-mild: #3987e5; --v-cool: #4a6483;
    --tab-bg: #1c212b; --tab-border: #2b3140; --tab-fg: #b8c0cf;
    --tab-active-bg: #3987e5; --tab-active-border: #3987e5; --tab-active-fg: #0b0d12;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --bg: #14171d; --fg: #e4e6eb; --muted: #9099a8; --footer-fg: #7b8291;
  --card-bg: #1c212b; --card-border: #2b3140; --rank: #6b7280;
  --tag-bg: #1c3a5e; --tag-fg: #8fc0ff;
  --link: #e4e6eb;
  --res-bg: #3a2418; --res-fg: #ff9d6c;
  --v-hot: #8fc0ff; --v-warm: #5b9de8; --v-mild: #3987e5; --v-cool: #4a6483;
  --tab-bg: #1c212b; --tab-border: #2b3140; --tab-fg: #b8c0cf;
  --tab-active-bg: #3987e5; --tab-active-border: #3987e5; --tab-active-fg: #0b0d12;
}
body { font-family: "Hiragino Sans", "Yu Gothic", sans-serif; background: var(--bg); color: var(--fg);
       max-width: 880px; margin: 0 auto; padding: 16px; }
.brand { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
.logo { width: 32px; height: 32px; flex: none; }
h1 { font-size: 1.4rem; margin: 0 auto 0 0; }
.theme-toggle { font: inherit; font-size: 0.8rem; padding: 6px 10px; border-radius: 999px;
                border: 1px solid var(--card-border); background: var(--card-bg); color: var(--fg);
                cursor: pointer; white-space: nowrap; }
.theme-toggle:hover { border-color: var(--tag-fg); }
.ng-toggle { font: inherit; font-size: 1rem; line-height: 1; padding: 5px 8px; border-radius: 999px;
             border: 1px solid var(--card-border); background: var(--card-bg); color: var(--fg); cursor: pointer; }
.ng-toggle:hover, .ng-toggle[aria-expanded="true"] { border-color: var(--tag-fg); }
.ng-panel { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 6px;
            padding: 12px; margin-bottom: 12px; font-size: 0.85rem; }
.ng-panel h2 { font-size: 0.95rem; margin: 0 0 4px; }
.ng-help { color: var(--muted); margin: 0 0 8px; }
.ng-form { display: flex; gap: 6px; }
.ng-form input { flex: 1; min-width: 0; font: inherit; padding: 6px 8px; border-radius: 4px;
                 border: 1px solid var(--card-border); background: var(--bg); color: var(--fg); }
.ng-form button, .ng-del { font: inherit; padding: 6px 12px; border-radius: 4px; cursor: pointer;
                           border: 1px solid var(--tab-active-border); background: var(--tab-active-bg);
                           color: var(--tab-active-fg); }
.ng-list { list-style: none; margin: 10px 0 0; padding: 0; display: flex; flex-wrap: wrap; gap: 6px; }
.ng-list li { margin: 0; padding: 3px 4px 3px 10px; gap: 6px; align-items: center; border-radius: 999px; flex-wrap: nowrap; }
.ng-del { padding: 0 7px; border-radius: 999px; background: transparent; color: var(--muted);
          border-color: var(--card-border); }
.ng-del:hover { color: var(--res-fg); border-color: var(--res-fg); }
.ng-count { color: var(--muted); margin: 8px 0 0; }
.meta { color: var(--muted); font-size: 0.85rem; margin-bottom: 16px; }
ol { list-style: none; margin: 0; padding: 0; }
li { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 4px; padding: 10px 12px;
     margin-bottom: 6px; display: flex; gap: 10px; align-items: baseline; }
li[hidden] { display: none; }
.rank { color: var(--rank); font-weight: bold; min-width: 2em; }
.tag { background: var(--tag-bg); color: var(--tag-fg); font-size: 0.75rem; padding: 2px 6px; border-radius: 3px;
       white-space: nowrap; }
.title { flex: 1; }
.title a { color: var(--link); text-decoration: none; }
.title a:hover { text-decoration: underline; }
.stats { font-size: 0.8rem; white-space: nowrap; }
.res { background: var(--res-bg); color: var(--res-fg); font-size: 0.75rem; padding: 2px 6px; border-radius: 3px;
       margin-right: 4px; }
.velocity { font-weight: 600; }
.v-hot { color: var(--v-hot); font-weight: 700; }
.v-warm { color: var(--v-warm); }
.v-mild { color: var(--v-mild); }
.v-cool { color: var(--v-cool); }
.tabs { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.tab-btn { font: inherit; font-size: 0.82rem; padding: 6px 12px; border-radius: 999px;
           border: 1px solid var(--tab-border); background: var(--tab-bg); color: var(--tab-fg); cursor: pointer; }
.tab-btn:hover { border-color: var(--tag-fg); }
.tab-btn.active { background: var(--tab-active-bg); border-color: var(--tab-active-border); color: var(--tab-active-fg); }
footer { margin-top: 24px; color: var(--footer-fg); font-size: 0.8rem; border-top: 1px solid var(--card-border);
         padding-top: 10px; }
footer ul { padding-left: 1.2em; }

@media (max-width: 480px) {
  body { padding: 10px; }
  h1 { font-size: 1.15rem; }
  li { flex-wrap: wrap; padding: 8px 10px; }
  .stats { order: 1; margin-left: auto; }
  .title { order: 2; flex-basis: 100%; margin-top: 4px; }
}
"""

# (tab id, nav label) in display order — a hand-picked subset/order distinct
# from boards.yaml's fetch order, matching how the boards are commonly referred to.
NAV_TABS = [
    ("all", "総合"),
    ("newsplus", "ニュー速＋"),
    ("mnewsplus", "芸スポ＋"),
    ("news", "ニュー速"),
    ("news4plus", "東アジア＋"),
    ("poverty", "ニュー速（嫌儲）"),
]


def _fmt_jst(dt: datetime) -> str:
    return dt.astimezone(JST).strftime("%Y-%m-%d %H:%M JST")


def _board_status_lines(board_results: list[BoardResult]) -> list[str]:
    lines = []
    for r in board_results:
        status = "OK" if r.ok else f"FAILED ({html.escape(r.error or '')})"
        lines.append(f"{html.escape(r.name)}: {status}")
    return lines


def _velocity_class(rank: int, total: int) -> str:
    # Tiered by rank (the list is already velocity-sorted) rather than a fixed
    # threshold, so the coloring stays meaningful whether it's a quiet night
    # or a breaking-news spike.
    frac = rank / total
    if frac <= 0.1:
        return "v-hot"
    if frac <= 0.3:
        return "v-warm"
    if frac <= 0.6:
        return "v-mild"
    return "v-cool"


def _render_rows(items: list[dict], board_names: dict[str, str]) -> str:
    total = len(items)
    rows = []
    for i, t in enumerate(items, start=1):
        tag = html.escape(board_names.get(t["board"], t["board"]))
        # 5ch titles embed literal numeric character refs (e.g. "&#12317;") for
        # glyphs Shift_JIS can't represent. Round-trip through unescape+escape so
        # those render as intended while any literal <, >, & etc. stay safely escaped.
        title = html.escape(html.unescape(t["title"]))
        url = html.escape(t["url"])
        m = AUTHOR_RE.search(html.unescape(t["title"]))
        author = html.escape(m.group(1).strip() if m else "")
        vclass = _velocity_class(i, total)
        metric = f'<span class="velocity {vclass}">{t["velocity"]:.1f}/h</span>'
        rows.append(
            f"""<li data-author="{author}">
  <span class="rank">{i}</span>
  <span class="tag">{tag}</span>
  <span class="title"><a href="{url}" target="_blank" rel="noopener">{title}</a></span>
  <span class="stats"><span class="res">{t['res_count']}レス</span>{metric}</span>
</li>"""
        )
    return "".join(rows)


def render_html(
    rankings: dict[str, list[dict]],
    generated_at: datetime,
    board_results: list[BoardResult],
) -> str:
    board_names = {r.key: r.name for r in board_results}
    ok_count = sum(1 for r in board_results if r.ok)

    nav_buttons = "".join(
        f'<button class="tab-btn board-btn{" active" if tab_id == "all" else ""}" data-tab="{tab_id}">{label}</button>'
        for tab_id, label in NAV_TABS
    )
    panels = "".join(
        f'<ol id="tab-{tab_id}" class="ranklist"{"" if tab_id == "all" else " hidden"}>'
        f"{_render_rows(rankings.get(tab_id, []), board_names)}</ol>"
        for tab_id, _ in NAV_TABS
    )

    status_lines = "".join(f"<li>{s}</li>" for s in _board_status_lines(board_results))

    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>5ch-nn</title>
<link rel="icon" type="image/svg+xml" href="{FAVICON_HREF}">
<script>
(function () {{
  try {{
    var t = localStorage.getItem("5ch-nn-theme");
    if (t === "light" || t === "dark") document.documentElement.setAttribute("data-theme", t);
  }} catch (e) {{}}
}})();
</script>
<style>{STYLE}</style>
</head>
<body>
<div class="brand">
{FAVICON_SVG}
<h1>5ch-nn 勢いランキング</h1>
<button id="ng-toggle" class="ng-toggle" type="button" aria-label="NG設定" aria-expanded="false" aria-controls="ng-panel" title="NG設定">⚙️</button>
<button id="theme-toggle" class="theme-toggle" type="button"></button>
</div>
<section id="ng-panel" class="ng-panel" hidden>
<h2>NG記者</h2>
<p class="ng-help">スレタイ末尾の [ ] 内（例: 861717324、おっさん友の会★）を登録すると、そのスレを非表示にします。設定はこのブラウザに保存されます。</p>
<form id="ng-form" class="ng-form">
<input id="ng-input" type="text" placeholder="記者名を入力" autocomplete="off">
<button type="submit">追加</button>
</form>
<ul id="ng-list" class="ng-list"></ul>
<p id="ng-count" class="ng-count"></p>
</section>
<p class="meta">更新: {_fmt_jst(generated_at)}（15分毎に自動更新） / 板: {ok_count}/{len(board_results)} OK</p>
<nav class="tabs" id="board-nav">{nav_buttons}</nav>
{panels}
<footer>
<p>個人が趣味で作成した非公式のまとめサイトです。各スレッドへのリンク先は5ch.netの該当板です。</p>
<p>板ステータス:</p>
<ul>{status_lines}</ul>
</footer>
<script>
(function () {{
  document.querySelectorAll(".board-btn").forEach(function (btn) {{
    btn.addEventListener("click", function () {{
      document.querySelectorAll(".board-btn").forEach(function (b) {{ b.classList.remove("active"); }});
      btn.classList.add("active");
      document.querySelectorAll(".ranklist").forEach(function (ol) {{ ol.hidden = true; }});
      var panel = document.getElementById("tab-" + btn.dataset.tab);
      if (panel) panel.hidden = false;
    }});
  }});
}})();
(function () {{
  var KEY = "5ch-nn-ng-authors";
  var toggle = document.getElementById("ng-toggle");
  var panel = document.getElementById("ng-panel");
  var form = document.getElementById("ng-form");
  var input = document.getElementById("ng-input");
  var list = document.getElementById("ng-list");
  var count = document.getElementById("ng-count");
  var ng = [];
  try {{ ng = JSON.parse(localStorage.getItem(KEY) || "[]"); }} catch (e) {{}}
  if (!Array.isArray(ng)) ng = [];
  function normalize(s) {{
    // Accept "[name]" pasted with its brackets as well as the bare name.
    return String(s).trim().replace(/^\\[|\\]$/g, "").trim();
  }}
  function save() {{
    try {{ localStorage.setItem(KEY, JSON.stringify(ng)); }} catch (e) {{}}
  }}
  function apply() {{
    var set = {{}};
    ng.forEach(function (a) {{ set[a] = true; }});
    var hidden = 0;
    document.querySelectorAll(".ranklist").forEach(function (ol) {{
      var n = 0;
      ol.querySelectorAll(":scope > li").forEach(function (li) {{
        var hit = set[li.dataset.author] === true;
        li.hidden = hit;
        if (hit) {{ if (ol.id === "tab-all") hidden++; return; }}
        li.querySelector(".rank").textContent = ++n;
      }});
    }});
    count.textContent = ng.length ? "総合で " + hidden + " 件を非表示中" : "";
    list.innerHTML = "";
    ng.forEach(function (a, i) {{
      var li = document.createElement("li");
      var name = document.createElement("span");
      name.textContent = a;
      var del = document.createElement("button");
      del.type = "button";
      del.className = "ng-del";
      del.textContent = "×";
      del.setAttribute("aria-label", a + " をNGから外す");
      del.addEventListener("click", function () {{ ng.splice(i, 1); save(); apply(); }});
      li.appendChild(name);
      li.appendChild(del);
      list.appendChild(li);
    }});
  }}
  toggle.addEventListener("click", function () {{
    panel.hidden = !panel.hidden;
    toggle.setAttribute("aria-expanded", String(!panel.hidden));
    if (!panel.hidden) input.focus();
  }});
  form.addEventListener("submit", function (ev) {{
    ev.preventDefault();
    var a = normalize(input.value);
    if (a && ng.indexOf(a) === -1) {{ ng.push(a); save(); apply(); }}
    input.value = "";
  }});
  apply();
}})();
(function () {{
  var btn = document.getElementById("theme-toggle");
  var root = document.documentElement;
  var KEY = "5ch-nn-theme";
  function current() {{
    return root.getAttribute("data-theme") ||
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  }}
  function updateLabel() {{
    var dark = current() === "dark";
    btn.textContent = dark ? "☀️ ライト" : "🌙 ダーク";
    btn.setAttribute("aria-pressed", String(dark));
    btn.setAttribute("aria-label", "ダークモード切り替え");
  }}
  btn.addEventListener("click", function () {{
    var next = current() === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try {{ localStorage.setItem(KEY, next); }} catch (e) {{}}
    updateLabel();
  }});
  updateLabel();
}})();
</script>
</body>
</html>
"""


def write_html(path: str, html_str: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_str)
