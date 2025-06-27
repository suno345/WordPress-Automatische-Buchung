#!/usr/bin/env python3
"""
シンプルなVPS向け構造を作成
"""

import os
import shutil
from pathlib import Path

def create_simple_structure():
    """シンプルな構造を作成"""
    
    root_dir = Path(__file__).parent.parent
    src_dir = root_dir / "src"
    backup_dir = root_dir / "backup_old_structure"
    
    # srcディレクトリクリア
    if src_dir.exists():
        shutil.rmtree(src_dir)
    src_dir.mkdir()
    
    print("📁 シンプルなVPS構造を作成中...")
    
    # 必要最小限のディレクトリ構造
    dirs_to_create = [
        "core/fanza",
        "core/grok", 
        "core/wordpress",
        "core/spreadsheet",
        "utils",
        "scheduler"
    ]
    
    for dir_path in dirs_to_create:
        (src_dir / dir_path).mkdir(parents=True)
        (src_dir / dir_path / "__init__.py").touch()
    
    # 基本__init__.py
    (src_dir / "__init__.py").touch()
    (src_dir / "core" / "__init__.py").touch()
    
    # 必要ファイルをコピー
    file_mappings = [
        # FANZA
        (backup_dir / "fanza/fanza_data_retriever.py", src_dir / "core/fanza/data_retriever.py"),
        
        # Grok
        (backup_dir / "grok/grok_analyzer.py", src_dir / "core/grok/analyzer.py"),
        
        # WordPress  
        (backup_dir / "modules/wordpress/wordpress_poster.py", src_dir / "core/wordpress/poster.py"),
        (backup_dir / "wordpress/wordpress_article_generator.py", src_dir / "core/wordpress/article_generator.py"),
        
        # Spreadsheet
        (backup_dir / "spreadsheet/spreadsheet_manager.py", src_dir / "core/spreadsheet/manager.py"),
        
        # Utils
        (backup_dir / "utils/logger.py", src_dir / "utils/logger.py"),
        (backup_dir / "utils/fanza_scraper.py", src_dir / "utils/fanza_scraper.py"),
        (backup_dir / "config/config_manager.py", src_dir / "utils/config_manager.py"),
        (backup_dir / "logger/error_logger.py", src_dir / "utils/error_logger.py"),
        
        # Scheduler
        (backup_dir / "scheduler/vps_simple_orchestrator.py", src_dir / "scheduler/vps_orchestrator.py"),
        
        # Main
        (backup_dir / "vps_main.py", src_dir / "vps_main.py")
    ]
    
    for src_file, dst_file in file_mappings:
        if src_file.exists():
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            print(f"✅ {src_file.name} → {dst_file}")
        else:
            print(f"⚠️  {src_file.name} が見つかりません")
    
    print("🎉 シンプル構造作成完了!")
    return src_dir

if __name__ == "__main__":
    create_simple_structure()