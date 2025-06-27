#!/usr/bin/env python3
"""
VPS向け不要ファイル削除スクリプト
"""

import os
import shutil
from pathlib import Path

def analyze_unused_files():
    """使わないファイルを分析"""
    
    root_dir = Path(__file__).parent.parent
    
    # VPS向けシステムで使わないファイル・ディレクトリ
    unused_items = {
        # 🔥 完全に不要（削除推奨）
        "delete_recommended": [
            "backup_old_structure/",  # バックアップ（整理完了後は不要）
            "tests/",                 # テストファイル（VPSでは不要）
            "docs/",                 # ドキュメント（VPSでは不要）
            "auto_wp_post.py",       # 旧メインファイル
            "__init__.py",           # ルートの不要ファイル
            "docker-compose.yml",    # Docker設定（VPS直接実行のため不要）
            "Dockerfile",            # Docker設定（VPS直接実行のため不要）
            "templates/",            # テンプレート（記事生成で未使用）
            "DMM_API.txt",          # API仕様書（開発用）
            "要件定義.txt",          # 要件定義（開発用）
        ],
        
        # ⚠️ 条件付きで不要（確認後削除）
        "delete_conditional": [
            "models/",               # 顔認識モデル（Grok使用時は不要の可能性）
            "cache/api/",           # 古いキャッシュ
            "logs/error_20250521.log", # 古いログファイル
            "logs/error_20250522.log",
            "logs/error_20250523.log", 
            "logs/20250522.log",
            "logs/debug.log",
            "logs/error_details.json",
            "logs/error_stats.json",
            "logs/info.log",
            "logs/secure.log",
            "logs/warning.log",
        ],
        
        # 📁 スクリプト整理（開発用のみ保持）
        "scripts_cleanup": [
            "scripts/auto_post_from_keywords.py",      # 旧スクリプト
            "scripts/deploy.ps1",                      # Windows用（Linux VPSでは不要）
            "scripts/deploy.sh",                       # 旧展開スクリプト
            "scripts/fetch_fanza_products_from_keywords.py", # 旧機能
            "scripts/scrape_fanza_doujin_from_sheet.py",     # 旧機能
            "scripts/setup.sh",                        # 旧セットアップ
            "scripts/reorganize_project.py",           # 整理完了後は不要
            "scripts/create_simple_structure.py",      # 整理完了後は不要
        ],
        
        # 💾 保持推奨（VPSで使用）
        "keep_required": [
            "src/",                  # メインソースコード
            "config/",              # Google認証ファイル
            "cache/images/",        # 画像キャッシュ
            "logs/error.log",       # 現在のエラーログ
            "prompts/",             # Grokプロンプト
            "requirements.txt",     # 依存関係
            ".env",                 # 環境設定
            ".env.vps.example",     # VPS設定例
            "scripts/vps_deploy.sh", # VPS展開
            "scripts/setup_vps_cron.sh", # cron設定
            "README.md",            # 基本説明
            "VPS_SETUP.md",         # VPS設定説明
            "FOLDER_STRUCTURE.md",  # 構造説明
        ]
    }
    
    return unused_items

def calculate_disk_usage():
    """ディスク使用量を計算"""
    
    root_dir = Path(__file__).parent.parent
    unused = analyze_unused_files()
    
    total_size = 0
    delete_size = 0
    
    print("📊 ディスク使用量分析")
    print("=" * 50)
    
    # 削除推奨ファイルのサイズ計算
    print("\n🔥 削除推奨ファイル:")
    for item in unused["delete_recommended"]:
        item_path = root_dir / item
        if item_path.exists():
            if item_path.is_file():
                size = item_path.stat().st_size
                delete_size += size
                print(f"  📄 {item}: {size/1024/1024:.1f}MB")
            elif item_path.is_dir():
                size = sum(f.stat().st_size for f in item_path.rglob('*') if f.is_file())
                delete_size += size
                print(f"  📁 {item}: {size/1024/1024:.1f}MB")
    
    # 条件付き削除ファイル
    print("\n⚠️ 条件付き削除ファイル:")
    conditional_size = 0
    for item in unused["delete_conditional"]:
        item_path = root_dir / item
        if item_path.exists():
            if item_path.is_file():
                size = item_path.stat().st_size
                conditional_size += size
                print(f"  📄 {item}: {size/1024/1024:.1f}MB")
            elif item_path.is_dir():
                size = sum(f.stat().st_size for f in item_path.rglob('*') if f.is_file())
                conditional_size += size
                print(f"  📁 {item}: {size/1024/1024:.1f}MB")
    
    # スクリプト整理
    print("\n📁 スクリプト整理:")
    script_size = 0
    for item in unused["scripts_cleanup"]:
        item_path = root_dir / item
        if item_path.exists():
            size = item_path.stat().st_size
            script_size += size
            print(f"  📄 {item}: {size/1024:.1f}KB")
    
    print(f"\n💾 削除可能サイズ:")
    print(f"  🔥 即座に削除: {delete_size/1024/1024:.1f}MB")
    print(f"  ⚠️ 条件付き削除: {conditional_size/1024/1024:.1f}MB")
    print(f"  📁 スクリプト整理: {script_size/1024:.1f}KB")
    print(f"  📊 合計削除可能: {(delete_size + conditional_size + script_size)/1024/1024:.1f}MB")

def create_cleanup_script():
    """削除スクリプトを生成"""
    
    unused = analyze_unused_files()
    
    cleanup_script = '''#!/bin/bash
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
'''
    
    for item in unused["delete_recommended"]:
        cleanup_script += f'rm -rf "{item}"\n'
    
    cleanup_script += '''
# 古いログファイル削除
echo "📝 古いログファイルを削除中..."
'''
    
    for item in unused["delete_conditional"]:
        if "logs/" in item:
            cleanup_script += f'rm -f "{item}"\n'
    
    cleanup_script += '''
# 開発用スクリプト削除
echo "📁 開発用スクリプトを削除中..."
'''
    
    for item in unused["scripts_cleanup"]:
        cleanup_script += f'rm -f "{item}"\n'
    
    cleanup_script += '''
# キャッシュクリア
echo "🗑️ 古いキャッシュをクリア中..."
find cache/ -name "*.json" -mtime +7 -delete 2>/dev/null || true
find logs/ -name "*.log" -mtime +30 -delete 2>/dev/null || true

echo "✅ クリーンアップ完了!"
echo "📊 ディスク使用量を確認:"
du -sh .
'''
    
    script_path = Path(__file__).parent / "cleanup_vps_files.sh"
    with open(script_path, 'w') as f:
        f.write(cleanup_script)
    
    os.chmod(script_path, 0o755)
    print(f"🗑️ 削除スクリプト作成: {script_path}")

if __name__ == "__main__":
    print("🔍 VPS向け不要ファイル分析")
    print("=" * 40)
    
    calculate_disk_usage()
    create_cleanup_script()
    
    unused = analyze_unused_files()
    
    print(f"\n📋 分析結果:")
    print(f"  🔥 削除推奨: {len(unused['delete_recommended'])}個")
    print(f"  ⚠️ 条件付き削除: {len(unused['delete_conditional'])}個") 
    print(f"  📁 スクリプト整理: {len(unused['scripts_cleanup'])}個")
    print(f"  💾 保持推奨: {len(unused['keep_required'])}個")
    
    print(f"\n🚀 次の手順:")
    print(f"1. scripts/cleanup_vps_files.sh を実行")
    print(f"2. 削除後の動作確認")
    print(f"3. VPSにアップロード")