# FANZA WordPress Auto Poster

FANZA APIから商品情報を取得し、AI（Grok）を活用して自動でWordPress記事を生成・投稿するPythonアプリケーションです。同人コンテンツ紹介サイトの運営自動化を目的としています。

## 主な機能

- **FANZA API連携**: 商品情報の自動取得
- **AI記事生成**: Grok APIを使用した記事の自動生成
- **WordPress自動投稿**: REST APIを通じた予約投稿
- **Google Sheets連携**: キーワード管理とスケジューリング
- **画像処理**: サムネイル自動生成と顔認識
- **スケジューリング**: 自動実行とタスク管理
- **監視・ログ**: エラー監視とDiscord通知

## 技術スタック

- **言語**: Python 3.8+
- **AI**: xAI Grok API
- **CMS**: WordPress REST API
- **データ管理**: Google Sheets API
- **通知**: Discord API
- **画像処理**: InsightFace（ONNX）
- **その他**: Docker対応

## セットアップ

1. リポジトリをクローン
```bash
git clone [repository_url]
cd fanza-wordpress-auto-poster
```

2. 仮想環境の作成
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
```

3. 依存関係のインストール
```bash
pip install -r requirements.txt
```

4. 環境変数の設定
`.env.example`を`.env`にコピーし、必要なAPIキーを設定してください。

## 設定

### 必要なAPIキー

以下のAPIキーが必要です：

- **FANZA API**: 商品情報取得用
- **xAI Grok API**: 記事生成用
- **WordPress**: REST API認証用
- **Google Sheets API**: データ管理用
- **Discord API**: 通知用（オプション）

## 使用方法

### 基本実行
```bash
python src/main.py
```

### Docker実行
```bash
docker-compose up -d
```

### テスト実行
```bash
python -m pytest tests/
```

## プロジェクト構造

```
src/
├── modules/
│   ├── fanza/           # FANZA API連携
│   ├── grok/           # AI記事生成
│   └── wordpress/      # WordPress投稿
├── utils/              # ユーティリティ
├── config/             # 設定管理
├── scheduler/          # スケジューリング
└── main.py            # メインエントリーポイント

docs/                   # ドキュメント
scripts/               # 実行スクリプト
tests/                 # テストコード
```

## 主要コンポーネント

- **FANZAモジュール**: API連携と商品データ取得
- **Grokモジュール**: AI記事生成と画像処理
- **WordPressモジュール**: 記事投稿とメディア管理
- **スケジューラー**: タスク管理と自動実行

## 注意事項

- 各種APIの利用規約を遵守してください
- 適切なレート制限を設定してください
- APIキーは安全に管理し、公開リポジトリにコミットしないでください
- 本プロジェクトは学習・ポートフォリオ目的で作成されています

## ライセンス

MIT License 