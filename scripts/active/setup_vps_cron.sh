#!/bin/bash
# VPS向けcron設定スクリプト

echo "VPS WordPress自動投稿 - cron設定スクリプト"

# プロジェクトパスを設定（実際のVPSパスに変更してください）
PROJECT_PATH="/home/user/wordpress-auto-post"
PYTHON_PATH="${PROJECT_PATH}/venv/bin/python"
SCRIPT_PATH="${PROJECT_PATH}/src/vps_main.py"

# 実行権限を付与
chmod +x "${SCRIPT_PATH}"

# crontabバックアップ
echo "既存のcrontabをバックアップ中..."
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || echo "既存のcrontabなし"

# cron設定を作成
cat << EOF > /tmp/vps_wordpress_cron
# VPS WordPress自動投稿設定
# PATH設定
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# 日次投稿（毎日9時、15時、21時に実行）
0 9 * * * cd ${PROJECT_PATH} && ${PYTHON_PATH} ${SCRIPT_PATH} --mode daily --max-posts 3 >> /var/log/wordpress-auto-post.log 2>&1
0 15 * * * cd ${PROJECT_PATH} && ${PYTHON_PATH} ${SCRIPT_PATH} --mode daily --max-posts 3 >> /var/log/wordpress-auto-post.log 2>&1
0 21 * * * cd ${PROJECT_PATH} && ${PYTHON_PATH} ${SCRIPT_PATH} --mode daily --max-posts 3 >> /var/log/wordpress-auto-post.log 2>&1

# キーワード投稿（毎日12時、18時に実行） - 必要に応じてキーワードを変更
0 12 * * * cd ${PROJECT_PATH} && ${PYTHON_PATH} ${SCRIPT_PATH} --mode keyword --keyword "アニメキャラ名" --max-posts 2 >> /var/log/wordpress-auto-post.log 2>&1
0 18 * * * cd ${PROJECT_PATH} && ${PYTHON_PATH} ${SCRIPT_PATH} --mode keyword --keyword "別のキャラ名" --max-posts 2 >> /var/log/wordpress-auto-post.log 2>&1

EOF

echo "cron設定内容："
cat /tmp/vps_wordpress_cron

# ユーザーに確認
read -p "この設定でcronを更新しますか？ (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 既存のcrontabを読み込み、新しい設定を追加
    (crontab -l 2>/dev/null; cat /tmp/vps_wordpress_cron) | crontab -
    echo "cron設定が完了しました"
    
    # ログファイル作成
    sudo touch /var/log/wordpress-auto-post.log
    sudo chmod 664 /var/log/wordpress-auto-post.log
    sudo chown $(whoami):$(whoami) /var/log/wordpress-auto-post.log
    
    echo "ログファイルを作成しました: /var/log/wordpress-auto-post.log"
    
    # 現在のcrontab表示
    echo "現在のcron設定："
    crontab -l
    
else
    echo "cron設定をキャンセルしました"
fi

# 一時ファイル削除
rm /tmp/vps_wordpress_cron

echo "設定完了"