#!/usr/bin/env python3
"""
スプレッドシート重複削除ユーティリティ

機能:
1. 商品管理シートの重複商品を検出・削除
2. キーワード管理シートの重複キーワードを検出・削除
3. バックアップ機能付きの安全な削除
4. 詳細なログ出力と削除レポート
"""

import os
import sys
from typing import List, Dict, Set, Tuple, Optional
from datetime import datetime
import re
import time

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.core.spreadsheet.manager import SpreadsheetManager
from src.monitor.monitor import Monitor


class DuplicateRemover:
    """スプレッドシート重複削除クラス"""
    
    def __init__(self):
        self.spreadsheet_manager = SpreadsheetManager()
        self.monitor = Monitor()
        self.deleted_records = []
        self.backup_data = {}
        
    def create_backup(self, sheet_name: str) -> bool:
        """
        削除前にシートのバックアップを作成
        
        Args:
            sheet_name: バックアップ対象のシート名
            
        Returns:
            bool: バックアップ成功可否
        """
        try:
            print(f"📋 {sheet_name}のバックアップを作成中...")
            
            # 全データを取得
            values = self.spreadsheet_manager._get_sheet_values(sheet_name, 'A:Z')
            if not values:
                print(f"⚠️  {sheet_name}にデータがありません")
                return False
            
            # バックアップデータを保存
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.backup_data[sheet_name] = {
                'timestamp': timestamp,
                'data': values,
                'row_count': len(values)
            }
            
            print(f"✅ バックアップ完了: {len(values)}行のデータを保存")
            return True
            
        except Exception as e:
            self.monitor.log_error(f"{sheet_name}のバックアップ作成に失敗: {str(e)}")
            return False
    
    def detect_product_duplicates(self) -> List[Dict]:
        """
        商品管理シートの重複商品を検出
        
        Returns:
            List[Dict]: 重複商品の詳細情報
        """
        try:
            print("🔍 商品管理シートの重複商品を検出中...")
            
            # 商品管理シートからデータを取得
            values = self.spreadsheet_manager._get_sheet_values('商品管理', 'A2:I1000')
            if not values:
                print("📋 商品管理シートにデータがありません")
                return []
            
            # 品番別にデータをグループ化
            product_groups = {}
            duplicates = []
            
            for idx, row in enumerate(values, start=2):
                if len(row) < 4:
                    continue
                
                # D列から品番を抽出
                product_url = row[3] if len(row) > 3 else ''
                product_code = self.spreadsheet_manager.extract_product_code(str(product_url))
                
                if not product_code:
                    continue
                
                row_data = {
                    'row_index': idx,
                    'product_code': product_code,
                    'status': str(row[0]).strip() if row[0] else '',
                    'original_work': str(row[1]).strip() if len(row) > 1 else '',
                    'character_name': str(row[2]).strip() if len(row) > 2 else '',
                    'product_url': product_url,
                    'title': str(row[4]).strip() if len(row) > 4 else '',
                    'reserve_date': str(row[5]).strip() if len(row) > 5 else '',
                    'post_url': str(row[6]).strip() if len(row) > 6 else '',
                    'last_processed': str(row[7]).strip() if len(row) > 7 else '',
                    'error_details': str(row[8]).strip() if len(row) > 8 else ''
                }
                
                if product_code not in product_groups:
                    product_groups[product_code] = []
                product_groups[product_code].append(row_data)
            
            # 重複商品を特定
            for product_code, group in product_groups.items():
                if len(group) > 1:
                    duplicates.extend(group)
                    print(f"🔍 重複発見: {product_code} ({len(group)}件)")
            
            print(f"📊 検出結果: {len(duplicates)}件の重複商品")
            return duplicates
            
        except Exception as e:
            self.monitor.log_error(f"重複商品の検出に失敗: {str(e)}")
            return []
    
    def detect_keyword_duplicates(self) -> List[Dict]:
        """
        キーワード管理シートの重複キーワードを検出
        
        Returns:
            List[Dict]: 重複キーワードの詳細情報
        """
        try:
            print("🔍 キーワード管理シートの重複キーワードを検出中...")
            
            # キーワード管理シートからデータを取得
            values = self.spreadsheet_manager._get_sheet_values('キーワード管理', 'A2:G1000')
            if not values:
                print("📋 キーワード管理シートにデータがありません")
                return []
            
            # キーワード別にデータをグループ化
            keyword_groups = {}
            duplicates = []
            
            for idx, row in enumerate(values, start=2):
                if len(row) < 4:
                    continue
                
                # D列のFANZA検索キーワードを取得
                keyword = str(row[3]).strip() if len(row) > 3 else ''
                if not keyword:
                    continue
                
                row_data = {
                    'row_index': idx,
                    'processed_flag': str(row[0]).strip() if row[0] else '',
                    'original_work': str(row[1]).strip() if len(row) > 1 else '',
                    'character_name': str(row[2]).strip() if len(row) > 2 else '',
                    'keyword': keyword,
                    'last_processed': str(row[4]).strip() if len(row) > 4 else '',
                    'last_result': str(row[5]).strip() if len(row) > 5 else '',
                    'notes': str(row[6]).strip() if len(row) > 6 else ''
                }
                
                if keyword not in keyword_groups:
                    keyword_groups[keyword] = []
                keyword_groups[keyword].append(row_data)
            
            # 重複キーワードを特定
            for keyword, group in keyword_groups.items():
                if len(group) > 1:
                    duplicates.extend(group)
                    print(f"🔍 重複発見: '{keyword}' ({len(group)}件)")
            
            print(f"📊 検出結果: {len(duplicates)}件の重複キーワード")
            return duplicates
            
        except Exception as e:
            self.monitor.log_error(f"重複キーワードの検出に失敗: {str(e)}")
            return []
    
    def remove_product_duplicates(self, strategy: str = 'keep_latest_processed') -> int:
        """
        商品管理シートの重複商品を削除
        
        Args:
            strategy: 削除戦略 ('keep_latest_processed', 'keep_first', 'interactive')
            
        Returns:
            int: 削除した商品数
        """
        try:
            print("🗑️  重複商品の削除を開始...")
            
            # バックアップ作成
            if not self.create_backup('商品管理'):
                print("❌ バックアップの作成に失敗しました。削除を中止します。")
                return 0
            
            # 重複商品を検出
            duplicates = self.detect_product_duplicates()
            if not duplicates:
                print("✅ 削除対象の重複商品はありませんでした")
                return 0
            
            # 品番別にグループ化
            product_groups = {}
            for item in duplicates:
                code = item['product_code']
                if code not in product_groups:
                    product_groups[code] = []
                product_groups[code].append(item)
            
            # 削除戦略に基づいて削除対象を決定
            rows_to_delete = []
            protected_statuses = {
                '予約投稿', '投稿済み', '投稿完了', '公開済み', '処理済み',
                '下書き保存', '下書き', 'draft', 'published', 'scheduled'
            }
            
            for product_code, group in product_groups.items():
                # 保護されたアイテムと未処理アイテムを分離
                protected_items = [item for item in group if item['status'] in protected_statuses]
                unprocessed_items = [item for item in group if item['status'] not in protected_statuses]
                
                if strategy == 'keep_latest_processed':
                    # 最新の処理済みを保持、未処理を削除
                    if protected_items:
                        # 処理済みがある場合は未処理をすべて削除
                        rows_to_delete.extend(unprocessed_items)
                    elif len(unprocessed_items) > 1:
                        # 未処理のみの場合は最新を除いて削除
                        sorted_items = sorted(unprocessed_items, key=lambda x: x['row_index'])
                        rows_to_delete.extend(sorted_items[:-1])
                        
                elif strategy == 'keep_first':
                    # 最初のアイテムを保持
                    sorted_items = sorted(group, key=lambda x: x['row_index'])
                    if len(sorted_items) > 1:
                        rows_to_delete.extend(sorted_items[1:])
            
            if not rows_to_delete:
                print("✅ 削除対象の商品はありませんでした")
                return 0
            
            print(f"🗑️  削除対象: {len(rows_to_delete)}件")
            for item in rows_to_delete:
                print(f"   Row {item['row_index']}: {item['product_code']} (ステータス: '{item['status']}')")
            
            # 確認プロンプト
            if strategy != 'interactive':
                confirm = input("\n削除を実行しますか？ (y/N): ")
                if confirm.lower() != 'y':
                    print("❌ 削除をキャンセルしました")
                    return 0
            
            # 削除実行（後ろから削除してインデックスのずれを防ぐ）
            rows_to_delete.sort(key=lambda x: x['row_index'], reverse=True)
            deleted_count = 0
            
            for item in rows_to_delete:
                try:
                    # レート制限対策
                    self.spreadsheet_manager._wait_for_rate_limit()
                    
                    # 行を削除
                    sheet_id = self.spreadsheet_manager._get_sheet_id('商品管理')
                    self.spreadsheet_manager.service.spreadsheets().batchUpdate(
                        spreadsheetId=self.spreadsheet_manager.spreadsheet_id,
                        body={
                            'requests': [{
                                'deleteDimension': {
                                    'range': {
                                        'sheetId': sheet_id,
                                        'dimension': 'ROWS',
                                        'startIndex': item['row_index'] - 1,
                                        'endIndex': item['row_index']
                                    }
                                }
                            }]
                        }
                    ).execute()
                    
                    print(f"✅ 削除完了: Row {item['row_index']} - {item['product_code']}")
                    self.deleted_records.append(item)
                    deleted_count += 1
                    
                except Exception as e:
                    print(f"❌ 削除失敗: Row {item['row_index']} - {item['product_code']}: {str(e)}")
            
            print(f"🎉 重複商品削除完了: {deleted_count}件削除")
            return deleted_count
            
        except Exception as e:
            self.monitor.log_error(f"重複商品の削除に失敗: {str(e)}")
            return 0
    
    def remove_keyword_duplicates(self, strategy: str = 'keep_first') -> int:
        """
        キーワード管理シートの重複キーワードを削除
        
        Args:
            strategy: 削除戦略 ('keep_first', 'keep_active', 'interactive')
            
        Returns:
            int: 削除したキーワード数
        """
        try:
            print("🗑️  重複キーワードの削除を開始...")
            
            # バックアップ作成
            if not self.create_backup('キーワード管理'):
                print("❌ バックアップの作成に失敗しました。削除を中止します。")
                return 0
            
            # 重複キーワードを検出
            duplicates = self.detect_keyword_duplicates()
            if not duplicates:
                print("✅ 削除対象の重複キーワードはありませんでした")
                return 0
            
            # キーワード別にグループ化
            keyword_groups = {}
            for item in duplicates:
                keyword = item['keyword']
                if keyword not in keyword_groups:
                    keyword_groups[keyword] = []
                keyword_groups[keyword].append(item)
            
            # 削除戦略に基づいて削除対象を決定
            rows_to_delete = []
            active_flags = ['true', 'on', '1', 'yes', '✓', 'チェック', 'checked', '✅']
            
            for keyword, group in keyword_groups.items():
                if strategy == 'keep_active':
                    # アクティブなものを保持
                    active_items = [item for item in group if item['processed_flag'].lower() in active_flags]
                    inactive_items = [item for item in group if item['processed_flag'].lower() not in active_flags]
                    
                    if active_items:
                        # アクティブがある場合は非アクティブを削除、複数アクティブがあれば最初以外削除
                        rows_to_delete.extend(inactive_items)
                        if len(active_items) > 1:
                            sorted_active = sorted(active_items, key=lambda x: x['row_index'])
                            rows_to_delete.extend(sorted_active[1:])
                    elif len(inactive_items) > 1:
                        # 非アクティブのみの場合は最初以外削除
                        sorted_items = sorted(inactive_items, key=lambda x: x['row_index'])
                        rows_to_delete.extend(sorted_items[1:])
                        
                elif strategy == 'keep_first':
                    # 最初のアイテムを保持
                    sorted_items = sorted(group, key=lambda x: x['row_index'])
                    if len(sorted_items) > 1:
                        rows_to_delete.extend(sorted_items[1:])
            
            if not rows_to_delete:
                print("✅ 削除対象のキーワードはありませんでした")
                return 0
            
            print(f"🗑️  削除対象: {len(rows_to_delete)}件")
            for item in rows_to_delete:
                print(f"   Row {item['row_index']}: '{item['keyword']}' (フラグ: '{item['processed_flag']}')")
            
            # 確認プロンプト
            if strategy != 'interactive':
                confirm = input("\n削除を実行しますか？ (y/N): ")
                if confirm.lower() != 'y':
                    print("❌ 削除をキャンセルしました")
                    return 0
            
            # 削除実行
            rows_to_delete.sort(key=lambda x: x['row_index'], reverse=True)
            deleted_count = 0
            
            for item in rows_to_delete:
                try:
                    # レート制限対策
                    self.spreadsheet_manager._wait_for_rate_limit()
                    
                    # 行を削除
                    sheet_id = self.spreadsheet_manager._get_sheet_id('キーワード管理')
                    self.spreadsheet_manager.service.spreadsheets().batchUpdate(
                        spreadsheetId=self.spreadsheet_manager.spreadsheet_id,
                        body={
                            'requests': [{
                                'deleteDimension': {
                                    'range': {
                                        'sheetId': sheet_id,
                                        'dimension': 'ROWS',
                                        'startIndex': item['row_index'] - 1,
                                        'endIndex': item['row_index']
                                    }
                                }
                            }]
                        }
                    ).execute()
                    
                    print(f"✅ 削除完了: Row {item['row_index']} - '{item['keyword']}'")
                    self.deleted_records.append(item)
                    deleted_count += 1
                    
                except Exception as e:
                    print(f"❌ 削除失敗: Row {item['row_index']} - '{item['keyword']}': {str(e)}")
            
            print(f"🎉 重複キーワード削除完了: {deleted_count}件削除")
            return deleted_count
            
        except Exception as e:
            self.monitor.log_error(f"重複キーワードの削除に失敗: {str(e)}")
            return 0
    
    def generate_report(self) -> str:
        """
        削除レポートを生成
        
        Returns:
            str: 削除レポート
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        report = f"""
=== スプレッドシート重複削除レポート ===
実行日時: {timestamp}
削除件数: {len(self.deleted_records)}件

