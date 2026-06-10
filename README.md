# LAST PROTOCOL — Artist HP

NOVA × ASH によるサイバーパンク音楽ユニット「LAST PROTOCOL」の公式サイト。

## 構成

```
docs/
  index.html   … サイト本体（GitHub Pagesが配信。data.jsを読んで描画）
  data.js      … 表示データ（自動生成。手で編集しない）
content/
  content.json … 手動管理データ（ディスコグラフィ、最新作の紹介文、タイトル上書き）
scripts/
  update_content.py … data.js 生成スクリプト
```

## コンテンツ更新（リリース時のワークフロー）

新しいMVを公開したら、以下を実行するだけでサイトが追従します：

```powershell
# 1. （新アルバム/シングルの場合）content/content.json の discography に追記
# 2. data.js を再生成
python scripts/update_content.py
# 3. push すれば公開に反映
git add -A; git commit -m "Update releases"; git push
```

スクリプトの動作：

- チャンネルの全動画から `[LAST PROTOCOL]` で始まるタイトルをMVとして抽出
- **LATEST** = 最新公開のMV
- **MV GALLERY** = 再生数上位3作
- タイトル末尾のジャンル表記（` - Cyberpunk ...`）は自動除去

### データソース（フォールバックチェーン）

1. **YouTube Data API** … 正確な再生数。有効な `YOUTUBE_API_KEY` が必要
2. **InnerTube**（YouTube内部API、キー不要）… 全動画対象、再生数は概数（「4.6万回視聴」等）← 現在これで動作中
3. **RSSフィード** … 直近15本のみ

正確な再生数を表示したい場合は、Google Cloud Console で YouTube Data API v3 の
APIキーを発行し、`../youtube-ads-report/.env` の `YOUTUBE_API_KEY` を差し替えること。

## ローカル確認

```powershell
python -m http.server 8765 --directory docs
# → http://localhost:8765
```

## 公開（GitHub Pages）

リポジトリ: `last-protocol-site`（Settings → Pages → Branch: main / `/docs`）

### 独自ドメイン（任意・未設定）

1. ドメイン取得（例: `lastprotocol.ai`）
2. DNSで CNAME を `<ユーザー名>.github.io` に向ける
3. GitHub Pages の Custom domain に設定 → HTTPS自動有効化

## TODO

- [ ] 有効な YouTube Data API キーの設定（再生数を概数→正確な値に）
- [ ] DISCOGRAPHY 各カードに各ストリーミングのアルバムURLをリンク（DistroKidハイパーフォロー等）
- [ ] OG画像を専用アートワークに差し替え（現状はYouTubeサムネ流用）
- [ ] アクセス解析（GA4 or Cloudflare Web Analytics）追加
- [ ] GitHub Actionsで update_content.py を定期実行（完全自動更新化）
