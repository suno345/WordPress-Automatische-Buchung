import datetime
import time
import asyncio
import aiohttp
from typing import Dict, List, Optional, Tuple
from ..config.config_manager import ConfigManager
from ..utils.error_logger import ErrorLogger
from ..data_retriever.fanza_retriever import FANZA_Data_Retriever
from ..grok_analyzer.grok_analyzer import Grok_Analyzer
from ..wordpress.article_generator import WordPress_Article_Generator
from ..wordpress.wordpress_poster import WordPress_Poster

class Scheduler_Orchestrator:
    """記事のスケジュール投稿を管理するクラス"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.logger = ErrorLogger()
        self.data_retriever = FANZA_Data_Retriever()
        self.analyzer = Grok_Analyzer()
        self.article_generator = WordPress_Article_Generator()
        self.wordpress_poster = WordPress_Poster()
        
        # スケジューリング設定
        self.posting_hours = self.config.get('POSTING_HOURS', [9, 12, 15, 18, 21])
        self.posts_per_day = self.config.get('POSTS_PER_DAY', 3)
        self.min_interval = self.config.get('MIN_POST_INTERVAL', 1)
        self.max_retries = self.config.get('MAX_RETRIES', 3)
        self.retry_delay = self.config.get('RETRY_DELAY', 300)  # 5分
        self.max_parallel_tasks = self.config.get('MAX_PARALLEL_TASKS', 3)
    
    async def schedule_articles(self, product_ids: List[str]) -> None:
        """記事のスケジュール投稿を行う（非同期）
        
        Args:
            product_ids: 商品IDのリスト
        """
        try:
            # 投稿時間を計算
            posting_times = await self._calculate_posting_times(len(product_ids))
            
            # タスクの作成
            tasks = []
            for product_id, post_time in zip(product_ids, posting_times):
                task = self._process_single_article(product_id, post_time)
                tasks.append(task)
            
            # 並列処理の実行
            await asyncio.gather(*tasks)
            
        except Exception as e:
            self.logger.log_error(
                str(e),
                'Scheduler_Orchestrator',
                'schedule_articles',
                {'product_count': len(product_ids)}
            )
    
    async def _calculate_posting_times(self, article_count: int) -> List[datetime.datetime]:
        """最適な投稿時間を計算する（非同期）
        
        Args:
            article_count: 投稿する記事数
            
        Returns:
            投稿時間のリスト
        """
        posting_times = []
        current_time = datetime.datetime.now()
        
        # WordPressの予約投稿を取得
        scheduled_posts = await self._get_scheduled_posts()
        
        # 予約投稿がない場合
        if not scheduled_posts:
            # 現在時刻から1時間後を最初の投稿時間として設定
            first_post_time = current_time + datetime.timedelta(hours=1)
            posting_times.append(first_post_time)
            
            # 残りの記事の投稿時間を計算
            for i in range(1, article_count):
                next_post_time = posting_times[-1] + datetime.timedelta(hours=self.min_interval)
                posting_times.append(next_post_time)
            
            return posting_times
        
        # 予約投稿がある場合
        last_scheduled_time = max(scheduled_posts)
        next_post_time = last_scheduled_time + datetime.timedelta(hours=1)
        
        # 現在時刻より前の場合は、現在時刻から1時間後に設定
        if next_post_time < current_time:
            next_post_time = current_time + datetime.timedelta(hours=1)
        
        posting_times.append(next_post_time)
        
        # 残りの記事の投稿時間を計算
        for i in range(1, article_count):
            next_post_time = posting_times[-1] + datetime.timedelta(hours=self.min_interval)
            posting_times.append(next_post_time)
        
        return posting_times
    
    async def _get_scheduled_posts(self) -> List[datetime.datetime]:
        """WordPressの予約投稿を取得する（非同期）
        
        Returns:
            予約投稿時間のリスト
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.wordpress_poster.api_url}/posts",
                    headers=self.wordpress_poster.headers,
                    params={'status': 'future', 'per_page': 100}
                ) as response:
                    response.raise_for_status()
                    posts = await response.json()
            
            scheduled_posts = []
            for post in posts:
                if 'date' in post:
                    post_time = datetime.datetime.fromisoformat(post['date'].replace('Z', '+00:00'))
                    scheduled_posts.append(post_time)
            
            return scheduled_posts
            
        except Exception as e:
            self.logger.log_error(
                str(e),
                'Scheduler_Orchestrator',
                '_get_scheduled_posts',
                None
            )
            return []
    
    async def _process_single_article(self, product_id: str, post_time: datetime.datetime) -> None:
        """1つの記事を処理する（非同期）
        
        Args:
            product_id: 商品ID
            post_time: 投稿予定時間
        """
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                # 商品情報を取得
                product_info = await self.data_retriever.get_product_info(product_id)
                if not product_info:
                    raise Exception(f"Failed to retrieve product info for ID: {product_id}")
                
                # コンテンツを分析
                analysis_result = await self.analyzer.analyze_content(
                    product_info.get('description', '')
                )
                
                # 記事を生成
                article_data = await self.article_generator.generate_article(
                    product_info,
                    analysis_result
                )
                if not article_data:
                    raise Exception(f"Failed to generate article for product: {product_id}")
                
                # 記事を投稿（下書きとして）
                post_id = await self.wordpress_poster.post_article(article_data)
                if not post_id:
                    raise Exception(f"Failed to post article for product: {product_id}")
                
                # 投稿時間を設定
                await self._schedule_post(post_id, post_time)
                
                self.logger.log_info(
                    f"Successfully scheduled article for product {product_id}",
                    'Scheduler_Orchestrator',
                    '_process_single_article',
                    {
                        'product_id': product_id,
                        'post_id': post_id,
                        'scheduled_time': post_time.isoformat()
                    }
                )
                
                return
                
            except Exception as e:
                retry_count += 1
                if retry_count < self.max_retries:
                    self.logger.log_warning(
                        f"Retry {retry_count}/{self.max_retries} for product {product_id}: {str(e)}",
                        'Scheduler_Orchestrator',
                        '_process_single_article',
                        {'product_id': product_id, 'retry_count': retry_count}
                    )
                    await asyncio.sleep(self.retry_delay)
                else:
                    self.logger.log_error(
                        f"Failed to process article after {self.max_retries} retries: {str(e)}",
                        'Scheduler_Orchestrator',
                        '_process_single_article',
                        {'product_id': product_id}
                    )
    
    async def _schedule_post(self, post_id: int, post_time: datetime.datetime) -> None:
        """記事の投稿時間を設定する（非同期）
        
        Args:
            post_id: 記事のID
            post_time: 投稿予定時間
        """
        try:
            # 記事を予約投稿として設定
            await self.wordpress_poster.update_article_status(post_id, 'future')
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.wordpress_poster.api_url}/posts/{post_id}",
                    headers=self.wordpress_poster.headers,
                    json={'date': post_time.isoformat()}
                ) as response:
                    response.raise_for_status()
            
        except Exception as e:
            self.logger.log_error(
                str(e),
                'Scheduler_Orchestrator',
                '_schedule_post',
                {
                    'post_id': post_id,
                    'scheduled_time': post_time.isoformat()
                }
            ) 