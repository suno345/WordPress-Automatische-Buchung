#!/usr/bin/env python3
"""
プロジェクト構造整理スクリプト
重複ファイルを統合し、VPS向けにシンプル化
"""

import os
import shutil
from pathlib import Path

def reorganize_project():
    """プロジェクト構造を整理"""
    
    print("🔧 プロジェクト構造整理開始...")
    
    # プロジェクトルート
    root_dir = Path(__file__).parent.parent
    src_dir = root_dir / "src"
    
    # 新しい構造を作成
    new_structure = {
        "src_new": {
            "core": ["fanza", "grok", "wordpress", "spreadsheet"],
            "utils": ["logger", "config", "cache", "security"],
            "scheduler": ["vps_orchestrator"]
        }
    }
    
    # バックアップディレクトリ作成
    backup_dir = root_dir / "backup_old_structure"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    
    print("📦 既存構造をバックアップ中...")
    shutil.copytree(src_dir, backup_dir)
    
    # 新しいsrc構造を作成
    new_src = root_dir / "src_new"
    if new_src.exists():
        shutil.rmtree(new_src)
    new_src.mkdir()
    
    print("📁 新しいディレクトリ構造を作成中...")
    
    # core/fanza - FANZA関連
    fanza_dir = new_src / "core" / "fanza"
    fanza_dir.mkdir(parents=True)
    
    # 最良のFANZAファイルを選択してコピー
    best_fanza_file = src_dir / "fanza" / "fanza_data_retriever.py"
    if best_fanza_file.exists():
        shutil.copy2(best_fanza_file, fanza_dir / "data_retriever.py")
    
    # core/grok - Grok AI関連
    grok_dir = new_src / "core" / "grok"
    grok_dir.mkdir(parents=True)
    
    # 最良のGrokファイルを選択
    best_grok_files = [
        (src_dir / "grok" / "grok_analyzer.py", "analyzer.py"),
        (src_dir / "modules" / "grok" / "face_processor.py", "face_processor.py")
    ]
    
    for src_file, dst_name in best_grok_files:
        if src_file.exists():
            shutil.copy2(src_file, grok_dir / dst_name)
    
    # core/wordpress - WordPress関連
    wp_dir = new_src / "core" / "wordpress"
    wp_dir.mkdir(parents=True)
    
    # 最良のWordPressファイルを選択
    best_wp_files = [
        (src_dir / "modules" / "wordpress" / "wordpress_poster.py", "poster.py"),
        (src_dir / "wordpress" / "wordpress_article_generator.py", "article_generator.py")
    ]
    
    for src_file, dst_name in best_wp_files:
        if src_file.exists():
            shutil.copy2(src_file, wp_dir / dst_name)
    
    # core/spreadsheet - スプレッドシート関連
    sheet_dir = new_src / "core" / "spreadsheet"
    sheet_dir.mkdir(parents=True)
    
    sheet_file = src_dir / "spreadsheet" / "spreadsheet_manager.py"
    if sheet_file.exists():
        shutil.copy2(sheet_file, sheet_dir / "manager.py")
    
    # utils/logger - ログ関連
    logger_dir = new_src / "utils" / "logger"
    logger_dir.mkdir(parents=True)
    
    logger_files = [
        (src_dir / "utils" / "logger.py", "logger.py"),
        (src_dir / "logger" / "error_logger.py", "error_logger.py")
    ]
    
    for src_file, dst_name in logger_files:
        if src_file.exists():
            shutil.copy2(src_file, logger_dir / dst_name)
    
    # utils/config - 設定関連
    config_dir = new_src / "utils" / "config"
    config_dir.mkdir(parents=True)
    
    config_files = [
        (src_dir / "config" / "config_manager.py", "config_manager.py"),
        (src_dir / "config" / "security_manager.py", "security_manager.py")
    ]
    
    for src_file, dst_name in config_files:
        if src_file.exists():
            shutil.copy2(src_file, config_dir / dst_name)
    
    # utils/cache - キャッシュ関連
    cache_dir = new_src / "utils" / "cache"
    cache_dir.mkdir(parents=True)
    
    cache_file = src_dir / "utils" / "cache_manager.py"
    if cache_file.exists():
        shutil.copy2(cache_file, cache_dir / "cache_manager.py")
    
    # scheduler - スケジューラー関連
    scheduler_dir = new_src / "scheduler"
    scheduler_dir.mkdir(parents=True)
    
    # VPS向けオーケストレーターをコピー
    vps_orchestrator = src_dir / "scheduler" / "vps_simple_orchestrator.py"
    if vps_orchestrator.exists():
        shutil.copy2(vps_orchestrator, scheduler_dir / "vps_orchestrator.py")
    
    # メインファイル
    main_files = [
        (src_dir / "vps_main.py", "vps_main.py"),
        (src_dir / "main.py", "main_legacy.py")  # レガシー版として保持
    ]
    
    for src_file, dst_name in main_files:
        if src_file.exists():
            shutil.copy2(src_file, new_src / dst_name)
    
    # __init__.pyファイルを作成
    init_dirs = [
        new_src,
        new_src / "core",
        new_src / "core" / "fanza",
        new_src / "core" / "grok", 
        new_src / "core" / "wordpress",
        new_src / "core" / "spreadsheet",
        new_src / "utils",
        new_src / "utils" / "logger",
        new_src / "utils" / "config",
        new_src / "utils" / "cache",
        new_src / "scheduler"
    ]
    
    for init_dir in init_dirs:
        (init_dir / "__init__.py").touch()
    
    print("✅ 新しい構造作成完了")
    print(f"📂 バックアップ: {backup_dir}")
    print(f"📂 新構造: {new_src}")
    
    return new_src

