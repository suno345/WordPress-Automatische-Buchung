"""
スケジューラーオーケストレーターモジュール
"""
import asyncio
from typing import List, Dict, Any
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

from src.wordpress.wordpress_article_generator import WordPressArticleGenerator
from src.wordpress.wordpress_poster import WordPress_Poster
from src.fanza.fanza_data_retriever import FANZA_Data_Retriever
from src.grok.grok_analyzer import Grok_Analyzer
from src.spreadsheet.spreadsheet_manager import SpreadsheetManager
from src.monitor.monitor import Monitor
from src.logger.error_logger import Error_Logger
from src.config.config_manager import Config_Manager
from src.utils.fanza_scraper import verify_image_urls, scrape_fanza_product_details

class Scheduler_Orchestrator:
    """スケジューラーオーケストレータークラス"""
    
    def __init__(self):
        """初期化"""
        load_dotenv()
        
        # 環境変数から設定を読み込み
        self.max_concurrent_tasks = int(os.getenv('MAX_CONCURRENT_TASKS', '5'))
        self.posts_per_day = int(os.getenv('POSTS_PER_DAY', '24'))
        self.retry_attempts = int(os.getenv('RETRY_ATTEMPTS', '3'))
        self.retry_delay = int(os.getenv('RETRY_DELAY', '300'))
        
        # コンポーネントの初期化
        self.fanza_retriever = FANZA_Data_Retriever()
        self.grok_analyzer = Grok_Analyzer()
        self.article_generator = WordPressArticleGenerator()
        self.wordpress_poster = WordPress_Poster()
        self.spreadsheet_manager = SpreadsheetManager()
        self.monitor = Monitor()
        self.error_logger = Error_Logger()
        self.config_manager = Config_Manager()
        
        # ロガーの設定
        self.article_generator.logger = self.error_logger
    
    async def run_daily_schedule(self):
        """日次スケジュールを実行"""
        try:
            self.monitor.log_debug("日次スケジュール実行開始")
            
            # 最新の商品情報を取得
            self.monitor.log_debug("最新の商品情報取得開始")
            products = await self.fanza_retriever.get_latest_products(hits=self.posts_per_day)
            
            if not products:
                self.monitor.log_warning("最新の商品情報が取得できませんでした")
                return
                
            self.monitor.log_debug(f"取得した商品数: {len(products)}")
            
            # 商品ごとに処理
            product_ids = [p['product_id'] for p in products]
            self.monitor.log_debug(f"処理対象の商品ID: {product_ids}")
            
            await self.schedule_articles(product_ids)
            
            self.monitor.log_debug("日次スケジュール実行完了")
            
        except Exception as e:
            self.error_logger.log_error("SCHEDULE_ERROR", f"日次スケジュール実行中にエラーが発生: {str(e)}")
            self.monitor.log_error(f"日次スケジュール実行中にエラーが発生: {str(e)}")
            raise
    
    async def run_keyword_schedule(self, keyword: str):
        """キーワードスケジュールを実行（新仕様：品番重複＆原作名・キャラ名一致判定）"""
        try:
            # キーワードで商品を検索
            products = await self.fanza_retriever.search_products(keyword)
            # キーワード管理シートから原作名・キャラ名を取得
            keywords = self.spreadsheet_manager.get_active_keywords()
            kw_row = next((k for k in keywords if k['keyword'] == keyword), None)
            if not kw_row:
                self.error_logger.log_error("SCHEDULE_ERROR", f"キーワード未登録: {keyword}")
                return
            original_work = kw_row.get('original_work', '')
            character_name = kw_row.get('character_name', '')
            for product in products:
                # 品番抽出
                product_code = self.spreadsheet_manager.extract_product_code(product.get('URL', ''))
                # 原作名・キャラ名一致判定
                grok_result = await self.grok_analyzer.analyze_product(product)
                if not self.spreadsheet_manager.is_product_match(grok_result, original_work, character_name):
                    continue
                # 重複チェック（品番）
                if self.spreadsheet_manager.check_product_code_exists(product_code):
                    continue
                # 投稿・シート追記のエラーハンドリング
                try:
                    # 記事生成
                    product_info = await scrape_fanza_product_details(product.get('URL', ''))
                    product_info['url'] = product.get('URL', '')
                    product_info['title'] = product.get('title', '')
                    product_info['product_id'] = product.get('product_id', '')
                    # Grokによる分析
                    grok_result = await self.grok_analyzer.analyze_product(product_info)
                    if not self.spreadsheet_manager.is_product_match(grok_result, original_work, character_name):
                        continue
                    # 重複チェック（品番）
                    if self.spreadsheet_manager.check_product_code_exists(product_code):
                        continue
                    # 記事コンテンツの生成
                    article_data = self.article_generator.generate_article_content(
                        product_info, grok_result
                    )
                    # WordPressへの投稿
                    post_result = await self.wordpress_poster.post_article(article_data)
                    # シート追記
                    if post_result:
                        self.spreadsheet_manager.add_product({
                            'url': product.get('URL', ''),
                            'title': product.get('title', ''),
                            'character_name': grok_result.get('character_name', ''),
                            'original_work': grok_result.get('original_work', ''),
                            'status': '投稿完了',
                            'post_url': post_result['post_url'],
                            'reserve_date': datetime.now().isoformat(),
                            'error_details': '',
                        })
                        # 投稿ID・URLをハイパーリンクで記録
                        post_id = str(post_result.get('post_id', ''))
                        wp_domain = os.getenv('WP_DOMAIN', 'YOUR_WP_DOMAIN')
                        if product_code and post_id:
                            self.spreadsheet_manager.update_post_url_by_product_code(product_code, post_id, wp_domain)
                except Exception as e:
                    # エラー詳細を商品管理シートに記録
                    self.spreadsheet_manager.update_product_error(product.get('URL', ''), str(e))
                    self.error_logger.log_error("POST_ERROR", f"投稿・シート追記エラー: {str(e)}")
            # キーワードのステータスを更新
            self.spreadsheet_manager.update_keyword_status(keyword, '完了')
        except Exception as e:
            self.error_logger.log_error("SCHEDULE_ERROR", f"キーワードスケジュール実行中にエラーが発生: {str(e)}")
            self.spreadsheet_manager.update_keyword_status(keyword, 'エラー')
            raise
    
    async def schedule_articles(self, product_ids: List[str]):
        """記事のスケジュール投稿を実行"""
        try:
            # 並列処理の制御
            semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
            
            # タスクの作成
            tasks = []
            for product_id in product_ids:
                task = asyncio.create_task(
                    self._process_with_semaphore(semaphore, product_id)
                )
                tasks.append(task)
            
            # タスクの実行
            await asyncio.gather(*tasks)
            
        except Exception as e:
            self.error_logger.log_error("SCHEDULE_ERROR", f"記事スケジュール実行中にエラーが発生: {str(e)}")
            raise
    
    async def _process_with_semaphore(self, semaphore: asyncio.Semaphore, product_id: str):
        """セマフォを使用して処理を実行"""
        async with semaphore:
            return await self._process_single_product(product_id)
    
    async def _process_single_product(self, product_id: str) -> bool:
        """単一商品の処理を実行（Webスクレイピングのみで商品情報取得）"""
        try:
            print(f"[DEBUG] 商品ID: {product_id} 商品情報取得（Webスクレイピング）開始")
            # 商品URLを生成
            product_url = f"https://www.dmm.co.jp/dc/doujin/-/detail/=/cid={product_id}/"
            
            # Webスクレイピングで商品情報取得
            product_info = await scrape_fanza_product_details(product_url)
            
            # 画像URLの検証
            valid_images = await verify_image_urls(product_info['sample_images'])
            if not valid_images:
                print(f"[WARNING] 商品ID: {product_id} 有効な画像が見つかりません")
                return False
                
            product_info['url'] = product_url
            product_info['title'] = product_info.get('title', product_id)
            product_info['product_id'] = product_id
            product_info['sample_images'] = valid_images
            
            print(f"[DEBUG] 商品ID: {product_id} 商品情報取得（Webスクレイピング）完了")
            
            # 重複チェック
            if self.spreadsheet_manager.check_product_exists(product_url):
                print(f"[DEBUG] 商品ID: {product_id} 既に登録済みのためスキップ")
                return True
                
            # Grokによる分析
            print(f"[DEBUG] 商品ID: {product_id} Grok分析開始")
            grok_result = await self.grok_analyzer.analyze_product(product_info)
            print(f"[DEBUG] 商品ID: {product_id} Grok分析完了")
            
            # 記事コンテンツの生成
            print(f"[DEBUG] 商品ID: {product_id} 記事生成開始")
            article_data = self.article_generator.generate_article_content(
                product_info, grok_result
            )
            print(f"[DEBUG] 商品ID: {product_id} 記事生成完了")
            
            # WordPressへの投稿
            print(f"[DEBUG] 商品ID: {product_id} WordPress投稿開始")
            post_result = await self.wordpress_poster.post_article(article_data)
            print(f"[DEBUG] 商品ID: {product_id} WordPress投稿完了: {post_result}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 商品ID: {product_id} 処理中にエラーが発生: {str(e)}")
            return False
    
    async def update_products_by_keywords(self):
        """
        キーワード管理シートのキーワードごとにFANZA APIで人気順30件の商品を取得し、
        商品管理シートに重複チェックしつつ追加する。
        さらに、説明文・キャッチコピーもスクレイピングで取得して記入する。
        サンプル画像URLもmain_image（1枚目）とgallery_images（2枚目以降,カンマ区切り）で記録する。
        取得できる限り多くの情報を商品管理シートのカラムに自動マッピングする。
        API取得・スクレイピングにリトライとエラーハンドリングを追加し、失敗時はエラーログと商品管理シートのエラー詳細カラムに記録する。
        """
        keywords = self.spreadsheet_manager.get_active_keywords()
        for kw in keywords:
            try:
                product_list = await self.fanza_retriever.search_products(kw['keyword'], limit=30)
            except Exception as e:
                self.error_logger.log_error("API_ERROR", f"API取得失敗: {kw['keyword']} ({e})")
                continue
            for product in product_list:
                url = product.get('URL')
                if not url:
                    continue
                if not self.spreadsheet_manager.check_product_exists(url):
                    # スクレイピングで説明文・キャッチコピー取得（リトライ付き）
                    details = {'description': '', 'catch_copy': ''}
                    error_msg = ''
                    for attempt in range(3):
                        try:
                            details = await scrape_fanza_product_details(url)
                            break
                        except Exception as e:
                            error_msg = f"スクレイピング失敗({attempt+1}/3): {url} ({e})"
                            self.error_logger.log_error("SCRAPING_ERROR", error_msg)
                            await asyncio.sleep(2)
                    # サンプル画像URLリスト抽出
                    images = []
                    if 'sampleImageURL' in product and 'sample_l' in product['sampleImageURL']:
                        images = product['sampleImageURL']['sample_l']
                    elif 'sample_images' in product:
                        images = product['sample_images']
                    main_image = images[0] if images else ''
                    gallery_images = ','.join(images[1:]) if len(images) > 1 else ''
                    # できるだけ多くの情報をマッピング
                    product_data = {
                        'url': url,
                        'title': product.get('title', ''),
                        'character_name': product.get('iteminfo', {}).get('character', [''])[0] if 'iteminfo' in product and 'character' in product['iteminfo'] else '',
                        'original_work': product.get('iteminfo', {}).get('original', [''])[0] if 'iteminfo' in product and 'original' in product['iteminfo'] else '',
                        'circle_name': product.get('maker', [''])[0] if isinstance(product.get('maker'), list) else product.get('maker', ''),
                        'genre': ','.join([g['name'] for g in product.get('iteminfo', {}).get('genre', [])]) if 'iteminfo' in product and 'genre' in product['iteminfo'] else '',
                        'price': product.get('prices', {}).get('price', ''),
                        'release_date': product.get('date', ''),
                        'review_count': product.get('review', {}).get('count', ''),
                        'review_average': product.get('review', {}).get('average', ''),
                        'description': details.get('description', ''),
                        'catch_copy': details.get('catch_copy', ''),
                        'main_image': main_image,
                        'gallery_images': gallery_images,
                        # 必要に応じて他のカラムも追加
                    }
                    self.spreadsheet_manager.add_product(product_data)
                    # エラーがあれば商品管理シートにも記録
                    if error_msg:
                        self.spreadsheet_manager.update_product_error(url, error_msg) 