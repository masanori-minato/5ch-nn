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
archive.py  state/archive.db (SQLite) に1時間バケット単位でレス数を蓄積し、
            ウィンドウ集計（現状は24時間分のみ）でのレス増加数を算出
     ↓
render.py   docs/index.html を生成（期間タブ: 現在の勢い/24時間 × 板タブ）
     ↑
build.py    上記を1コマンドで実行するオーケストレーター
```

対象板・グローバル設定は [boards.yaml](boards.yaml) で管理。サーバーのサブドメインが変わって取得できなくなった板が出たら、[bbsmenu.html](https://menu.5ch.io/bbsmenu.html)で現在のURLを確認してここを更新してください（ページ下部の板ステータス欄で不調な板が分かります）。

`state/archive.db`は過去`archive_retention_days`日分（デフォルト90日）のみ保持し、それより古い観測データは実行のたびに自動で削除されます。表示に使っているのは今のところ24時間ウィンドウ（総合のみ、板別ブレークダウンは未実装）だが、90日分archiveしておくことで将来的に週間ランキングを追加する際に履歴の作り直しが不要になる。デプロイ直後や運用開始直後は24時間ランキングの元になる履歴がまだ無いため、実質「現在のレス数そのまま」に近い並びになる。日数が経つにつれて本来のウィンドウ集計に育っていく。

## ローカル実行

```
pip install requests PyYAML
python build.py
```

`docs/index.html`・`state/threads.json`・`state/archive.db`が更新されます。「現在の勢い」は1回目は各スレッドの生存時間ベースの平均速度、2回目以降は前回実行との差分から実際の直近速度が計算されます。「24時間」はarchive.dbに蓄積された過去のレス数との差分（総合のみ）です。

## スコープ外（現時点では未実装）

- 週間ランキング（archive.pyの`compute_deltas`は`window_hours`可変で既に対応可能。UI配線は後日）
- 24時間ランキングの板別ブレークダウン（現状は総合のみ）
- ホットキーワードサイドバー（形態素解析が必要）
- 板別サブページ
- サムネイル画像
