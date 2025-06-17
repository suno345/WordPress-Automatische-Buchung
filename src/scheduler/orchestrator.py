import os
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
from ..utils.logger import setup_logger
from ..utils.cache_manager import CacheManager
from ..fanza.data_retriever import FANZA_Data_Retriever
from ..grok.analyzer import Grok_Analyzer
from ..wordpress.article_generator import WordPress_Article_Generator
from ..wordpress.poster import WordPress_Poster

class Scheduler_Orchestrator:
    """全体の処理フローを制御するクラス"""

    def __init__(self):
        """初期化処理"""
        load_dotenv()
        self.logger = setup_logger(__name__)
        self.cache_manager = CacheManager()
        
        # 各モジュールのインスタンス化
        self.fanza_retriever = FANZA_Data_Retriever()
        self.grok_analyzer = Grok_Analyzer()
        self.article_generator = WordPress_Article_Generator()
        self.wordpress_poster = WordPress_Poster()
        
        # 設定値
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        self.retry_delay = int(os.getenv('RETRY_DELAY', '60'))  # 秒
        self.posts_per_day = int(os.getenv('POSTS_PER_DAY', '24'))
        self.post_interval = int(os.getenv('POST_INTERVAL', '60'))  # 分

    async def schedule_articles(self, product_ids: List[str]) -> Dict[str, str]:
        """記事のスケジュール投稿を行う
        
        Args:
            product_ids: 処理対象の商品IDリスト
            
        Returns:
            処理結果の辞書（商品ID: ステータス）
        """
        results = {}
        
        # 投稿時間の計算
        post_times = self._calculate_post_times(len(product_ids))
        
        # 商品ごとの処理
        for product_id, post_time in zip(product_ids, post_times):
            try:
                # 商品情報の取得
                product_info = await self.fanza_retriever.get_product_info(product_id)
                if not product_info:
                    results[product_id] = 'ERROR: 商品情報取得失敗'
                    continue
                
                # 顔画像データの取得
                face_images = await self.grok_analyzer.get_anime_face_image_data(
                    product_info['sample_images']['sample_l'][0]
                )
                if not face_images:
                    results[product_id] = 'ERROR: 顔画像データ取得失敗'
                    continue
                
                # 原作・キャラクターの推測
                grok_result = await self.grok_analyzer.infer_origin_and_character(
                    face_images,
                    product_info['title'],
                    product_info.get('description', '')
                )
                
                # 記事コンテンツの生成
                article_data = self.article_generator.generate_article_content(
                    product_info,
                    grok_result
                )
                
                # 記事の投稿
                post_result = self.wordpress_poster.post_article(article_data)
                if not post_result:
                    results[product_id] = 'ERROR: 記事投稿失敗'
                    continue
                
                results[product_id] = 'SUCCESS'
                
            except Exception as e:
                self.logger.error(f"商品処理エラー (ID: {product_id}): {str(e)}")
                results[product_id] = f'ERROR: {str(e)}'
        
        return results

    def _calculate_post_times(self, num_posts: int) -> List[datetime]:
        """投稿時間を計算する
        
        Args:
            num_posts: 投稿数
            
        Returns:
            投稿時間のリスト
        """
        now = datetime.now()
        post_times = []
        
        # 1日分の投稿時間を計算
        for i in range(min(num_posts, self.posts_per_day)):
            post_time = now + timedelta(minutes=i * self.post_interval)
            post_times.append(post_time)
        
        return post_times

    async def process_keyword(self, keyword: str) -> Dict[str, str]:
        """キーワードに基づいて商品を処理する
        
        Args:
            keyword: 検索キーワード
            
        Returns:
            処理結果の辞書（商品ID: ステータス）
        """
        try:
            # キーワード検索
            products = await self.fanza_retriever.get_latest_products(
                hits=100,
                keyword=keyword,
                sort='rank'
            )
            
            if not products:
                return {'error': '商品が見つかりませんでした'}
            
            # 商品IDの抽出
            product_ids = [p['content_id'] for p in products]
            
            # 記事のスケジュール投稿
            return await self.schedule_articles(product_ids)
            
        except Exception as e:
            self.logger.error(f"キーワード処理エラー (キーワード: {keyword}): {str(e)}")
            return {'error': str(e)}

    async def retry_failed_products(self, failed_results: Dict[str, str]) -> Dict[str, str]:
        """失敗した商品の再処理を行う
        
        Args:
            failed_results: 失敗した商品の結果辞書
            
        Returns:
            再処理結果の辞書
        """
        retry_results = {}
        
        for product_id, status in failed_results.items():
            if not status.startswith('ERROR'):
                continue
            
            for attempt in range(self.max_retries):
                try:
                    # 再試行前の待機
                    await asyncio.sleep(self.retry_delay)
                    
                    # 商品情報の取得
                    product_info = await self.fanza_retriever.get_product_info(product_id)
                    if not product_info:
                        continue
                    
                    # 顔画像データの取得
                    face_images = await self.grok_analyzer.get_anime_face_image_data(
                        product_info['sample_images']['sample_l'][0]
                    )
                    if not face_images:
                        continue
                    
                    # 原作・キャラクターの推測
                    grok_result = await self.grok_analyzer.infer_origin_and_character(
                        face_images,
                        product_info['title'],
                        product_info.get('description', '')
                    )
                    
                    # 記事コンテンツの生成
                    article_data = self.article_generator.generate_article_content(
                        product_info,
                        grok_result
                    )
                    
                    # 記事の投稿
                    post_result = self.wordpress_poster.post_article(article_data)
                    if post_result:
                        retry_results[product_id] = 'SUCCESS'
                        break
                    
                except Exception as e:
                    self.logger.error(f"再試行エラー (ID: {product_id}, 試行: {attempt + 1}): {str(e)}")
            
            if product_id not in retry_results:
                retry_results[product_id] = f'ERROR: 最大再試行回数を超過'
        
        return retry_results 