import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from ...config.config_manager import ConfigManager
from ...utils.error_logger import ErrorLogger
from ...utils.cache_manager import CacheManager

class WordPressPoster:
    """WordPress投稿クラス"""

    def __init__(
        self,
        config: Optional[ConfigManager] = None,
        cache: Optional[CacheManager] = None,
        logger: Optional[ErrorLogger] = None
    ):
        """
        初期化

        Args:
            config: 設定マネージャー（オプション）
            cache: キャッシュマネージャー（オプション）
            logger: エラーロガー（オプション）
        """
        self.config = config or ConfigManager()
        self.cache = cache or CacheManager(self.config)
        self.logger = logger or ErrorLogger()
        
        self.wp_url = self.config.get('WP_URL')
        self.wp_username = self.config.get('WP_USERNAME')
        self.wp_password = self.config.get('WP_APPLICATION_PASSWORD')
        self.retry_count = int(self.config.get('RETRY_COUNT', 3))
        self.retry_delay = int(self.config.get('RETRY_DELAY', 5))

    async def _make_request(
        self,
        endpoint: str,
        method: str,
        data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        WordPress APIリクエストを実行

        Args:
            endpoint: APIエンドポイント
            method: HTTPメソッド
            data: リクエストデータ
            retry_count: リトライ回数

        Returns:
            APIレスポンス
        """
        url = f"{self.wp_url}/wp-json/wp/v2/{endpoint}"
        auth = aiohttp.BasicAuth(self.wp_username, self.wp_password)
        
        try:
            async with aiohttp.ClientSession(auth=auth) as session:
                if method == 'GET':
                    async with session.get(url) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            raise Exception(f"HTTP error: {response.status}")
                elif method == 'POST':
                    async with session.post(url, json=data) as response:
                        if response.status in [200, 201]:
                            return await response.json()
                        else:
                            raise Exception(f"HTTP error: {response.status}")
                elif method == 'PUT':
                    async with session.put(url, json=data) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            raise Exception(f"HTTP error: {response.status}")

        except Exception as e:
            if retry_count < self.retry_count:
                await asyncio.sleep(self.retry_delay)
                return await self._make_request(endpoint, method, data, retry_count + 1)
            else:
                self.logger.log_error(
                    "WordPress APIリクエストに失敗しました",
                    error=e,
                    context={'endpoint': endpoint, 'method': method, 'data': data}
                )
                raise

    async def _ensure_category_exists(self, category_name: str) -> int:
        """
        カテゴリの存在確認と作成

        Args:
            category_name: カテゴリ名

        Returns:
            カテゴリID
        """
        # カテゴリの検索
        categories = await self._make_request('categories', 'GET')
        for category in categories:
            if category['name'] == category_name:
                return category['id']
        
        # カテゴリの作成
        data = {'name': category_name}
        response = await self._make_request('categories', 'POST', data)
        return response['id']

    async def _ensure_tag_exists(self, tag_name: str) -> int:
        """
        タグの存在確認と作成

        Args:
            tag_name: タグ名

        Returns:
            タグID
        """
        # タグの検索
        tags = await self._make_request('tags', 'GET')
        for tag in tags:
            if tag['name'] == tag_name:
                return tag['id']
        
        # タグの作成
        data = {'name': tag_name}
        response = await self._make_request('tags', 'POST', data)
        return response['id']

    async def _upload_image(self, image_url: str) -> Optional[int]:
        """
        画像をアップロード

        Args:
            image_url: 画像URL

        Returns:
            アップロードされた画像のID
        """
        try:
            # 画像のダウンロード
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        return None
                    image_data = await response.read()
            
            # 画像のアップロード
            auth = aiohttp.BasicAuth(self.wp_username, self.wp_password)
            url = f"{self.wp_url}/wp-json/wp/v2/media"
            
            async with aiohttp.ClientSession(auth=auth) as session:
                data = aiohttp.FormData()
                data.add_field('file',
                             image_data,
                             filename='image.jpg',
                             content_type='image/jpeg')
                
                async with session.post(url, data=data) as response:
                    if response.status in [200, 201]:
                        result = await response.json()
                        return result['id']
                    return None

        except Exception as e:
            self.logger.log_error(
                "画像のアップロードに失敗しました",
                error=e,
                context={'image_url': image_url}
            )
            return None

    async def post_article(
        self,
        article_data: Dict[str, Any],
        schedule_date: Optional[datetime] = None
    ) -> Optional[int]:
        """
        記事を投稿

        Args:
            article_data: 記事データ
            schedule_date: 予約投稿日時

        Returns:
            投稿された記事のID
        """
        try:
            # カテゴリの設定
            category_ids = []
            for category_name in article_data['categories']:
                category_id = await self._ensure_category_exists(category_name)
                category_ids.append(category_id)
            
            # タグの設定
            tag_ids = []
            for tag_name in article_data['tags']:
                tag_id = await self._ensure_tag_exists(tag_name)
                tag_ids.append(tag_id)
            
            # アイキャッチ画像の設定
            featured_media_id = None
            if article_data['metadata'].get('image_url'):
                featured_media_id = await self._upload_image(
                    article_data['metadata']['image_url']
                )
            
            # 投稿データの作成
            post_data = {
                'title': article_data['title'],
                'content': article_data['content'],
                'status': 'future' if schedule_date else 'publish',
                'categories': category_ids,
                'tags': tag_ids,
                'featured_media': featured_media_id
            }
            
            if schedule_date:
                post_data['date'] = schedule_date.isoformat()
            
            # 記事の投稿
            response = await self._make_request('posts', 'POST', post_data)
            return response['id']

        except Exception as e:
            self.logger.log_error(
                "記事の投稿に失敗しました",
                error=e,
                context={'article_data': article_data, 'schedule_date': schedule_date}
            )
            return None

    async def update_article_status(
        self,
        article_id: int,
        status: str
    ) -> bool:
        """
        記事のステータスを更新

        Args:
            article_id: 記事ID
            status: 新しいステータス

        Returns:
            更新の成功/失敗
        """
        try:
            data = {'status': status}
            await self._make_request(f'posts/{article_id}', 'PUT', data)
            return True
        except Exception as e:
            self.logger.log_error(
                "記事のステータス更新に失敗しました",
                error=e,
                context={'article_id': article_id, 'status': status}
            )
            return False 