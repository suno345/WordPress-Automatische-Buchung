"""
VPS向けシンプルスケジューラーオーケストレーター
予約投稿システムを削除し、即時投稿用に最適化
"""
import asyncio
from typing import List, Dict, Any
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

from src.core.wordpress.article_generator import WordPressArticleGenerator
from src.core.wordpress.poster import WordPressPoster as WordPress_Poster
from src.core.fanza.data_retriever import FANZA_Data_Retriever
from src.core.hybrid_analyzer import Hybrid_Analyzer as Grok_Analyzer
from src.core.spreadsheet.manager import SpreadsheetManager
from src.utils.logger import Logger as Monitor
from src.utils.error_logger import Error_Logger
from src.utils.fanza_scraper import verify_image_urls, scrape_fanza_product_details

class VPS_Simple_Orchestrator:
    """VPS向けシンプルオーケストレータークラス（即時投稿）"""
    
    def __init__(self):
        """初期化"""
        load_dotenv()
        
        # VPS向け設定値（軽量化）
        self.max_concurrent_tasks = int(os.getenv('VPS_MAX_CONCURRENT_TASKS', '2'))
        self.posts_per_run = int(os.getenv('VPS_POSTS_PER_RUN', '5'))
        self.retry_attempts = int(os.getenv('RETRY_ATTEMPTS', '2'))
        
        # コンポーネントの初期化
        self.fanza_retriever = FANZA_Data_Retriever()
        self.grok_analyzer = Grok_Analyzer()
        self.article_generator = WordPressArticleGenerator()
        self.wordpress_poster = WordPress_Poster()
        self.spreadsheet_manager = SpreadsheetManager()
        self.monitor = Monitor()
        self.error_logger = Error_Logger()
        
        # ロガーの設定
        self.article_generator.logger = self.error_logger
    
    async def run_simple_posting(self, max_posts: int = None):
        """シンプル投稿実行（VPS向け）"""
        try:
            max_posts = max_posts or self.posts_per_run
            self.monitor.log_debug(f"VPS簡易投稿開始 - 最大投稿数: {max_posts}")
            
            # 最新の商品情報を取得（軽量化）
            products = await self.fanza_retriever.get_latest_products(hits=max_posts * 2)
            
            if not products:
                self.monitor.log_warning("商品情報が取得できませんでした")
                return
                
            # 重複除外
            valid_products = []
            for product in products:
                product_url = product.get('URL', '')
                if product_url and not self.spreadsheet_manager.check_product_exists(product_url):
                    valid_products.append(product)
                    if len(valid_products) >= max_posts:
                        break
            
            self.monitor.log_debug(f"投稿対象商品数: {len(valid_products)}")
            
            # 即時投稿処理
            success_count = 0
            for product in valid_products:
                try:
                    result = await self._process_single_product_simple(product)
                    if result:
                        success_count += 1
                        self.monitor.log_debug(f"投稿成功: {product.get('title', 'Unknown')}")
                    else:
                        self.monitor.log_warning(f"投稿失敗: {product.get('title', 'Unknown')}")
                except Exception as e:
                    self.error_logger.log_error("PRODUCT_ERROR", f"商品処理エラー: {str(e)}")
            
            self.monitor.log_debug(f"VPS簡易投稿完了 - 成功: {success_count}/{len(valid_products)}")
            
        except Exception as e:
            self.error_logger.log_error("VPS_ERROR", f"VPS簡易投稿エラー: {str(e)}")
            raise
    
    async def run_scheduled_posting(self, posts_per_batch: int = 1):
        """24時間予約投稿システム（30分間隔、スプレッドシートキーワード使用）"""
        try:
            self.monitor.log_debug(f"VPS予約投稿開始 - バッチサイズ: {posts_per_batch}")
            
            # スプレッドシートから処理対象キーワードを取得
            active_keywords = self.spreadsheet_manager.get_active_keywords()
            
            if not active_keywords:
                self.monitor.log_warning("処理対象のキーワードがありません")
                return 0
            
            self.monitor.log_debug(f"処理対象キーワード数: {len(active_keywords)}")
            
            # 重複除外と次回予約投稿時間の計算
            last_scheduled_time = self.spreadsheet_manager.get_last_scheduled_time()
            if last_scheduled_time:
                next_scheduled_time = last_scheduled_time + timedelta(minutes=30)
            else:
                # 初回実行時は現在時刻から30分後
                next_scheduled_time = datetime.now() + timedelta(minutes=30)
            
            # キーワードから商品を検索・選定
            valid_products = []
            for keyword_info in active_keywords:
                if len(valid_products) >= posts_per_batch:
                    break
                    
                keyword = keyword_info.get('keyword', '')
                original_work = keyword_info.get('original_work', '')
                character_name = keyword_info.get('character_name', '')
                
                if not keyword:
                    continue
                
                try:
                    # キーワードで商品検索
                    products = await self.fanza_retriever.search_products(keyword, limit=5)
                    
                    for product in products:
                        if len(valid_products) >= posts_per_batch:
                            break
                            
                        product_url = product.get('URL', '')
                        if (product_url and 
                            not self.spreadsheet_manager.check_product_exists(product_url)):
                            # キーワード情報を商品に付加
                            product['sheet_original_work'] = original_work
                            product['sheet_character_name'] = character_name
                            product['source_keyword'] = keyword
                            valid_products.append(product)
                            
                except Exception as e:
                    self.monitor.log_warning(f"キーワード検索失敗: {keyword} - {str(e)}")
                    continue
            
            if not valid_products:
                self.monitor.log_warning("投稿対象の新規商品がありません")
                return 0
            
            self.monitor.log_debug(f"予約投稿対象商品数: {len(valid_products)}")
            self.monitor.log_debug(f"次回予約投稿時間: {next_scheduled_time.strftime('%m/%d %H:%M')}")
            
            # 予約投稿処理
            success_count = 0
            for i, product in enumerate(valid_products):
                try:
                    # 各商品の予約投稿時間を30分ずつずらす
                    post_scheduled_time = next_scheduled_time + timedelta(minutes=30 * i)
                    
                    result = await self._process_single_product_scheduled_with_keywords(product, post_scheduled_time)
                    if result:
                        success_count += 1
                        self.monitor.log_debug(f"予約投稿設定完了: {product.get('title', 'Unknown')} at {post_scheduled_time.strftime('%m/%d %H:%M')}")
                    else:
                        self.monitor.log_warning(f"予約投稿設定失敗: {product.get('title', 'Unknown')}")
                        
                except Exception as e:
                    self.error_logger.log_error("SCHEDULED_PRODUCT_ERROR", f"予約投稿商品処理エラー: {str(e)}")
            
            self.monitor.log_debug(f"VPS予約投稿完了 - 成功: {success_count}/{len(valid_products)}")
            return success_count
            
        except Exception as e:
            self.error_logger.log_error("VPS_SCHEDULED_ERROR", f"VPS予約投稿エラー: {str(e)}")
            raise
    
    async def run_keyword_posting(self, keyword: str, max_posts: int = 3):
        """キーワード指定投稿（VPS向け軽量版）"""
        try:
            self.monitor.log_debug(f"キーワード投稿開始: {keyword}")
            
            # キーワード検索
            products = await self.fanza_retriever.search_products(keyword, limit=max_posts * 2)
            
            # キーワード管理シートから設定取得
            keywords = self.spreadsheet_manager.get_active_keywords()
            kw_row = next((k for k in keywords if k['keyword'] == keyword), None)
            
            if not kw_row:
                self.error_logger.log_error("KEYWORD_ERROR", f"キーワード未registered: {keyword}")
                return
            
            original_work = kw_row.get('original_work', '')
            character_name = kw_row.get('character_name', '')
            
            success_count = 0
            for product in products[:max_posts]:
                try:
                    # 重複チェック
                    product_url = product.get('URL', '')
                    if self.spreadsheet_manager.check_product_exists(product_url):
                        continue
                    
                    # 即時投稿処理
                    result = await self._process_single_product_with_filter(
                        product, original_work, character_name
                    )
                    if result:
                        success_count += 1
                
                except Exception as e:
                    self.error_logger.log_error("KEYWORD_PRODUCT_ERROR", f"キーワード商品処理エラー: {str(e)}")
            
            # キーワードステータス更新
            self.spreadsheet_manager.update_keyword_status(keyword, '完了')
            self.monitor.log_debug(f"キーワード投稿完了: {keyword} - 成功: {success_count}")
            
        except Exception as e:
            self.error_logger.log_error("KEYWORD_ERROR", f"キーワード投稿エラー: {str(e)}")
            self.spreadsheet_manager.update_keyword_status(keyword, 'エラー')
    
    async def _process_single_product_simple(self, product: Dict[str, Any]) -> bool:
        """単一商品の簡易処理（即時投稿）"""
        try:
            product_url = product.get('URL', '')
            product_id = product.get('product_id', '')
            
            # 商品情報取得
            product_info = await scrape_fanza_product_details(product_url)
            product_info['url'] = product_url
            product_info['title'] = product.get('title', '')
            product_info['product_id'] = product_id
            
            # 画像検証
            valid_images = await verify_image_urls(product_info.get('sample_images', []))
            if not valid_images:
                self.monitor.log_warning(f"有効な画像なし: {product_id}")
                return False
            
            product_info['sample_images'] = valid_images
            
            # Grok分析（エラー時はスキップ）
            grok_result = {}
            try:
                grok_result = await self.grok_analyzer.analyze_product(product_info)
                
                # キャラ名取得チェック
                if not grok_result.get('character_name') or grok_result.get('character_name').strip() == '':
                    self.monitor.log_warning(f"キャラ名未取得のため下書き保存: {product_id}")
                    # 下書きとして保存
                    article_data = self.article_generator.generate_article_content(
                        product_info, {'character_name': '未取得', 'original_work': ''}
                    )
                    await self._save_as_draft(article_data, product_info, "キャラ名未取得")
                    return False
                    
            except Exception as e:
                self.monitor.log_warning(f"Grok分析失敗（下書き保存）: {str(e)}")
                # 下書きとして保存
                article_data = self.article_generator.generate_article_content(
                    product_info, {'character_name': '分析失敗', 'original_work': ''}
                )
                await self._save_as_draft(article_data, product_info, f"Grok分析失敗: {str(e)}")
                return False
            
            # 記事生成
            article_data = self.article_generator.generate_article_content(
                product_info, grok_result
            )
            
            # WordPress即時投稿
            post_result = await self.wordpress_poster.post_article(article_data)
            
            if post_result:
                # スプレッドシート更新
                self.spreadsheet_manager.add_product({
                    'url': product_url,
                    'title': product.get('title', ''),
                    'character_name': grok_result.get('character_name', ''),
                    'original_work': grok_result.get('original_work', ''),
                    'status': '投稿完了',
                    'post_url': str(post_result.get('post_id', '')),
                    'reserve_date': datetime.now().isoformat(),
                    'error_details': '',
                })
                return True
            
            return False
            
        except Exception as e:
            self.error_logger.log_error("PRODUCT_ERROR", f"商品処理エラー: {str(e)}")
            return False
    
    async def _process_single_product_with_filter(self, product: Dict[str, Any], 
                                                original_work: str, character_name: str) -> bool:
        """フィルター付き商品処理"""
        try:
            # 基本処理は同じ
            result = await self._process_single_product_simple(product)
            
            # フィルター機能は簡略化（VPS向け）
            # 必要に応じて後で詳細フィルターを追加
            
            return result
            
        except Exception as e:
            self.error_logger.log_error("FILTER_ERROR", f"フィルター処理エラー: {str(e)}")
            return False
    
    async def _process_single_product_scheduled(self, product: Dict[str, Any], scheduled_time: datetime) -> bool:
        """単一商品の予約投稿処理"""
        try:
            product_url = product.get('URL', '')
            product_id = product.get('product_id', '')
            
            # 商品情報取得
            product_info = await scrape_fanza_product_details(product_url)
            product_info['url'] = product_url
            product_info['title'] = product.get('title', '')
            product_info['product_id'] = product_id
            
            # 画像検証
            valid_images = await verify_image_urls(product_info.get('sample_images', []))
            if not valid_images:
                self.monitor.log_warning(f"有効な画像なし: {product_id}")
                # 画像なしでも記事作成を試行
                product_info['sample_images'] = []
            else:
                product_info['sample_images'] = valid_images
            
            # Grok分析（エラー時はスキップ）
            grok_result = {}
            try:
                grok_result = await self.grok_analyzer.analyze_product(product_info)
                
                # キャラ名取得チェック
                if not grok_result.get('character_name') or grok_result.get('character_name').strip() == '':
                    self.monitor.log_warning(f"キャラ名未取得のため下書き保存: {product_id}")
                    # 下書きとして保存
                    article_data = self.article_generator.generate_article_content(
                        product_info, {'character_name': '未取得', 'original_work': ''}
                    )
                    await self._save_as_draft(article_data, product_info, "キャラ名未取得")
                    return False
                    
            except Exception as e:
                self.monitor.log_warning(f"Grok分析失敗（下書き保存）: {str(e)}")
                # 下書きとして保存
                article_data = self.article_generator.generate_article_content(
                    product_info, {'character_name': '分析失敗', 'original_work': ''}
                )
                await self._save_as_draft(article_data, product_info, f"Grok分析失敗: {str(e)}")
                return False
            
            # 記事生成
            article_data = self.article_generator.generate_article_content(
                product_info, grok_result
            )
            
            # WordPress予約投稿（将来の時刻で投稿設定）
            article_data['scheduled_date'] = scheduled_time.isoformat()
            post_result = await self.wordpress_poster.post_scheduled_article(article_data)
            
            if post_result:
                # スプレッドシートに予約投稿として記録
                self.spreadsheet_manager.add_product({
                    'url': product_url,
                    'title': product.get('title', ''),
                    'character_name': grok_result.get('character_name', ''),
                    'original_work': grok_result.get('original_work', ''),
                    'status': '予約投稿',
                    'post_url': str(post_result.get('post_id', '')),
                    'reserve_date': scheduled_time.strftime('%m/%d %H:%M'),
                    'error_details': '',
                })
                return True
            
            return False
            
        except Exception as e:
            self.error_logger.log_error("SCHEDULED_PRODUCT_ERROR", f"予約投稿商品処理エラー: {str(e)}")
            return False
    
    async def _process_single_product_scheduled_with_keywords(self, product: Dict[str, Any], scheduled_time: datetime) -> bool:
        """キーワード情報付き商品の予約投稿処理"""
        try:
            product_url = product.get('URL', '')
            product_id = product.get('product_id', '')
            
            # スプレッドシートから取得したキーワード情報
            original_work = product.get('sheet_original_work', '')
            character_name = product.get('sheet_character_name', '')
            source_keyword = product.get('source_keyword', '')
            
            # 商品情報取得（キーワード情報付き）
            from src.utils.fanza_scraper import scrape_fanza_product_details
            product_info = await scrape_fanza_product_details(
                product_url, 
                sheet_original_work=original_work,
                sheet_character=character_name
            )
            product_info['url'] = product_url
            product_info['title'] = product.get('title', '')
            product_info['product_id'] = product_id
            
            # 画像検証
            valid_images = await verify_image_urls(product_info.get('sample_images', []))
            if not valid_images:
                self.monitor.log_warning(f"有効な画像なし: {product_id}")
                # 画像なしでも記事作成を試行
                product_info['sample_images'] = []
            else:
                product_info['sample_images'] = valid_images
            
            # Grok分析（スプレッドシート情報を優先使用）
            grok_result = {
                'character_name': character_name,
                'original_work': original_work
            }
            
            try:
                # AIによる追加分析も実行
                ai_result = await self.grok_analyzer.analyze_product(product_info)
                
                # スプレッドシート情報が空の場合のみAI結果を使用
                if not character_name and ai_result.get('character_name'):
                    grok_result['character_name'] = ai_result.get('character_name')
                if not original_work and ai_result.get('original_work'):
                    grok_result['original_work'] = ai_result.get('original_work')
                    
            except Exception as e:
                self.monitor.log_warning(f"Grok分析失敗（スプレッドシート情報を使用）: {str(e)}")
            
            # キャラ名チェック
            if not grok_result.get('character_name') or grok_result.get('character_name').strip() == '':
                self.monitor.log_warning(f"キャラ名未取得のため下書き保存: {product_id}")
                article_data = self.article_generator.generate_article_content(
                    product_info, {'character_name': '未取得', 'original_work': original_work}
                )
                await self._save_as_draft(article_data, product_info, f"キャラ名未取得 (キーワード: {source_keyword})")
                return False
            
            # 記事生成
            article_data = self.article_generator.generate_article_content(
                product_info, grok_result
            )
            
            # WordPress予約投稿（将来の時刻で投稿設定）
            article_data['scheduled_date'] = scheduled_time.isoformat()
            post_result = await self.wordpress_poster.post_scheduled_article(article_data)
            
            if post_result:
                # スプレッドシートに予約投稿として記録
                self.spreadsheet_manager.add_product({
                    'url': product_url,
                    'title': product.get('title', ''),
                    'character_name': grok_result.get('character_name', ''),
                    'original_work': grok_result.get('original_work', ''),
                    'status': '予約投稿',
                    'post_url': str(post_result.get('post_id', '')),
                    'reserve_date': scheduled_time.strftime('%m/%d %H:%M'),
                    'error_details': f'キーワード: {source_keyword}',
                })
                return True
            
            return False
            
        except Exception as e:
            self.error_logger.log_error("SCHEDULED_KEYWORD_PRODUCT_ERROR", f"キーワード予約投稿商品処理エラー: {str(e)}")
            return False

    async def _save_as_draft(self, article_data: Dict[str, Any], product_info: Dict[str, Any], reason: str):
        """下書きとして保存"""
        try:
            # WordPressに下書きとして投稿
            draft_data = article_data.copy()
            draft_data['title'] = f"[下書き] {draft_data.get('title', '')}"
            draft_data['status'] = 'draft'  # 下書きステータス
            
            # WordPress投稿（下書き）
            post_result = await self.wordpress_poster.post_draft(draft_data)
            
            if post_result:
                # スプレッドシートに下書きとして記録
                self.spreadsheet_manager.add_product({
                    'url': product_info.get('url', ''),
                    'title': product_info.get('title', ''),
                    'character_name': '下書き',
                    'original_work': '下書き',
                    'status': '下書き保存',
                    'post_url': str(post_result.get('post_id', '')),
                    'reserve_date': datetime.now().isoformat(),
                    'error_details': reason,
                })
                
                self.monitor.log_debug(f"下書き保存完了: {product_info.get('title', '')} (理由: {reason})")
                return True
            
            return False
            
        except Exception as e:
            self.error_logger.log_error("DRAFT_ERROR", f"下書き保存エラー: {str(e)}")
            return False