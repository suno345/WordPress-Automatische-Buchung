# WordPress自動投稿システム

VPS向けに最適化された同人作品のWordPress自動投稿システムです。

## 機能

- FANZAから商品情報を自動取得
- AIによる記事自動生成
- WordPress自動投稿
- Googleスプレッドシートとの連携
- VPS環境での軽量実行

## セットアップ

1. リポジトリのクローン
```bash
git clone https://github.com/suno345/WordPress-Automatische-Buchung.git
cd WordPress-Automatische-Buchung
```

2. 依存関係のインストール
```bash
pip install -r requirements.txt
```

3. 環境変数の設定
```bash
cp API.env .env
# .envファイルを編集してAPIキーなどを設定
```

## VPSサーバーでの実行

詳細な手順は[VPS_SETUP.md](docs/VPS_SETUP.md)を参照してください。

### クイックスタート

```bash
# 自動デプロイスクリプトを実行
./scripts/active/vps_deploy.sh
```

## 使用方法

```bash
# 日次投稿
python src/vps_main.py --mode daily --max-posts 3

# キーワード投稿
python src/vps_main.py --mode keyword --keyword "キーワード" --max-posts 2
```

## ライセンス

このプロジェクトは学習・ポートフォリオ目的で作成されています。