【削除された項目】
"""
        
        for i, record in enumerate(self.deleted_records, 1):
            if 'product_code' in record:
                report += f"{i:3d}. 商品: {record['product_code']} (Row {record['row_index']})\n"
            elif 'keyword' in record:
                report += f"{i:3d}. キーワード: '{record['keyword']}' (Row {record['row_index']})\n"
        
        report += f"\n=== レポート終了 ===\n"
        return report
    
    def run_full_cleanup(self) -> Dict[str, int]:
        """
        完全な重複削除を実行
        
        Returns:
            Dict[str, int]: 削除結果
        """
        print("🧹 スプレッドシート完全クリーンアップを開始...")
        
        results = {
            'products_deleted': 0,
            'keywords_deleted': 0,
            'total_deleted': 0
        }
        
        # 商品重複削除
        print("\n" + "="*50)
        print("📦 商品管理シートの重複削除")
        print("="*50)
        results['products_deleted'] = self.remove_product_duplicates()
        
        # キーワード重複削除
        print("\n" + "="*50)
        print("🔑 キーワード管理シートの重複削除")
        print("="*50)
        results['keywords_deleted'] = self.remove_keyword_duplicates()
        
        results['total_deleted'] = results['products_deleted'] + results['keywords_deleted']
        
        # レポート生成
        print("\n" + "="*50)
        print("📊 削除レポート")
        print("="*50)
        print(self.generate_report())
        
        return results


def main():
    """メイン関数"""
    print("🧹 スプレッドシート重複削除ツール")
    print("="*50)
    
    try:
        remover = DuplicateRemover()
        
        # メニュー表示
        while True:
            print("\n【メニュー】")
            print("1. 商品重複検出のみ")
            print("2. キーワード重複検出のみ")
            print("3. 商品重複削除")
            print("4. キーワード重複削除")
            print("5. 完全クリーンアップ（全削除）")
            print("0. 終了")
            
            choice = input("\n選択してください (0-5): ").strip()
            
            if choice == '0':
                print("👋 終了します")
                break
            elif choice == '1':
                remover.detect_product_duplicates()
            elif choice == '2':
                remover.detect_keyword_duplicates()
            elif choice == '3':
                remover.remove_product_duplicates()
            elif choice == '4':
                remover.remove_keyword_duplicates()
            elif choice == '5':
                remover.run_full_cleanup()
            else:
                print("❌ 無効な選択です")
    
    except KeyboardInterrupt:
        print("\n👋 ユーザーによって中断されました")
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")


if __name__ == "__main__":
    main()