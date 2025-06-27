# VPS WordPress自動投稿システム - セットアップガイド

VPS向けに最適化された軽量版WordPress自動投稿システムのセットアップ手順です。

## ✨ 主な改善点

- **予約投稿システムを削除** → 即時投稿に変更
- **VPSリソース制約に対応** → 同時実行数やメモリ使用量を制限
- **cron実行に最適化** → 軽量なエントリーポイント追加
- **キャラ名取得失敗時の対応** → 下書きとして保存してスキップ
- **エラー修正** → ログ解析で発見された問題を解決

## 🚀 VPS展開手順

### 1. 自動展開（推奨）

```bash
# プロジェクトディレクトリで実行
./scripts/vps_deploy.sh
```

### 2. 手動展開

```bash
# 1. プロジェクトディレクトリ作成
mkdir -p /home/$(whoami)/wordpress-auto-post
cd /home/$(whoami)/wordpress-auto-post

# 2. ファイルアップロード（scp、git clone等）
# ローカルファイルをVPSにアップロード

# 3. Python仮想環境作成
python3 -m venv venv
source venv/bin/activate

# 4. 依存関係インストール
pip install -r requirements.txt

# 5. 環境設定
cp .env.vps.example .env
nano .env  # APIキー等を設定
```

## ⚙️ 設定ファイル

`.env`ファイルで以下を設定：

```bash
# VPS向け軽量設定
VPS_MAX_CONCURRENT_TASKS=2      # 同時実行数制限
VPS_POSTS_PER_RUN=3            # 1回の投稿数制限

# API設定
FANZA_API_ID=your_api_id
GROK_API_KEY=your_grok_key
WP_URL=https://your-site.com
WP_USERNAME=your_username
WP_PASSWORD=your_app_password

# Google Sheets
GOOGLE_SHEETS_ID=your_sheet_id
```

## 🤖 cron自動実行設定

```bash
# cron設定スクリプト実行
./scripts/setup_vps_cron.sh
```

### デフォルトcron設定

```cron
# 日次投稿（9時、15時、21時）
0 9 * * * cd /home/user/wordpress-auto-post && venv/bin/python src/vps_main.py --mode daily --max-posts 3

# キーワード投稿（12時、18時）
0 12 * * * cd /home/user/wordpress-auto-post && venv/bin/python src/vps_main.py --mode keyword --keyword "キーワード" --max-posts 2
```

## 📋 使用方法

### 手動実行

```bash
cd /home/user/wordpress-auto-post
source venv/bin/activate

# 日次投稿（最新商品から3件）
python src/vps_main.py --mode daily --max-posts 3

# キーワード投稿
python src/vps_main.py --mode keyword --keyword "アニメキャラ名" --max-posts 2

# デバッグモード
python src/vps_main.py --mode daily --max-posts 1 --debug
```

### ログ確認

```bash
# 実行ログ
tail -f /var/log/wordpress-auto-post.log

# エラーログ
tail -f logs/error.log
```

## 🔧 キャラ名取得失敗時の動作

### 新しい動作フロー

1. **商品情報取得** → 成功
2. **Grok分析でキャラ名取得** → 失敗
3. **下書きとして保存** → WordPress下書き投稿
4. **次の商品を処理** → 継続実行

### 下書き記事の特徴

- タイトルに `[下書き]` プレフィックス
- WordPressステータス: `draft`
- スプレッドシート記録: `下書き保存`
- エラー詳細記録: 失敗理由

## 📊 監視・メンテナンス

### 重要な監視項目

```bash
# システム負荷
htop

# ディスク使用量
df -h

# メモリ使用量
free -h

# プロセス確認
ps aux | grep python
```

### ログローテーション設定

```bash
# logrotateで自動ローテーション
sudo nano /etc/logrotate.d/wordpress-auto-post
```

## ⚡ パフォーマンス最適化

### VPS向け軽量設定

- **同時実行数**: 2タスクに制限
- **メモリ使用量**: 512MB制限
- **キャッシュサイズ**: 50MB制限
- **画像品質**: 80%に圧縮
- **HTTP接続数**: 5接続に制限

### リソース監視

```bash
# メモリ使用量チェック
python -c "
import psutil
print(f'メモリ使用量: {psutil.virtual_memory().percent}%')
print(f'ディスク使用量: {psutil.disk_usage(\"/\").percent}%')
"
```

## 🚨 トラブルシューティング

### よくある問題

1. **API認証エラー**
   ```bash
   # .envファイルのAPIキーを確認
   grep API .env
   ```

2. **メモリ不足**
   ```bash
   # プロセス数を減らす
   export VPS_MAX_CONCURRENT_TASKS=1
   ```

3. **ディスク容量不足**
   ```bash
   # キャッシュクリア
   rm -rf cache/*
   ```

4. **cron実行されない**
   ```bash
   # cron設定確認
   crontab -l
   
   # cron実行ログ確認
   sudo tail -f /var/log/cron.log
   ```

### 緊急停止

```bash
# 実行中プロセス停止
pkill -f vps_main.py

# cron無効化
crontab -r
```

## 📞 サポート

問題が発生した場合：

1. ログファイルを確認
2. 設定ファイルを再確認
3. 手動実行でテスト
4. VPSリソース状況を確認

---

**注意**: 本システムは学習・ポートフォリオ目的です。商用利用時は各種APIの利用規約を遵守してください。