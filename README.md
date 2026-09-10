# 5ch-nn

5ch(5channel)のニュース系掲示板を横断で監視し、「勢い」(直近のレス増加ペース／時)順にスレッドをランキング表示する非公式のまとめサイトです。[2NN](https://www.2nn.jp/)を参考に、個人の趣味として作成しています。

GitHub Actionsが15分毎に各板の`subject.txt`を取得し、`docs/index.html`を再生成してpush → GitHub Pagesで自動公開されます。

**運用上の注意**: GitHub純正の`schedule`トリガーは15分刻みで設定していても内部キューで間引かれ、実際は1時間に1回程度まで遅延することが確認されている（2026-08-13）。そのため実際の15分更新は、外部cronサービスから`workflow_dispatch`をAPI経由で叩くことで実現している。`build.yml`側の`schedule`はhourlyのフォールバックのみ。外部トリガーのセットアップ手順は下記「更新頻度の仕組み」を参照。

### 更新頻度の仕組み（外部トリガー）

1. GitHubで [Fine-grained PAT](https://github.com/settings/personal-access-tokens/new) を発行。対象リポジトリを`5ch-nn`に限定し、Permissions → **Actions: Read and write** を付与。
2. [cron-job.org](https://cron-job.org/)（無料）でアカウント作成し、新規cronジョブを以下の設定で作成:
   - URL: `https://api.github.com/repos/masanori-minato/5ch-nn/actions/workflows/build.yml/dispatches`
   - Method: `POST`
   - Headers: `Authorization: Bearer <PAT>` / `Accept: application/vnd.github+json` / `X-GitHub-Api-Version: 2022-11-28`
   - Body: `{"ref":"main"}`
   - 実行間隔: 15分ごと
3. PATの有効期限が切れたら再発行してcron-job.org側のヘッダーを更新する（既知の保守ポイント）。

## 仕組み

```
collect.py  各板のsubject.txtを取得・パース(Shift_JIS)
     ↓
rank.py     state/threads.json と突き合わせて「現在の勢い」(run間のレス増加速度)を計算・更新
     ↓
db.py       Supabase(Postgres)の threads / thread_snapshots に書き込み(run毎に履歴を蓄積)
     ↓
render.py   docs/index.html を生成（板タブ）
     ↑
build.py    上記を1コマンドで実行するオーケストレーター
```

DB書き込みが失敗してもサイト生成は止めない(板取得失敗時と同じ「一部が落ちても全体は継続する」方針)。

### データベース(Supabase)

`state/threads.json`は最新状態を毎回上書きするだけなので、履歴を残すためにSupabase(Postgres)にも保存している。スキーマは[supabase/migrations/20260910000000_init_schema.sql](supabase/migrations/20260910000000_init_schema.sql)（Supabaseダッシュボードの SQL Editor で実行済み）。

- `boards` — 板マスタ
- `threads` — スレッドの識別情報(board_key + dat_idで一意)
- `thread_snapshots` — 収集run毎のレス数・勢いのスナップショット(履歴)

接続には環境変数`SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`が必要(Supabaseダッシュボード → Project Settings → API から取得)。ローカルは`.env.example`をコピーして`.env`に値を入れる(`.env`はgit管理外)。GitHub Actions側はリポジトリのSecretsに同名で登録する。

対象板・グローバル設定は [boards.yaml](boards.yaml) で管理。サーバーのサブドメインが変わって取得できなくなった板が出たら、[bbsmenu.html](https://menu.5ch.io/bbsmenu.html)で現在のURLを確認してここを更新してください（ページ下部の板ステータス欄で不調な板が分かります）。

## ローカル実行

```
pip install -r requirements.txt
cp .env.example .env  # SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY を入力
python build.py
```

`docs/index.html`・`state/threads.json`が更新されます。「現在の勢い」は1回目は各スレッドの生存時間ベースの平均速度、2回目以降は前回実行との差分から実際の直近速度が計算されます。

## スコープ外（現時点では未実装）

- 週間ランキング・24時間ランキングなどの期間集計（過去に24時間集計を実装していたが運用を取りやめ、削除済み）
- ホットキーワードサイドバー（形態素解析が必要）
- 板別サブページ
- サムネイル画像
