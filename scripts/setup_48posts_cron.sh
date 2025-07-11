#!/bin/bash
# VPS 48件予約投稿システム cron設定スクリプト

set -e

echo "=== VPS 48件予約投稿システム cron設定開始 ==="

# 現在のユーザー名とプロジェクトパスを取得
USER_NAME=$(whoami)
PROJECT_PATH=$(pwd)

echo "ユーザー名: $USER_NAME"
echo "プロジェクトパス: $PROJECT_PATH"

# ログディレクトリとファイルの作成
echo "ログファイルの設定..."
sudo mkdir -p /var/log
sudo touch /var/log/wordpress-auto-post-48.log
sudo chown $USER_NAME:$USER_NAME /var/log/wordpress-auto-post-48.log

# cron設定の追加
echo "cron設定の追加..."

# 既存のcrontab設定を取得
crontab -l > /tmp/current_cron 2>/dev/null || echo "" > /tmp/current_cron

# 48件予約投稿の設定を追加（重複チェック）
if ! grep -q "schedule48" /tmp/current_cron; then
    echo "" >> /tmp/current_cron
    echo "# WordPress Auto Post - 48件予約投稿システム" >> /tmp/current_cron
    echo "# 毎日0時に翌日分48件を予約投稿（30分間隔）" >> /tmp/current_cron
    echo "0 0 * * * cd $PROJECT_PATH && $PROJECT_PATH/venv/bin/python src/vps_main.py --mode schedule48 >> /var/log/wordpress-auto-post-48.log 2>&1" >> /tmp/current_cron
    echo "" >> /tmp/current_cron
    
    # 新しいcrontab設定を適用
    crontab /tmp/current_cron
    
    echo "✅ cron設定を追加しました"
else
    echo "⚠️  既存のschedule48設定が見つかりました（スキップ）"
fi

# 一時ファイルの削除
rm -f /tmp/current_cron

# cron設定の確認
echo ""
echo "=== 現在のcron設定 ==="
crontab -l

# cronサービスの状態確認
echo ""
echo "=== cronサービス状態確認 ==="
sudo systemctl status cron --no-pager -l

# cronサービスが停止している場合は開始
if ! sudo systemctl is-active --quiet cron; then
    echo "cronサービスを開始します..."
    sudo systemctl start cron
    sudo systemctl enable cron
fi

echo ""
echo "=== セットアップ完了 ==="
echo ""
echo "📋 実行内容:"
echo "  • 毎日0:00に翌日分48件の予約投稿を実行"
echo "  • 投稿時間: 翌日0:30から30分間隔で48件"
echo "  • ログファイル: /var/log/wordpress-auto-post-48.log"
echo ""
echo "🔧 手動テスト方法:"
echo "  python src/vps_main.py --mode schedule48 --debug"
echo ""
echo "📊 監視方法:"
echo "  tail -f /var/log/wordpress-auto-post-48.log"
echo "  sudo tail -f /var/log/cron.log"
echo ""
echo "⚠️  注意事項:"
echo "  • 初回実行は明日の0:00から開始されます"
echo "  • VPSのリソース状況を定期的に監視してください"
echo "  • API制限に注意してください"
echo ""