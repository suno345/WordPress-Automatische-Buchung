#!/bin/bash
# VPS 48件予約投稿システム 監視スクリプト

echo "=== WordPress 48件予約投稿システム 監視ダッシュボード ==="
echo ""

# システム情報表示
echo "📅 現在時刻: $(date '+%Y-%m-%d %H:%M:%S')"
echo "🖥️  システム: $(hostname)"
echo "👤 ユーザー: $(whoami)"
echo ""

# cron設定確認
echo "⏰ cron設定:"
crontab -l | grep -E "(schedule48|WordPress)" || echo "   設定なし"
echo ""

# 最新のログ確認
LOG_FILE="/var/log/wordpress-auto-post-48.log"
if [ -f "$LOG_FILE" ]; then
    echo "📝 最新ログ (最新10行):"
    tail -10 "$LOG_FILE"
    echo ""
    
    # 今日の実行状況
    TODAY=$(date '+%Y-%m-%d')
    echo "📊 今日($TODAY)の実行状況:"
    grep "$TODAY" "$LOG_FILE" | grep -E "(開始|完了|エラー)" | tail -5 || echo "   今日の実行記録なし"
    echo ""
    
    # エラー確認
    ERROR_COUNT=$(grep -c "ERROR\|エラー" "$LOG_FILE" 2>/dev/null || echo "0")
    echo "🚨 エラー件数: $ERROR_COUNT"
    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo "   最新エラー:"
        grep "ERROR\|エラー" "$LOG_FILE" | tail -3
    fi
    echo ""
else
    echo "⚠️  ログファイル未作成: $LOG_FILE"
    echo ""
fi

# システムリソース確認
echo "💾 システムリソース:"
echo "   CPU使用率: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "   メモリ使用率: $(free | grep Mem | awk '{printf("%.1f%%", $3/$2 * 100.0)}')"
echo "   ディスク使用率: $(df -h / | awk 'NR==2{print $5}')"
echo ""

# Pythonプロセス確認
PYTHON_PROCESSES=$(ps aux | grep -E "vps_main|wordpress-auto" | grep -v grep | wc -l)
echo "🐍 実行中のPythonプロセス: $PYTHON_PROCESSES"
if [ "$PYTHON_PROCESSES" -gt 0 ]; then
    echo "   プロセス詳細:"
    ps aux | grep -E "vps_main|wordpress-auto" | grep -v grep | awk '{print "   PID:" $2 " " $11 " " $12 " " $13 " " $14}'
fi
echo ""

# 次回実行予定
echo "⏳ 次回実行予定:"
NEXT_RUN=$(crontab -l | grep schedule48 | head -1)
if [ ! -z "$NEXT_RUN" ]; then
    echo "   毎日0:00 (翌日分48件予約投稿)"
    
    # 次回実行までの時間計算
    CURRENT_HOUR=$(date '+%H')
    CURRENT_MIN=$(date '+%M')
    
    if [ "$CURRENT_HOUR" -eq 0 ] && [ "$CURRENT_MIN" -lt 30 ]; then
        echo "   状態: 実行中または実行直後"
    else
        HOURS_UNTIL_NEXT=$((24 - CURRENT_HOUR))
        if [ "$CURRENT_MIN" -gt 0 ]; then
            HOURS_UNTIL_NEXT=$((HOURS_UNTIL_NEXT - 1))
            MINS_UNTIL_NEXT=$((60 - CURRENT_MIN))
        else
            MINS_UNTIL_NEXT=0
        fi
        echo "   次回まで: ${HOURS_UNTIL_NEXT}時間${MINS_UNTIL_NEXT}分"
    fi
else
    echo "   cron設定なし"
fi
echo ""

# 便利なコマンド表示
echo "🔧 便利なコマンド:"
echo "   リアルタイムログ監視: tail -f $LOG_FILE"
echo "   手動実行(テスト):     python src/vps_main.py --mode schedule48 --debug"
echo "   cron設定確認:        crontab -l"
echo "   cronログ確認:        sudo tail -f /var/log/cron.log"
echo ""