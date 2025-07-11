# WordPress自動投稿システム

VPS向けに最適化された同人作品のWordPress自動投稿システムです。

## 機能

- FANZAから商品情報を自動取得
- AIによる記事自動生成（Gemini + Grok）
- WordPress自動投稿・予約投稿
- Googleスプレッドシートとの連携
- VPS環境での軽量実行
- **48件予約投稿システム**（30分間隔で1日48件）

## セットアップ

1. リポジトリのクローン
```bash
git clone https://github.com/suno345/WordPress-Automatische-Buchung.git wordpress-auto-post
cd wordpress-auto-post
```

2. Python仮想環境の作成
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
```

3. 依存関係のインストール
```bash
pip install -r requirements.txt beautifulsoup4 lxml
```

4. 環境変数の設定
```bash
cp .env.vps.example .env
nano .env  # 実際の値を設定
```

### 必須の環境変数

```bash
# FANZA API（商品情報取得用）
FANZA_API_ID=your_api_id
FANZA_AFFILIATE_ID=your_affiliate_id

# Gemini API（キャラクター認識用）
GEMINI_API_KEY=your_gemini_api_key

# Grok API（記事生成用）
GROK_API_KEY=your_grok_api_key

# WordPress
WP_URL=https://your-site.com
WP_USERNAME=your_username
WP_APP_PASSWORD=your_app_password

# Google Sheets（オプション）
GOOGLE_SHEETS_ID=your_sheet_id
```

## VPSサーバーでの実行

詳細な手順は[VPS_SETUP.md](docs/VPS_SETUP.md)を参照してください。

### クイックスタート

```bash
# 自動デプロイスクリプトを実行
./scripts/active/vps_deploy.sh
```

## 使用方法

### 基本コマンド

```bash
# 仮想環境をアクティベート
source venv/bin/activate

# 日次投稿（最新商品から3件）
python src/vps_main.py --mode daily --max-posts 3

# キーワード投稿
python src/vps_main.py --mode keyword --keyword "キーワード" --max-posts 2

# 48件予約投稿（毎日0時実行用）
python src/vps_main.py --mode schedule48

# デバッグモード（詳細ログ表示）
python src/vps_main.py --mode daily --max-posts 1 --debug
```

## 🚀 48件予約投稿システム

### 概要
毎日0時に翌日分48件を30分間隔で予約投稿するシステムです。

### セットアップ
```bash
# 自動セットアップ実行
chmod +x scripts/setup_48posts_cron.sh
./scripts/setup_48posts_cron.sh
```

### 監視・管理
```bash
# 監視ダッシュボード
chmod +x scripts/monitor_48posts.sh
./scripts/monitor_48posts.sh

# ログ監視
tail -f /var/log/wordpress-auto-post-48.log
```

詳細は[VPS_48POSTS_SETUP.md](docs/VPS_48POSTS_SETUP.md)を参照してください。

### トラブルシューティング

```bash
# APIキー設定確認
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('GEMINI_API_KEY:', bool(os.getenv('GEMINI_API_KEY'))); print('GROK_API_KEY:', bool(os.getenv('GROK_API_KEY')))"

# ログ確認
tail -f logs/error_*.log
```

## ライセンス

このプロジェクトは学習・ポートフォリオ目的で作成されています。