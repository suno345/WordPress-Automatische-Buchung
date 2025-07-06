#!/bin/bash
# VPS予約投稿システム cron設定スクリプト（30分間隔）

# プロジェクトディレクトリの設定
PROJECT_DIR="/home/user/WordPress自動投稿"
PYTHON_BIN="/home/user/.local/bin/python3"
VENV_ACTIVATE="/home/user/venv/bin/activate"

echo "=== VPS予約投稿システム cron設定 ==="
echo "30分間隔での自動実行を設定します（1日48回）"

# 現在のcrontabをバックアップ
echo "現在のcrontabをバックアップ中..."
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt

# crontabエントリの作成（キーワードベース）
CRON_ENTRY="0,30 * * * * cd $PROJECT_DIR && source $VENV_ACTIVATE && $PYTHON_BIN src/vps_main.py --mode scheduled --batch-size 1 >> /var/log/wordpress_auto_poster.log 2>&1"

echo "追加するcrontabエントリ（スプレッドシートキーワード使用）:"
echo "$CRON_ENTRY"

# 既存のエントリをチェック
if crontab -l 2>/dev/null | grep -q "vps_main.py --mode scheduled"; then
    echo "警告: 既にVPS予約投稿のcronエントリが存在します"
    echo "既存のエントリを削除してから追加しますか？ (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        # 既存のエントリを削除
        crontab -l | grep -v "vps_main.py --mode scheduled" | crontab -
        echo "既存のエントリを削除しました"
    else
        echo "設定をキャンセルしました"
        exit 1
    fi
fi

# 新しいエントリを追加
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "✅ cron設定が完了しました"
echo ""
echo "=== 設定内容 ==="
echo "実行間隔: 30分毎（毎時00分と30分）"
echo "1日の実行回数: 48回"
echo "バッチサイズ: 1件/回"
echo "データソース: スプレッドシート「キーワード管理」"
echo "処理方式: キーワードベース商品検索 + 予約投稿"
echo "ログファイル: /var/log/wordpress_auto_poster.log"
echo ""
echo "=== 現在のcrontab ==="
crontab -l
echo ""
echo "=== 手動実行テスト ==="
echo "以下のコマンドで手動実行をテストできます:"
echo "cd $PROJECT_DIR && source $VENV_ACTIVATE && $PYTHON_BIN src/vps_main.py --mode scheduled --batch-size 1"
echo ""
echo "=== ログ確認 ==="
echo "ログを確認するには以下のコマンドを使用してください:"
echo "tail -f /var/log/wordpress_auto_poster.log"
echo ""
echo "=== cron削除方法 ==="
echo "設定を削除するには以下のコマンドを実行してください:"
echo "crontab -l | grep -v 'vps_main.py --mode scheduled' | crontab -"