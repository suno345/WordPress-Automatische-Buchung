#!/bin/bash
# VPS展開スクリプト

set -e  # エラー時に停止

echo "🚀 VPS WordPress自動投稿システム展開スクリプト"
echo "================================================"

# 設定
PROJECT_NAME="wordpress-auto-post"
INSTALL_DIR="/home/$(whoami)/${PROJECT_NAME}"
PYTHON_VERSION="3.8"

# 色付きメッセージ関数
print_step() {
    echo -e "\n\033[1;34m📋 $1\033[0m"
}

print_success() {
    echo -e "\033[1;32m✅ $1\033[0m"
}

print_warning() {
    echo -e "\033[1;33m⚠️  $1\033[0m"
}

print_error() {
    echo -e "\033[1;31m❌ $1\033[0m"
}

# 1. 必要パッケージの確認とインストール
print_step "必要パッケージの確認"
if ! command -v python3 &> /dev/null; then
    print_error "Python3がインストールされていません"
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    print_warning "pip3をインストール中..."
    sudo apt update
    sudo apt install -y python3-pip
fi

if ! command -v git &> /dev/null; then
    print_warning "gitをインストール中..."
    sudo apt install -y git
fi

print_success "必要パッケージの確認完了"

# 2. プロジェクトディレクトリの作成
print_step "プロジェクトディレクトリの準備"
if [ -d "$INSTALL_DIR" ]; then
    print_warning "既存のプロジェクトディレクトリを発見"
    read -p "既存のディレクトリを削除しますか？ (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
        print_success "既存ディレクトリを削除"
    else
        print_error "展開をキャンセル"
        exit 1
    fi
fi

mkdir -p "$INSTALL_DIR"
print_success "プロジェクトディレクトリ作成: $INSTALL_DIR"

# 3. ファイルコピー（ローカルから）
print_step "プロジェクトファイルのコピー"
# 現在のディレクトリからVPSにコピー
CURRENT_DIR="$(pwd)"
if [ -f "$CURRENT_DIR/src/vps_main.py" ]; then
    cp -r "$CURRENT_DIR"/* "$INSTALL_DIR/"
    print_success "プロジェクトファイルをコピー完了"
else
    print_error "vps_main.pyが見つかりません。正しいディレクトリで実行してください"
    exit 1
fi

cd "$INSTALL_DIR"

# 4. Python仮想環境の作成
print_step "Python仮想環境の作成"
python3 -m venv venv
source venv/bin/activate
print_success "仮想環境作成完了"

# 5. 依存関係のインストール
print_step "依存関係のインストール"
if [ -f "requirements.txt" ]; then
    pip install --upgrade pip
    pip install -r requirements.txt
    print_success "依存関係インストール完了"
else
    print_warning "requirements.txtが見つかりません"
fi

# 6. 環境設定ファイルの準備
print_step "環境設定ファイルの準備"
if [ -f ".env.vps.example" ]; then
    cp .env.vps.example .env
    print_warning "環境設定ファイル(.env)を作成しました"
    print_warning "APIキーやWordPress設定を編集してください: $INSTALL_DIR/.env"
else
    print_error ".env.vps.exampleが見つかりません"
fi

# 7. ログディレクトリの作成
print_step "ログディレクトリの作成"
mkdir -p logs
mkdir -p cache/api
mkdir -p cache/images
chmod 755 logs cache
print_success "ディレクトリ作成完了"

# 8. 実行権限の設定
print_step "実行権限の設定"
chmod +x src/vps_main.py
chmod +x scripts/*.sh
print_success "実行権限設定完了"

# 9. テスト実行
print_step "テスト実行"
print_warning "設定ファイル(.env)を編集後、以下のコマンドでテストしてください："
echo "cd $INSTALL_DIR"
echo "source venv/bin/activate"
echo "python src/vps_main.py --mode daily --max-posts 1 --debug"

# 10. cron設定の案内
print_step "cron設定の案内"
print_warning "自動実行を設定するには："
echo "cd $INSTALL_DIR"
echo "./scripts/setup_vps_cron.sh"

print_success "VPS展開完了！"
echo ""
echo "📝 次の手順："
echo "1. 環境設定ファイルを編集: $INSTALL_DIR/.env"
echo "2. テスト実行でAPI接続を確認"
echo "3. cron設定で自動実行を有効化"
echo ""
echo "🔧 手動実行コマンド："
echo "cd $INSTALL_DIR && source venv/bin/activate"
echo "python src/vps_main.py --mode daily --max-posts 3"
echo "python src/vps_main.py --mode keyword --keyword 'キーワード' --max-posts 2"