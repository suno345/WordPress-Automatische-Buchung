#!/bin/bash

# エラーが発生したら即座に終了
set -e

# 色の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ログ出力関数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Pythonのバージョン確認
log_info "Pythonのバージョンを確認中..."
python_version=$(python3 --version 2>&1)
if [[ $python_version == *"Python 3"* ]]; then
    log_info "Python 3.x がインストールされています: $python_version"
else
    log_error "Python 3.x が必要です"
    exit 1
fi

# 仮想環境の作成
log_info "仮想環境を作成中..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    log_info "仮想環境を作成しました"
else
    log_warn "仮想環境は既に存在します"
fi

# 仮想環境の有効化
log_info "仮想環境を有効化中..."
source venv/bin/activate

# 必要なパッケージのインストール
log_info "必要なパッケージをインストール中..."
pip install --upgrade pip
pip install -r requirements.txt

# 環境変数ファイルの確認
log_info "環境変数ファイルを確認中..."
if [ ! -f ".env" ]; then
    log_warn ".env ファイルが見つかりません"
    if [ -f ".env.example" ]; then
        log_info ".env.example から .env を作成します"
        cp .env.example .env
        log_warn "APIキーなどの設定値を .env ファイルに設定してください"
    else
        log_error ".env.example ファイルも見つかりません"
        exit 1
    fi
else
    log_info ".env ファイルが存在します"
fi

# キャッシュディレクトリの作成
log_info "キャッシュディレクトリを作成中..."
mkdir -p cache/images
mkdir -p cache/api
mkdir -p logs

# 権限の設定
log_info "ディレクトリの権限を設定中..."
chmod 755 cache
chmod 755 logs
chmod 644 .env

# テストの実行
log_info "テストを実行中..."
python -m pytest tests/

log_info "セットアップが完了しました！"
log_info "以下のコマンドでプログラムを実行できます："
echo "source venv/bin/activate  # 仮想環境の有効化"
echo "python src/main.py --daily  # 日次スケジュールの実行"
echo "python src/main.py --keyword 'キーワード'  # キーワードスケジュールの実行" 