import os
from typing import List, Dict, Optional, Any
from datetime import datetime
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from src.monitor.monitor import Monitor
import re
import time
import threading

class SpreadsheetManager:
    def __init__(self):
        self.monitor = Monitor()
        self.spreadsheet_id = os.getenv('GOOGLE_SHEETS_ID')
        
        # シート名の定義
        self.keyword_sheet = 'キーワード管理'
        self.product_sheet = '商品管理'
        
        # レート制限対策
        self._request_count = 0
        self._last_request_time = 0
        self._request_lock = threading.Lock()
        self._max_requests_per_minute = 50  # 安全マージンを考慮して50に設定
        self._min_request_interval = 1.2  # 最小リクエスト間隔（秒）
        
        # Google Sheets APIクライアントの初期化
        self.service = self._init_sheets_service()

    def _wait_for_rate_limit(self):
        """レート制限を考慮した待機処理"""
        with self._request_lock:
            current_time = time.time()
            
            # 前回のリクエストから最小間隔が経過していない場合は待機
            time_since_last_request = current_time - self._last_request_time
            if time_since_last_request < self._min_request_interval:
                wait_time = self._min_request_interval - time_since_last_request
                print(f"[INFO] レート制限対策: {wait_time:.2f}秒待機中...")
                time.sleep(wait_time)
                current_time = time.time()
            
            # 1分間のリクエスト数をリセット（60秒経過した場合）
            if current_time - self._last_request_time > 60:
                self._request_count = 0
            
            # リクエスト数が上限に達している場合は待機
            if self._request_count >= self._max_requests_per_minute:
                wait_time = 60 - (current_time - self._last_request_time)
                if wait_time > 0:
                    print(f"[INFO] レート制限対策: 1分間のリクエスト上限に達したため{wait_time:.2f}秒待機中...")
                    time.sleep(wait_time)
                    self._request_count = 0
            
            self._request_count += 1
            self._last_request_time = time.time()
            print(f"[DEBUG] APIリクエスト実行 (今分のリクエスト数: {self._request_count}/{self._max_requests_per_minute})")

    def _init_sheets_service(self):
        """Google Sheets APIクライアントを初期化"""
        try:
            # Google Sheets APIのスコープを設定
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

            # サービスアカウントキーファイルへのパスを環境変数から取得
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

            if not credentials_path:
                # 環境変数が未設定の場合、デフォルトのパスを使用
                current_dir = os.path.dirname(__file__)
                credentials_path = os.path.join(current_dir, '..', '..', 'credentials.json')
                print(f"[INFO] 環境変数 GOOGLE_APPLICATION_CREDENTIALS が未設定のため、デフォルトパスを使用します: {credentials_path}")

            # パスを正規化
            credentials_path = os.path.normpath(credentials_path)

            # サービスアカウントキーファイルが存在するか確認
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(f"サービスアカウントキーファイルが見つかりません: {credentials_path}")

            credentials = service_account.Credentials.from_service_account_file(
                credentials_path, scopes=SCOPES)

            service = build('sheets', 'v4', credentials=credentials)
            print("[INFO] Google Sheets APIクライアントの初期化に成功")
            return service
        except Exception as e:
            self.monitor.log_error(f"Google Sheets APIクライアントの初期化に失敗: {str(e)}")
            return None

    def _get_sheet_values(self, sheet_name: str, range_name: str, value_render_option: str = 'FORMATTED_VALUE') -> List[List]:
        """シートの値を取得"""
        try:
            # レート制限対策
            self._wait_for_rate_limit()
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f'{sheet_name}!{range_name}',
                valueRenderOption=value_render_option
            ).execute()
            values = result.get('values', [])
            
            # デバッグ出力を簡略化（大量のデータの場合）
            if len(values) > 10:
                print(f"Debug in _get_sheet_values: sheet_name={sheet_name}, range_name={range_name}, rows_count={len(values)}")
            else:
                print(f"Debug in _get_sheet_values: sheet_name={sheet_name}, range_name={range_name}, values={values}")

            return values
        except Exception as e:
            self.monitor.log_error(f"シートの値の取得に失敗: {str(e)}")
            return []

    def _update_sheet_values(self, sheet_name: str, range_name: str, values: List[List]) -> bool:
        """シートの値を更新"""
        try:
            # レート制限対策
            self._wait_for_rate_limit()
            
            body = {'values': values}
            # HYPERLINK関数が含まれていればUSER_ENTERED、なければRAW
            value_input_option = 'USER_ENTERED' if any(
                any(isinstance(cell, str) and cell.startswith('=HYPERLINK(') for cell in row)
                for row in values
            ) else 'RAW'
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f'{sheet_name}!{range_name}',
                valueInputOption=value_input_option,
                body=body
            ).execute()
            return True
        except Exception as e:
            self.monitor.log_error(f"シートの値の更新に失敗: {str(e)}")
            return False

    def get_active_keywords(self) -> List[Dict]:
        """処理対象のキーワードを取得"""
        try:
            # シートからデータを取得
            values = self._get_sheet_values(self.keyword_sheet, 'A:G')
            if not values:
                return []

            # ヘッダー行を取得
            headers = values[0]
            
            # 処理対象のキーワードを抽出
            active_keywords = []
            processed_count = 0
            skipped_count = 0
            
            for row_index, row in enumerate(values[1:]):  # ヘッダーをスキップ
                # 空行や不完全な行をスキップ
                if len(row) < 4 or not any(row):
                    skipped_count += 1
                    continue
                
                processed_count += 1
                
                # 処理フラグがON（True）の場合のみ処理対象とする
                processed_flag_raw = row[0] if len(row) > 0 else ''
                processed_flag = str(processed_flag_raw).strip().lower()
                
                # デバッグ出力を最小限に（TRUEの場合のみ）
                if processed_flag in ['true', 'on', '1', 'yes', '✓', 'チェック', 'checked', '✅']:
                    print(f"Debug in get_active_keywords: Found active keyword at row {row_index + 2}: {row}")
                    
                    keyword_data = {
                        'original_work': row[1] if len(row) > 1 else '',           # 原作名
                        'character_name': row[2] if len(row) > 2 else '',          # キャラクター名
                        'keyword': row[3] if len(row) > 3 else '',                 # FANZA検索キーワード
                        'last_processed': row[4] if len(row) > 4 else None,  # 最終処理日時
                        'last_result': row[5] if len(row) > 5 else None,    # 最終処理結果
                        'notes': row[6] if len(row) > 6 else None           # 備考
                    }
                    
                    # キーワードカラムが空でない場合のみ追加
                    if keyword_data['keyword']:
                        active_keywords.append(keyword_data)
                        print(f"Debug in get_active_keywords: Added keyword: '{keyword_data['keyword']}' for {keyword_data['character_name']}")
            
            print(f"Debug in get_active_keywords: Processed {processed_count} rows, skipped {skipped_count} empty rows")
            print(f"Debug in get_active_keywords: Final active_keywords count: {len(active_keywords)}")

            return active_keywords

        except Exception as e:
            self.monitor.log_error(f"キーワードの取得に失敗: {str(e)}")
            return []

    def update_keyword_status(self, keyword: str, status: str, result: Optional[str] = None) -> bool:
        """キーワードの処理状態を更新"""
        try:
            # 現在のデータを取得
            values = self._get_sheet_values(self.keyword_sheet, 'A:F')
            if not values:
                return False

            # キーワードに一致する行を探す
            for i, row in enumerate(values[1:], start=2):  # ヘッダーをスキップ
                if len(row) >= 3 and row[2] == keyword:
                    # 更新するデータ
                    update_range = f'D{i}:E{i}'
                    update_values = [[
                        datetime.now().isoformat(),  # 最終処理日時
                        status + (f": {result}" if result else "")  # 最終処理結果
                    ]]
                    
                    # スプレッドシートを更新
                    return self._update_sheet_values(self.keyword_sheet, update_range, update_values)
            
            return False

        except Exception as e:
            self.monitor.log_error(f"キーワードの状態更新に失敗: {str(e)}")
            return False

    def get_next_keyword_to_process(self) -> Optional[Dict]:
        """次に処理すべきキーワードを取得（最終処理日時の古い順）"""
        try:
            # A列がTRUEのキーワードを取得
            active_keywords = self.get_active_keywords()
            if not active_keywords:
                print("Debug: アクティブなキーワードが見つかりません")
                return None
            
            # 最終処理日時でソート（未処理または古い順）
            def parse_datetime(date_str):
                if not date_str or date_str.strip() == '':
                    return datetime.min  # 未処理の場合は最も古い日時として扱う
                try:
                    # ISO形式で解析を試行
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        # 一般的な日時形式で解析を試行
                        return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        return datetime.min  # パースできない場合は最も古い日時として扱う
            
            # 最終処理日時でソート
            sorted_keywords = sorted(active_keywords, key=lambda x: parse_datetime(x.get('last_processed', '')))
            
            # 最も古い（または未処理の）キーワードを返す
            next_keyword = sorted_keywords[0]
            print(f"Debug: 次の処理対象キーワード: {next_keyword['keyword']} (最終処理: {next_keyword.get('last_processed', '未処理')})")
            
            return next_keyword
            
        except Exception as e:
            self.monitor.log_error(f"次のキーワード取得に失敗: {str(e)}")
            return None

    def update_keyword_last_processed(self, keyword: str, character_name: str = None) -> bool:
        """キーワードの最終処理日時を更新"""
        try:
            # 現在のデータを取得
            values = self._get_sheet_values(self.keyword_sheet, 'A:G')
            if not values:
                return False

            # キーワードまたはキャラクター名に一致する行を探す
            for i, row in enumerate(values[1:], start=2):  # ヘッダーをスキップ
                row_keyword = row[3] if len(row) > 3 else ''
                row_character = row[2] if len(row) > 2 else ''
                
                # キーワードまたはキャラクター名で一致判定
                if (keyword and row_keyword == keyword) or (character_name and row_character == character_name):
                    # E列（最終処理日時）を更新
                    update_range = f'E{i}'
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    update_values = [[current_time]]
                    
                    print(f"Debug: キーワード '{keyword}' (キャラ: {character_name}) の最終処理日時を更新: {current_time}")
                    
                    # スプレッドシートを更新
                    return self._update_sheet_values(self.keyword_sheet, update_range, update_values)
            
            print(f"Warning: キーワード '{keyword}' (キャラ: {character_name}) が見つかりませんでした")
            return False

        except Exception as e:
            self.monitor.log_error(f"最終処理日時の更新に失敗: {str(e)}")
            return False

    def get_sequential_keywords_for_48posts(self, start_count: int = 48) -> List[Dict]:
        """48件投稿用の順次キーワード取得"""
        try:
            # A列がTRUEのキーワードを取得
            active_keywords = self.get_active_keywords()
            if not active_keywords:
                return []
            
            # 最終処理日時でソート（古い順）
            def parse_datetime(date_str):
                if not date_str or date_str.strip() == '':
                    return datetime.min
                try:
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        return datetime.min
            
            sorted_keywords = sorted(active_keywords, key=lambda x: parse_datetime(x.get('last_processed', '')))
            
            # 必要な件数分のキーワードを循環して取得
            result_keywords = []
            keyword_count = len(sorted_keywords)
            
            if keyword_count == 0:
                return []
            
            for i in range(start_count):
                keyword_index = i % keyword_count  # 循環させる
                result_keywords.append(sorted_keywords[keyword_index])
            
            print(f"Debug: 48件投稿用に {len(result_keywords)} 件のキーワードを準備しました")
            return result_keywords
            
        except Exception as e:
            self.monitor.log_error(f"順次キーワード取得に失敗: {str(e)}")
            return []

    def _convert_product_id_to_url(self, product_id: str) -> str:
        """
        商品IDをFANZAの商品詳細URL形式に変換する。
        簡易的な変換であり、サービスやフロアによっては異なる形式になる可能性がある。
        """
        # 仮に同人(digital/doujin)のURL形式に変換
        return f"https://www.dmm.co.jp/dc/doujin/-/detail/=/cid={product_id}/"

    def extract_product_code(self, product_identifier: str) -> Optional[str]:
        """
        商品URLまたはHYPERLINK形式から品番（cid）を抽出する
        
        Args:
            product_identifier: 商品URLまたはHYPERLINK形式の文字列
            
        Returns:
            品番（cid）。抽出できない場合はNone
        """
        if not product_identifier or not isinstance(product_identifier, str):
            return None
        
        # HYPERLINK形式の場合、URLを抽出
        if product_identifier.startswith('=HYPERLINK('):
            match = re.search(r'=HYPERLINK\("([^"]+)"', product_identifier)
            if match:
                url = match.group(1)
            else:
                return None
        else:
            url = product_identifier
        
        # URLから品番（cid）を抽出
        match = re.search(r'cid=([^/&]+)', url)
        if match:
            return match.group(1)
        
        return None

    _product_codes_cache = None
    _cache_timestamp = None
    _cache_ttl = 300  # 5分間キャッシュ
    
    def _get_cached_product_codes(self) -> set:
        """既存商品コードをキャッシュ付きで取得"""
        current_time = time.time()
        
        # キャッシュが有効な場合はそれを返す
        if (self._product_codes_cache is not None and 
            self._cache_timestamp is not None and 
            current_time - self._cache_timestamp < self._cache_ttl):
            return self._product_codes_cache
        
        # キャッシュを更新
        sheet_name = '商品管理'
        url_values = self._get_sheet_values(sheet_name, f'D:D')
        
        # HashSetでO(1)検索を実現
        product_codes = set()
        for row in url_values:
            if row:
                code = self.extract_product_code(str(row[0]))
                if code:
                    product_codes.add(code.strip())
        
        self._product_codes_cache = product_codes
        self._cache_timestamp = current_time
        
        print(f"Debug: 商品コードキャッシュを更新 - {len(product_codes)}件")
        return product_codes
    
    def check_product_exists(self, product_identifier: str) -> bool:
        """
        商品管理シートに特定の商品が存在するかチェック（最適化版）
        商品URLまたは商品IDでチェック可能
        """
        # 品番を抽出
        product_code = self.extract_product_code(product_identifier)
        if not product_code:
            print(f"Warning: 有効な品番を抽出できませんでした: {product_identifier}")
            return False

        # キャッシュされたHashSetでO(1)検索
        existing_codes = self._get_cached_product_codes()
        normalized_code = product_code.strip()
        
        return normalized_code in existing_codes
    
    def check_products_batch(self, product_identifiers: list) -> dict:
        """複数商品の重複チェックをバッチ処理"""
        # 1回のシート取得で全商品をチェック
        existing_codes = self._get_cached_product_codes()
        
        results = {}
        for identifier in product_identifiers:
            code = self.extract_product_code(identifier)
            if code:
                results[identifier] = code.strip() in existing_codes
            else:
                results[identifier] = False
                
        return results

    def clear_product_cache(self):
        """商品コードキャッシュをクリア"""
        self._product_codes_cache = None
        self._cache_timestamp = None
        print("Debug: 商品コードキャッシュをクリアしました")

    def add_product(self, product_data: Dict[str, Any]) -> bool:
        """商品情報を追加（商品管理シート9カラム対応）"""
        try:
            # 商品URLが商品IDのように見える場合、URLに変換して保存
            product_url = product_data.get('url', '')
            if product_url and not product_url.startswith("http"):
                product_data['url'] = self._convert_product_id_to_url(product_url)
            
            # 保存する行データを作成（シートのカラム順に合わせる）
            # カラムの順番: 投稿ステータス, 原作名, キャラ名, 商品URL, 商品名, 予約投稿日時, 記事URL, 最終処理日時, エラー詳細

            # D列 (商品URL): 品番表記のハイパーリンク
            product_url = product_data.get('url', '')
            # HYPERLINKから実際のURLを抽出するロジックが必要な場合があるが、
            # ここではproduct_data['商品URL']が既に =HYPERLINK("URL", "TEXT") 形式か、生のURLであることを想定
            actual_product_url = ''
            product_id_for_link = ''
            if isinstance(product_url, str) and product_url.startswith('=HYPERLINK("'):
                match = re.search(r'=HYPERLINK\("([^\"]+)\", \"([^\"]+)\"\)', product_url)
                if match:
                    actual_product_url = match.group(1)
                    product_id_for_link = match.group(2)
                else: # パース失敗時は元の値をそのまま使う（フォールバック）
                    actual_product_url = product_url 
            else:
                actual_product_url = product_url # 数式でなければそのままURLとみなす
                # product_id_for_link は別途 product_data から取得するか、URLから抽出
                product_id_from_data = product_data.get('品番') # 仮のキー、実際には存在しないかも
                if product_id_from_data:
                    product_id_for_link = product_id_from_data
                elif actual_product_url:
                    product_id_for_link = self.extract_product_code(actual_product_url)
            
            escaped_actual_product_url = actual_product_url.replace('"', '""')
            escaped_product_id_for_link = product_id_for_link.replace('"', '""')
            product_url_cell = f'=HYPERLINK("{escaped_actual_product_url}", "{escaped_product_id_for_link}")' if escaped_actual_product_url and escaped_product_id_for_link else ''

            # F列 (予約投稿日時) および H列 (最終処理日時): MM/DD hh:mm 形式
            reserve_date_str = product_data.get('reserve_date', '')
            try:
                # ISO形式などdatetimeで解析可能な形式を想定
                reserve_date_formatted = datetime.fromisoformat(reserve_date_str).strftime('%m/%d %H:%M') if reserve_date_str else ''
            except ValueError:
                reserve_date_formatted = reserve_date_str # 解析失敗時は元の文字列をそのまま使用

            last_processed_str = product_data.get('last_processed', '')
            try:
                # ISO形式などdatetimeで解析可能な形式を想定
                last_processed_formatted = datetime.fromisoformat(last_processed_str).strftime('%m/%d %H:%M') if last_processed_str else ''
            except ValueError:
                last_processed_formatted = last_processed_str # 解析失敗時は元の文字列をそのまま使用

            # G列 (記事URL): 記事ID表記のハイパーリンク
            article_url = product_data.get('post_url', '')
            actual_article_url = ''
            article_id_for_link = ''

            if isinstance(article_url, str) and article_url.startswith('=HYPERLINK("'):
                match = re.search(r'=HYPERLINK\("([^\"]+)\", \"([^\"]+)\"\)', article_url)
                if match:
                    actual_article_url = match.group(1)
                    article_id_for_link = match.group(2)
                else: # パース失敗時は元の値をそのまま使う（フォールバック）
                    actual_article_url = article_url
            else:
                actual_article_url = article_url # 数式でなければそのままURLとみなす
                # article_id_for_link は別途 product_data から取得するか、URLから抽出
                post_id_from_data = product_data.get('記事ID') # 仮のキー
                if post_id_from_data:
                    article_id_for_link = str(post_id_from_data)
                elif actual_article_url:
                    # URLから記事IDを抽出（/?p=ID または /archives/ID 形式を想定）
                    match_p = re.search(r'/?p=(\\d+)', actual_article_url)
                    if match_p:
                        article_id_for_link = match_p.group(1)
                    else:
                        match_arc = re.search(r'/archives/(\\d+)', actual_article_url)
                        if match_arc:
                            article_id_for_link = match_arc.group(1)

            escaped_actual_article_url = actual_article_url.replace('"', '""')
            escaped_article_id_for_link = article_id_for_link.replace('"', '""')
            article_url_cell = f'=HYPERLINK("{escaped_actual_article_url}", "{escaped_article_id_for_link}")' if escaped_actual_article_url and escaped_article_id_for_link else ''

            row_data = [
                product_data.get('status', ''), # A: 投稿ステータス
                product_data.get('original_work', ''), # B: 原作名
                product_data.get('character_name', ''), # C: キャラ名
                product_url_cell,                       # D: 商品URL (品番表記+リンク)
                product_data.get('title', ''), # E: FANZAの商品タイトル
                reserve_date_formatted,                 # F: 予約投稿日時 (MM/DD hh:mm)
                article_url_cell,                          # G: 記事URL (記事ID表記+リンク)
                last_processed_formatted,               # H: 最終処理日時 (MM/DD hh:mm)
                product_data.get('error_details', ''), # I: エラー詳細
            ]

            sheet_name = '商品管理'
            # 末尾に行を追加
            range_name = f'{sheet_name}!A:I' # 9カラム分
            
            print(f"Debug in add_product: Attempting to append row: {row_data}")

            try:
                # レート制限対策
                self._wait_for_rate_limit()
                
                self.service.spreadsheets().values().append(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name,
                    valueInputOption='USER_ENTERED',
                    body={
                        'values': [row_data]
                    }
                ).execute()
                
                # 商品追加後にキャッシュをクリア
                self.clear_product_cache()
                return True
            except Exception as e:
                self.monitor.log_error(f"商品の追加に失敗: {str(e)}")
                return False

        except Exception as e:
            self.monitor.log_error(f"商品の追加に失敗: {str(e)}")
            return False

    def add_products_batch(self, products_data: List[Dict[str, Any]]) -> bool:
        """
        商品管理シートに複数の商品を一括追加（重複商品の自動削除機能付き）
        
        Args:
            products_data: 商品データのリスト
            
        Returns:
            bool: 追加が成功したかどうか
        """
        try:
            if not products_data:
                return True
            
            # 【新機能】重複商品の自動削除
            print("🔍 重複商品の検出と削除を開始...")
            deleted_count = self._remove_duplicate_products(products_data)
            if deleted_count > 0:
                print(f"✅ {deleted_count}件の重複商品を削除しました")
            else:
                print("📋 削除対象の重複商品はありませんでした")
            
            # 商品データを行形式に変換
            rows_data = []
            for product_data in products_data:
                # 商品URLが商品IDのように見える場合、URLに変換して保存
                product_url = product_data.get('url', '')
                if product_url and not product_url.startswith("http"):
                    product_data['url'] = self._convert_product_id_to_url(product_url)
                
                # D列 (商品URL): 品番表記のハイパーリンク
                product_url = product_data.get('url', '')
                actual_product_url = ''
                product_id_for_link = ''
                
                if isinstance(product_url, str) and product_url.startswith('=HYPERLINK("'):
                    match = re.search(r'=HYPERLINK\("([^\"]+)\", \"([^\"]+)\"\)', product_url)
                    if match:
                        actual_product_url = match.group(1)
                        product_id_for_link = match.group(2)
                    else:
                        actual_product_url = product_url 
                else:
                    actual_product_url = product_url
                    product_id_from_data = product_data.get('品番')
                    if product_id_from_data:
                        product_id_for_link = product_id_from_data
                    elif actual_product_url:
                        product_id_for_link = self.extract_product_code(actual_product_url)
                
                escaped_actual_product_url = actual_product_url.replace('"', '""')
                escaped_product_id_for_link = product_id_for_link.replace('"', '""')
                product_url_cell = f'=HYPERLINK("{escaped_actual_product_url}", "{escaped_product_id_for_link}")' if escaped_actual_product_url and escaped_product_id_for_link else ''

                row_data = [
                    product_data.get('status', '未処理'),
                    product_data.get('original_work', ''),
                    product_data.get('character_name', ''),
                    product_url_cell,
                    product_data.get('title', ''),
                    product_data.get('reserve_date', ''),
                    product_data.get('post_url', ''),
                    product_data.get('last_processed', ''),
                    product_data.get('error_details', '')
                ]
                rows_data.append(row_data)
            
            print(f"Debug in add_products_batch: Attempting to append {len(rows_data)} rows")
            
            # レート制限対策
            self._wait_for_rate_limit()
            
            # スプレッドシートに行を一括追加
            body = {'values': rows_data}
            
            # HYPERLINK関数が含まれているかチェック
            value_input_option = 'USER_ENTERED' if any(
                any(isinstance(cell, str) and cell.startswith('=HYPERLINK(') for cell in row)
                for row in rows_data
            ) else 'RAW'
            
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.product_sheet}!A:I',
                valueInputOption=value_input_option,
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            print(f"Debug in add_products_batch: Successfully added {len(rows_data)} products")
            return True
            
        except Exception as e:
            self.monitor.log_error(f"商品の一括追加に失敗: {str(e)}")
            return False

    def _remove_duplicate_products(self, new_products_data: List[Dict[str, Any]]) -> int:
        """
        新商品追加前に既存の重複商品を削除（未処理商品のみ対象）
        
        Args:
            new_products_data: 追加予定の新商品データリスト
            
        Returns:
            int: 削除した商品数
        """
        try:
            # 新商品の品番リストを作成
            new_product_ids = set()
            for product_data in new_products_data:
                product_url = product_data.get('url', '')
                product_id = self.extract_product_code(product_url)
                if product_id:
                    new_product_ids.add(product_id)
            
            if not new_product_ids:
                return 0
            
            print(f"🔍 新商品の品番: {list(new_product_ids)}")
            
            # 既存の商品管理シートデータを取得
            values = self._get_sheet_values(self.product_sheet, 'A2:I1000', value_render_option='FORMULA')
            if not values:
                return 0
            
            # 削除対象外のステータス（処理済み商品は削除しない）
            protected_statuses = {
                '予約投稿', '投稿済み', '投稿完了', '公開済み', '処理済み', 
                '下書き保存', '下書き', 'draft', 'published', 'scheduled'
            }
            
            # 重複商品の行番号を特定（未処理のもののみ）
            rows_to_delete = []
            for idx, row in enumerate(values, start=2):
                if len(row) < 4:
                    continue
                
                # A列（ステータス）をチェック
                status = str(row[0]).strip() if row[0] else ''
                
                # 処理済み商品は削除対象から除外
                if status in protected_statuses:
                    continue
                
                # D列（商品URL）から品番を抽出
                product_url = row[3] if len(row) > 3 else ''
                existing_product_id = self.extract_product_code(str(product_url))
                
                if existing_product_id in new_product_ids:
                    rows_to_delete.append({
                        'row_index': idx,
                        'product_id': existing_product_id,
                        'status': status,
                        'url': product_url
                    })
            
            if not rows_to_delete:
                return 0
            
            print(f"🗑️  削除対象の重複商品（未処理のみ）: {len(rows_to_delete)}件")
            for item in rows_to_delete:
                print(f"   Row {item['row_index']}: {item['product_id']} (ステータス: '{item['status']}')")
            
            # 行を後ろから削除（インデックスのずれを防ぐため）
            rows_to_delete.sort(key=lambda x: x['row_index'], reverse=True)
            
            deleted_count = 0
            for item in rows_to_delete:
                try:
                    # レート制限対策
                    self._wait_for_rate_limit()
                    
                    # 行を削除
                    self.service.spreadsheets().batchUpdate(
                        spreadsheetId=self.spreadsheet_id,
                        body={
                            'requests': [{
                                'deleteDimension': {
                                    'range': {
                                        'sheetId': self._get_sheet_id(self.product_sheet),
                                        'dimension': 'ROWS',
                                        'startIndex': item['row_index'] - 1,  # 0ベースのインデックス
                                        'endIndex': item['row_index']
                                    }
                                }
                            }]
                        }
                    ).execute()
                    
                    print(f"✅ 削除完了: Row {item['row_index']} - {item['product_id']} (未処理)")
                    deleted_count += 1
                    
                except Exception as e:
                    print(f"❌ 削除失敗: Row {item['row_index']} - {item['product_id']}: {str(e)}")
            
            return deleted_count
            
        except Exception as e:
            print(f"❌ 重複商品削除処理中にエラー: {str(e)}")
            return 0
    
    def cleanup_duplicate_products(self) -> int:
        """
        商品管理シートから重複商品を一括削除（未処理のもののみ）
        新商品追加に依存しない独立した重複削除機能
        
        Returns:
            int: 削除した商品数
        """
        try:
            print("🔍 商品管理シートの重複商品検出を開始...")
            
            # 既存の商品管理シートデータを取得
            values = self._get_sheet_values(self.product_sheet, 'A2:I1000', value_render_option='FORMULA')
            if not values:
                print("📋 商品管理シートにデータがありません")
                return 0
            
            # 削除対象外のステータス（処理済み商品は削除しない）
            protected_statuses = {
                '予約投稿', '投稿済み', '投稿完了', '公開済み', '処理済み', 
                '下書き保存', '下書き', 'draft', 'published', 'scheduled'
            }
            
            # 品番ごとにグループ化して重複を検出
            product_groups = {}
            for idx, row in enumerate(values, start=2):
                if len(row) < 4:
                    continue
                
                # A列（ステータス）をチェック
                status = str(row[0]).strip() if row[0] else ''
                
                # D列（商品URL）から品番を抽出
                product_url = row[3] if len(row) > 3 else ''
                product_id = self.extract_product_code(str(product_url))
                
                if not product_id:
                    continue
                
                if product_id not in product_groups:
                    product_groups[product_id] = []
                
                product_groups[product_id].append({
                    'row_index': idx,
                    'product_id': product_id,
                    'status': status,
                    'url': product_url,
                    'protected': status in protected_statuses
                })
            
            # 重複商品の削除対象を特定
            rows_to_delete = []
            for product_id, group in product_groups.items():
                if len(group) <= 1:
                    continue  # 重複していない
                
                # 保護されたエントリがあるか確認
                protected_entries = [entry for entry in group if entry['protected']]
                unprotected_entries = [entry for entry in group if not entry['protected']]
                
                if protected_entries:
                    # 保護されたエントリがある場合、未処理のエントリのみ削除
                    rows_to_delete.extend(unprotected_entries)
                else:
                    # 保護されたエントリがない場合、最初のエントリ以外を削除
                    rows_to_delete.extend(group[1:])
            
            if not rows_to_delete:
                print("📋 削除対象の重複商品はありませんでした")
                return 0
            
            print(f"🗑️  重複商品削除対象: {len(rows_to_delete)}件")
            for item in rows_to_delete:
                print(f"   Row {item['row_index']}: {item['product_id']} (ステータス: '{item['status']}')")
            
            # 削除の確認（バッチ処理時はスキップ）
            if len(rows_to_delete) > 5:
                print(f"⚠️  {len(rows_to_delete)}件の削除を実行します。続行しますか？ (自動実行中のため続行)")
            
            # 行を後ろから削除（インデックスのずれを防ぐため）
            rows_to_delete.sort(key=lambda x: x['row_index'], reverse=True)
            
            deleted_count = 0
            for item in rows_to_delete:
                try:
                    # レート制限対策
                    self._wait_for_rate_limit()
                    
                    # 行を削除
                    self.service.spreadsheets().batchUpdate(
                        spreadsheetId=self.spreadsheet_id,
                        body={
                            'requests': [{
                                'deleteDimension': {
                                    'range': {
                                        'sheetId': self._get_sheet_id(self.product_sheet),
                                        'dimension': 'ROWS',
                                        'startIndex': item['row_index'] - 1,  # 0ベースのインデックス
                                        'endIndex': item['row_index']
                                    }
                                }
                            }]
                        }
                    ).execute()
                    
                    print(f"✅ 削除完了: Row {item['row_index']} - {item['product_id']}")
                    deleted_count += 1
                    
                except Exception as e:
                    print(f"❌ 削除失敗: Row {item['row_index']} - {item['product_id']}: {str(e)}")
            
            print(f"✅ 重複商品の削除が完了しました。削除件数: {deleted_count}件")
            return deleted_count
            
        except Exception as e:
            print(f"❌ 重複商品削除処理中にエラー: {str(e)}")
            return 0

    def _get_sheet_id(self, sheet_name: str) -> int:
        """
        シート名からシートIDを取得
        
        Args:
            sheet_name: シート名
            
        Returns:
            int: シートID
        """
        try:
            # レート制限対策
            self._wait_for_rate_limit()
            
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            for sheet in spreadsheet['sheets']:
                if sheet['properties']['title'] == sheet_name:
                    return sheet['properties']['sheetId']
            
            raise ValueError(f"シート '{sheet_name}' が見つかりません")
            
        except Exception as e:
            raise Exception(f"シートID取得に失敗: {str(e)}")

    def get_existing_product_codes(self) -> List[str]:
        """商品管理シートから既存の品番を読み込む"""
        try:
            sheet_name = '商品管理'
            # 商品URLカラム(D列)を取得
            url_values = self._get_sheet_values(sheet_name, 'D:D')
            # URLから品番を抽出
            existing_product_codes = [self.extract_product_code(str(row[0])) for row in url_values if row]
            # 空の品番を除外
            existing_product_codes = [code for code in existing_product_codes if code]
            print(f"Debug: 既存の品番リスト: {existing_product_codes}")
            return existing_product_codes
        except Exception as e:
            self.monitor.log_error(f"品番リストの取得に失敗: {str(e)}")
            return []

    def update_post_url_by_product_code(self, product_code: str, post_id: str, wp_domain: str):
        """品番で該当行を特定し、記事URLカラムにWordPress記事IDのハイパーリンクを記録"""
        values = self._get_sheet_values(self.product_sheet, 'D2:D1000')  # 商品URL列（品番ハイパーリンク）
        for idx, row in enumerate(values, start=2):
            if row and product_code in row[0]:
                post_url = f'https://{wp_domain}/?p={post_id}'
                post_cell = f'=HYPERLINK("{post_url}", "{post_id}")'
                # G列（記事URLカラム）に記録
                update_range = f'G{idx}'
                self._update_sheet_values(self.product_sheet, update_range, [[post_cell]])
                break 

    def get_product_urls_from_keywords(self) -> List[str]:
        """キーワード管理シートから処理フラグONのFANZA検索キーワードで商品URLリストを取得"""
        values = self._get_sheet_values(self.keyword_sheet, 'A1:D1000')
        urls = []
        for row in values[1:]:
            if len(row) >= 4 and row[0].lower() in ['true', 'on', '1', 'yes']:
                keyword = row[3]
                # ここでFANZA APIや検索URL生成ロジックを呼び出す想定
                # 例: https://www.dmm.co.jp/dc/doujin/-/list/=/keyword={keyword}/
                search_url = f'https://www.dmm.co.jp/dc/doujin/-/list/=/keyword={keyword}/'
                urls.append(search_url)
        return urls 

    def update_row(self, sheet_name: str, row_idx: int, row_data: List[str]) -> None:
        """
        指定された行のデータを更新する
        
        Args:
            sheet_name (str): シート名
            row_idx (int): 更新する行のインデックス（1始まり）
            row_data (List[str]): 更新するデータ
        """
        try:
            # G列（記事URL, row_data[6]）が=HYPERLINK(で始まっていなければ自動でリンク化
            if len(row_data) > 6 and row_data[6]:
                cell = row_data[6]
                if isinstance(cell, str) and not cell.startswith('=HYPERLINK('):
                    url = cell
                    # IDはURLの末尾の数字や/?p=ID、/archives/IDから推測
                    import re
                    post_id = ''
                    match = re.search(r'[?&]p=(\d+)', url)
                    if match:
                        post_id = match.group(1)
                    else:
                        match = re.search(r'/archives/(\d+)', url)
                        if match:
                            post_id = match.group(1)
                        else:
                            # 末尾の数字
                            match = re.search(r'(\d+)(?:/)?$', url)
                            if match:
                                post_id = match.group(1)
                    if url and post_id:
                        escaped_url = url.replace('"', '""')
                        escaped_id = post_id.replace('"', '""')
                        row_data[6] = f'=HYPERLINK("{escaped_url}", "{escaped_id}")'
            range_name = f"{sheet_name}!A{row_idx}:I{row_idx}"
            body = {
                "values": [row_data]
            }
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            print(f"Debug: Updated row {row_idx} in sheet {sheet_name}")
        except Exception as e:
            print(f"Error in update_row: {str(e)}") 

    def add_character_to_keywords(self, original_work: str, character_names: List[str]) -> bool:
        """
        キーワード管理シートに新しいキャラクター情報を追加
        """
        try:
            # キーワード管理シートからデータを取得
            values = self._get_sheet_values(self.keyword_sheet, 'A:C')
            if not values:
                print("キーワード管理シートにデータがありません。")
                return False

            # ヘッダー行をスキップ
            existing_characters = set()
            for row in values[1:]:
                if len(row) > 1:
                    existing_characters.add(row[1])  # 既存のキャラクター名

            # 新しいキャラクター情報を追加
            new_rows = []
            for char_name in character_names:
                if char_name not in existing_characters:
                    new_rows.append([True, original_work, char_name, char_name, '', ''])  # 新しい行データ
                    existing_characters.add(char_name)

            # 新しい行をシートに追加
            if new_rows:
                range_to_update = f'{self.keyword_sheet}!A{len(values) + 1}:F{len(values) + len(new_rows)}'
                body = {'values': new_rows}
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_to_update,
                    valueInputOption='USER_ENTERED',
                    body=body
                ).execute()
                print(f"{len(new_rows)}件の新しいキャラクター情報をキーワード管理シートに追加しました。")
                return True
            else:
                print("新しいキャラクター情報はありませんでした。")
                return False

        except Exception as e:
            self.monitor.log_error(f"キーワード管理シートへのキャラクター情報追加に失敗: {str(e)}")
            return False

    def format_product_sheet(self) -> bool:
        """
        商品管理シートの整形を行う（品番・投稿IDリンク化など）
        
        Returns:
            bool: 整形が成功したかどうか
        """
        try:
            print("商品管理シートの整形を開始します...")
            
            # 現在のデータを取得
            values = self._get_sheet_values(self.product_sheet, 'A:I')
            if not values or len(values) <= 1:
                print("商品管理シートにデータがありません。")
                return True
            
            # ヘッダー行をスキップして処理
            updated_rows = []
            for i, row in enumerate(values[1:], start=2):
                if len(row) < 4:
                    continue
                
                row_updated = False
                
                # D列（商品URL）の整形
                product_url = row[3] if len(row) > 3 else ''
                if product_url and not product_url.startswith('=HYPERLINK('):
                    # 品番を抽出
                    product_code = self.extract_product_code(product_url)
                    if product_code:
                        # HYPERLINKに変換
                        escaped_url = product_url.replace('"', '""')
                        escaped_code = product_code.replace('"', '""')
                        hyperlink_formula = f'=HYPERLINK("{escaped_url}", "{escaped_code}")'
                        row[3] = hyperlink_formula
                        row_updated = True

                # G列（記事URL）の整形
                article_url = row[6] if len(row) > 6 else ''
                if article_url and not article_url.startswith('=HYPERLINK('):
                    # 記事IDを抽出（/?p=ID または /archives/ID 形式）
                    import re
                    post_id = ''
                    match = re.search(r'[?&]p=(\d+)', article_url)
                    if match:
                        post_id = match.group(1)
                    else:
                        match = re.search(r'/archives/(\d+)', article_url)
                        if match:
                            post_id = match.group(1)
                        else:
                            # 末尾の数字
                            match = re.search(r'(\d+)(?:/)?$', article_url)
                            if match:
                                post_id = match.group(1)
                    if article_url and post_id:
                        escaped_url = article_url.replace('"', '""')
                        escaped_id = post_id.replace('"', '""')
                        row[6] = f'=HYPERLINK("{escaped_url}", "{escaped_id}")'
                        row_updated = True
                
                # 行が更新された場合のみupdated_rowsに追加
                if row_updated:
                    updated_rows.append((i, row))
            
            # 更新されたデータをシートに反映
            if updated_rows:
                for row_idx, row_data in updated_rows:
                    range_name = f'{self.product_sheet}!A{row_idx}:I{row_idx}'
                    self._update_sheet_values(self.product_sheet, f'A{row_idx}:I{row_idx}', [row_data])
                
                print(f"{len(updated_rows)}行の商品管理シートを整形しました。")
            else:
                print("整形が必要な行はありませんでした。")
            
            return True
            
        except Exception as e:
            self.monitor.log_error(f"商品管理シートの整形に失敗: {str(e)}")
            return False

    def get_last_scheduled_time(self) -> Optional[datetime]:
        """
        商品管理シートのF列（予約投稿日時）から最後の予約投稿時間を取得
        
        Returns:
            最後の予約投稿時間。データがない場合はNone
        """
        try:
            # F列（予約投稿日時）のデータを取得
            values = self._get_sheet_values(self.product_sheet, 'F:F')
            if not values or len(values) <= 1:
                print("Debug: 商品管理シートに予約投稿データがありません")
                return None
            
            scheduled_times = []
            for i, row in enumerate(values[1:], start=2):  # ヘッダーをスキップ
                if row and row[0]:  # F列にデータがある場合
                    time_str = str(row[0]).strip()
                    if time_str:
                        try:
                            # MM/DD HH:MM形式をパース
                            if '/' in time_str and ':' in time_str:
                                # 現在の年を使用してdatetimeオブジェクトを作成
                                current_year = datetime.now().year
                                # MM/DD HH:MM形式を解析
                                date_part, time_part = time_str.split(' ')
                                month, day = map(int, date_part.split('/'))
                                hour, minute = map(int, time_part.split(':'))
                                
                                scheduled_time = datetime(current_year, month, day, hour, minute)
                                scheduled_times.append(scheduled_time)
                                print(f"Debug: 予約投稿時間を解析: {time_str} -> {scheduled_time}")
                        except (ValueError, IndexError) as e:
                            print(f"Debug: 予約投稿時間の解析に失敗 (行{i}): {time_str} - {str(e)}")
                            continue
            
            if not scheduled_times:
                print("Debug: 有効な予約投稿時間が見つかりませんでした")
                return None
            
            # 最新の予約投稿時間を返す
            last_time = max(scheduled_times)
            print(f"Debug: 最後の予約投稿時間: {last_time}")
            return last_time
            
        except Exception as e:
            self.monitor.log_error(f"最後の予約投稿時間の取得に失敗: {str(e)}")
            return None