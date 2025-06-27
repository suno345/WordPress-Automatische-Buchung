#!/usr/bin/env python3
"""
スプレッドシート重複削除実行スクリプト

使用方法:
  python scripts/remove_duplicates.py [--products] [--keywords] [--all]
  
オプション:
  --products : 商品管理シートの重複削除のみ
  --keywords : キーワード管理シートの重複削除のみ
  --all      : 全ての重複削除を実行
  引数なし   : インタラクティブモード
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.spreadsheet.manager import SpreadsheetManager
from src.utils.duplicate_remover import DuplicateRemover


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='スプレッドシート重複削除ツール')
    parser.add_argument('--products', action='store_true', help='商品管理シートの重複削除のみ')
    parser.add_argument('--keywords', action='store_true', help='キーワード管理シートの重複削除のみ')
    parser.add_argument('--all', action='store_true', help='全ての重複削除を実行')
    parser.add_argument('--detect-only', action='store_true', help='検出のみ（削除しない）')
    
    args = parser.parse_args()
    
    print("🧹 スプレッドシート重複削除ツール")
    print("=" * 50)
    
    try:
        # SpreadsheetManagerの既存機能を使用
        if args.products or args.all:
            print("\n📦 商品管理シートの重複処理を開始...")
            spreadsheet_manager = SpreadsheetManager()
            deleted_count = spreadsheet_manager.cleanup_duplicate_products()
            print(f"✅ 商品重複削除完了: {deleted_count}件削除")
        
        # 高機能版はDuplicateRemoverを使用
        if args.keywords:
            print("\n🔑 キーワード管理シートの重複処理を開始...")
            remover = DuplicateRemover()
            
            if args.detect_only:
                duplicates = remover.detect_keyword_duplicates()
                print(f"📊 検出結果: {len(duplicates)}件の重複キーワード")
            else:
                deleted_count = remover.remove_keyword_duplicates('keep_active')
                print(f"✅ キーワード重複削除完了: {deleted_count}件削除")
        
        # 引数なしの場合はインタラクティブモード
        if not any([args.products, args.keywords, args.all]):
            print("\n【インタラクティブモード】")
            print("利用可能な操作:")
            print("1. 商品重複削除 (SpreadsheetManager)")
            print("2. キーワード重複検出 (DuplicateRemover)")
            print("3. キーワード重複削除 (DuplicateRemover)")
            print("4. 完全クリーンアップ")
            
            choice = input("\n選択してください (1-4): ").strip()
            
            if choice == '1':
                spreadsheet_manager = SpreadsheetManager()
                deleted_count = spreadsheet_manager.cleanup_duplicate_products()
                print(f"✅ 商品重複削除完了: {deleted_count}件削除")
                
            elif choice == '2':
                remover = DuplicateRemover()
                duplicates = remover.detect_keyword_duplicates()
                print(f"📊 検出結果: {len(duplicates)}件の重複キーワード")
                
            elif choice == '3':
                remover = DuplicateRemover()
                deleted_count = remover.remove_keyword_duplicates('keep_active')
                print(f"✅ キーワード重複削除完了: {deleted_count}件削除")
                
            elif choice == '4':
                print("\n🧹 完全クリーンアップを実行...")
                
                # 商品重複削除
                spreadsheet_manager = SpreadsheetManager()
                products_deleted = spreadsheet_manager.cleanup_duplicate_products()
                
                # キーワード重複削除
                remover = DuplicateRemover()
                keywords_deleted = remover.remove_keyword_duplicates('keep_active')
                
                total_deleted = products_deleted + keywords_deleted
                print(f"\n🎉 完全クリーンアップ完了!")
                print(f"   商品削除: {products_deleted}件")
                print(f"   キーワード削除: {keywords_deleted}件")
                print(f"   合計削除: {total_deleted}件")
                
            else:
                print("❌ 無効な選択です")
    
    except KeyboardInterrupt:
        print("\n👋 ユーザーによって中断されました")
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()