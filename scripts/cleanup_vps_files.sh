#!/bin/bash
# VPS向け不要ファイル削除スクリプト
# 実行前に重要ファイルのバックアップを取ってください

echo "🧹 VPS向け不要ファイル削除開始"

# 削除確認
read -p "本当に削除しますか？ (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "削除をキャンセルしました"
    exit 1
fi

# 削除推奨ファイル
echo "🔥 削除推奨ファイルを削除中..."
rm -rf "backup_old_structure/"
rm -rf "tests/"
rm -rf "docs/"
rm -rf "auto_wp_post.py"
rm -rf "__init__.py"
rm -rf "docker-compose.yml"
rm -rf "Dockerfile"
rm -rf "templates/"
rm -rf "DMM_API.txt"
rm -rf "要件定義.txt"

# 古いログファイル削除
echo "📝 古いログファイルを削除中..."
rm -f "logs/error_20250521.log"
rm -f "logs/error_20250522.log"
rm -f "logs/error_20250523.log"
rm -f "logs/20250522.log"
rm -f "logs/debug.log"
rm -f "logs/error_details.json"
rm -f "logs/error_stats.json"
rm -f "logs/info.log"
rm -f "logs/secure.log"
rm -f "logs/warning.log"

# 開発用スクリプト削除
echo "📁 開発用スクリプトを削除中..."
rm -f "scripts/auto_post_from_keywords.py"
rm -f "scripts/deploy.ps1"
rm -f "scripts/deploy.sh"
rm -f "scripts/fetch_fanza_products_from_keywords.py"
rm -f "scripts/scrape_fanza_doujin_from_sheet.py"
rm -f "scripts/setup.sh"
rm -f "scripts/reorganize_project.py"
rm -f "scripts/create_simple_structure.py"

# キャッシュクリア
echo "🗑️ 古いキャッシュをクリア中..."
find cache/ -name "*.json" -mtime +7 -delete 2>/dev/null || true
find logs/ -name "*.log" -mtime +30 -delete 2>/dev/null || true

echo "✅ クリーンアップ完了!"
echo "📊 ディスク使用量を確認:"
du -sh .
