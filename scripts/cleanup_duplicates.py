#!/usr/bin/env python3
"""
スプレッドシート重複商品削除ユーティリティ
商品管理シートから重複商品を検出・削除します
"""

import sys
import os
from pathlib import Path

# パスの設定
sys.path.append(str(Path(__file__).parent.parent))

from src.core.spreadsheet.manager import SpreadsheetManager
from src.utils.logger import Logger

def main():
    """重複商品削除メイン処理"""
    print("=== スプレッドシート重複商品削除ユーティリティ ===")
    
    try:
        # SpreadsheetManagerの初期化
        sheet_manager = SpreadsheetManager()
        logger = Logger.get_logger("cleanup_duplicates")
        
        print("🔍 重複商品の検出と削除を開始します...")
        
        # 重複商品削除実行
        deleted_count = sheet_manager.cleanup_duplicate_products()
        
        if deleted_count > 0:
            print(f"✅ 処理完了: {deleted_count}件の重複商品を削除しました")
            logger.info(f"重複商品削除完了: {deleted_count}件")
        else:
            print("📋 削除対象の重複商品はありませんでした")
            logger.info("重複商品削除: 削除対象なし")
            
        # 整形処理も実行（オプション）
        print("\n🔧 商品管理シートの整形を実行します...")
        format_result = sheet_manager.format_product_sheet()
        
        if format_result:
            print("✅ シート整形完了")
            logger.info("商品管理シート整形完了")
        else:
            print("⚠️  シート整形中にエラーが発生しました")
            logger.warning("商品管理シート整形エラー")
        
        print("\n=== 処理完了 ===")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        logger = Logger.get_logger("cleanup_duplicates")
        logger.error(f"重複商品削除エラー: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()