def create_structure_readme(new_src_dir):
    """新しい構造の説明ファイルを作成"""
    
    readme_content = """# 整理後のプロジェクト構造

```
src_new/
├── vps_main.py              # VPS向けメインエントリーポイント
├── main_legacy.py           # 従来版（参考用）
├── core/                    # コア機能
│   ├── fanza/
│   │   └── data_retriever.py    # FANZA API & スクレイピング
│   ├── grok/
│   │   ├── analyzer.py          # Grok AI分析
│   │   └── face_processor.py    # 顔認識処理
│   ├── wordpress/
│   │   ├── poster.py            # WordPress投稿
│   │   └── article_generator.py # 記事生成
│   └── spreadsheet/
│       └── manager.py           # Google Sheets管理
├── utils/                   # ユーティリティ
│   ├── logger/
│   │   ├── logger.py            # 基本ログ
│   │   └── error_logger.py      # エラーログ
│   ├── config/
│   │   ├── config_manager.py    # 設定管理
│   │   └── security_manager.py  # セキュリティ
│   └── cache/
│       └── cache_manager.py     # キャッシュ管理
└── scheduler/
    └── vps_orchestrator.py      # VPS向けオーケストレーター
```

## 変更点

### 削除された重複ファイル
- 複数のgrok_analyzer.py → core/grok/analyzer.py に統合
- 複数のwordpress_poster.py → core/wordpress/poster.py に統合
- 散在していたモニタリング関連 → utils/logger/ に統合

### 統合されたディレクトリ
- analyzer/ + grok/ + grok_analyzer/ → core/grok/
- wordpress/ + wordpress_poster/ + modules/wordpress/ → core/wordpress/
- monitor/ + monitoring/ → utils/logger/
- error/ + logger/ → utils/logger/

### 最適化された構造
- VPS向けの軽量化
- 明確な責任分離
- 重複の排除
- 保守性の向上

## 使用方法

```bash
# VPS向け実行
python src_new/vps_main.py --mode daily --max-posts 3

# 従来版実行（参考）
python src_new/main_legacy.py --daily
```
"""
    
    readme_path = new_src_dir / "STRUCTURE.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"📝 構造説明ファイル作成: {readme_path}")

if __name__ == "__main__":
    try:
        new_src = reorganize_project()
        create_structure_readme(new_src)
        
        print("\n🎉 プロジェクト整理完了!")
        print("\n次の手順:")
        print("1. src_new/ の動作確認")
        print("2. 問題なければ src/ を削除して src_new/ を src/ にリネーム")
        print("3. import文を新しい構造に合わせて修正")
        
    except Exception as e:
        print(f"❌ エラー: {e}")