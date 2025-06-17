# セットアップガイド

## 目次
1. [必要条件](#必要条件)
2. [インストール手順](#インストール手順)
3. [環境設定](#環境設定)
4. [動作確認](#動作確認)
5. [トラブルシューティング](#トラブルシューティング)

## 必要条件

### システム要件
- Python 3.8以上
- pip（Pythonパッケージマネージャー）
- インターネット接続
- 十分なディスク容量（キャッシュ用）

### 必要なAPIキー
- FANZA APIキー
- WordPress API認証情報
- Grok APIキー（オプション）

## インストール手順

1. リポジトリのクローン
```bash
git clone https://github.com/your-username/fanza-wordpress-autopost.git
cd fanza-wordpress-autopost
```

2. 仮想環境の作成と有効化
```bash
python -m venv venv
source venv/bin/activate  # Linuxの場合
# または
.\venv\Scripts\activate  # Windowsの場合
```

3. 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

## 環境設定

1. 環境変数ファイルの作成
```bash
cp .env.example .env
```

2. `.env`ファイルの編集
以下の項目を設定してください：

```env
# FANZA API設定
FANZA_API_KEY=your_api_key_here
FANZA_SITE_ID=your_site_id_here

# WordPress設定
WP_API_URL=https://your-wordpress-site.com/wp-json/wp/v2
WP_USERNAME=your_username
WP_PASSWORD=your_application_password

# キャッシュ設定
CACHE_DIR=./cache
CACHE_EXPIRY=3600

# ログ設定
LOG_DIR=./logs
LOG_LEVEL=INFO

# スケジューラー設定
MAX_RETRIES=3
RETRY_DELAY=60
MAX_PARALLEL_TASKS=5
```

3. ディレクトリの作成
```bash
mkdir -p cache logs
```

## 動作確認

1. 設定の確認
```bash
python -m src.config.config_manager
```

2. テストの実行
```bash
python -m unittest discover tests
```

3. サンプル実行
```bash
python -m src.main
```

## トラブルシューティング

### よくある問題と解決方法

1. APIキーの認証エラー
   - APIキーが正しく設定されているか確認
   - APIキーの有効期限を確認
   - アクセス権限を確認

2. WordPress接続エラー
   - WordPressのURLが正しいか確認
   - 認証情報が正しいか確認
   - WordPressのREST APIが有効か確認

3. キャッシュ関連のエラー
   - キャッシュディレクトリのパーミッションを確認
   - ディスク容量を確認
   - キャッシュをクリアして再試行

4. ログ関連のエラー
   - ログディレクトリのパーミッションを確認
   - ログファイルのサイズを確認
   - ログローテーションの設定を確認

### サポート

問題が解決しない場合は、以下の情報を添えてGitHubのIssueを作成してください：

1. エラーメッセージ
2. 実行環境の詳細
3. 実行したコマンド
4. ログファイルの内容 