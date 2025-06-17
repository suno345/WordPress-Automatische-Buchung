#!/bin/bash

# エラーが発生したら即座に終了
set -e

# 色の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ログ関数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 環境変数の読み込み
if [ -f .env ]; then
    log_info "環境変数を読み込み中..."
    source .env
else
    log_error ".envファイルが見つかりません"
    exit 1
fi

# 必要なディレクトリの作成
log_info "必要なディレクトリを作成中..."
mkdir -p cache logs

# 仮想環境の確認と作成
if [ ! -d "venv" ]; then
    log_info "仮想環境を作成中..."
    python3 -m venv venv
fi

# 仮想環境の有効化
log_info "仮想環境を有効化中..."
source venv/bin/activate

# 依存パッケージのインストール
log_info "依存パッケージをインストール中..."
pip install --upgrade pip
pip install -r requirements.txt

# 設定ファイルの確認
if [ ! -f "config.json" ]; then
    log_warn "config.jsonが見つかりません。デフォルト設定を作成します..."
    python -m src.config.config_manager --init
fi

# テストの実行
log_info "テストを実行中..."
python -m unittest discover tests

# キャッシュのクリーンアップ
log_info "古いキャッシュをクリーンアップ中..."
python -m src.utils.cache_cleaner --days 7

# ログのクリーンアップ
log_info "古いログをクリーンアップ中..."
python -m src.utils.log_cleaner --days 30

# バックアップの作成
log_info "バックアップを作成中..."
timestamp=$(date +%Y%m%d_%H%M%S)
backup_dir="backups/backup_${timestamp}"
mkdir -p "$backup_dir"

# 設定ファイルのバックアップ
cp .env "${backup_dir}/.env"
cp config.json "${backup_dir}/config.json"

# キャッシュのバックアップ
if [ -d "cache" ]; then
    tar -czf "${backup_dir}/cache.tar.gz" cache/
fi

# ログのバックアップ
if [ -d "logs" ]; then
    tar -czf "${backup_dir}/logs.tar.gz" logs/
fi

# デプロイ完了
log_info "デプロイが完了しました！"
log_info "バックアップは ${backup_dir} に保存されました"

# 実行権限の付与
chmod +x scripts/*.sh

# 仮想環境の無効化
deactivate 