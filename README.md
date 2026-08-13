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
rank.py     state/threads.json と突き合わせてレス増加速度(勢い)を計算・更新
     ↓
render.py   docs/index.html を生成
     ↑
build.py    上記を1コマンドで実行するオーケストレーター
```

対象板・グローバル設定は [boards.yaml](boards.yaml) で管理。サーバーのサブドメインが変わって取得できなくなった板が出たら、[bbsmenu.html](https://menu.5ch.io/bbsmenu.html)で現在のURLを確認してここを更新してください（ページ下部の板ステータス欄で不調な板が分かります）。

## ローカル実行

```
pip install requests PyYAML
python build.py
```

`docs/index.html`と`state/threads.json`が更新されます。1回目は各スレッドの生存時間ベースの平均速度、2回目以降は前回実行との差分から実際の直近速度が計算されます。

## スコープ外（現時点では未実装）

- ホットキーワードサイドバー（形態素解析が必要）
- 板別サブページ
- サムネイル画像
