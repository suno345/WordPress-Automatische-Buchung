import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from ...config.config_manager import ConfigManager
from ...utils.cache_manager import CacheManager
from ...utils.error_logger import ErrorLogger

class FanzaApiClient:
    """FANZA APIクライアント"""

    BASE_URL = "https://api.dmm.com/affiliate/v3"
    
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
        
        self.api_key = self.config.get('FANZA_API_KEY')
        self.affiliate_id = self.config.get('FANZA_AFFILIATE_ID')
        self.rate_limit = int(self.config.get('API_RATE_LIMIT', 1))  # 1秒あたり1リクエスト
        self.retry_count = 1  # デバッグ用に最小リトライ
        self.retry_delay = 1  # デバッグ用に最小遅延

    async def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Any],
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        APIリクエストを実行

        Args:
            endpoint: APIエンドポイント
            params: リクエストパラメータ
            retry_count: リトライ回数

        Returns:
            APIレスポンス
        """
        url = f"{self.BASE_URL}/{endpoint}"
        
        # 共通パラメータの設定
        params.update({
            'api_id': self.api_key,
            'affiliate_id': self.affiliate_id,
            'site': 'FANZA',
            'service': 'digital',
            'hits': 100,  # 最大取得件数
            'offset': 1,
            'output': 'json'
        })

        # None値を除外
        params = {k: v for k, v in params.items() if v is not None}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('result', {}).get('status') == 200:
                            return data
                        else:
                            error_msg = data.get('result', {}).get('message', 'Unknown error')
                            raise Exception(f"API error: {error_msg}")
                    else:
                        error_text = await response.text()
                        print(f"API HTTP error {response.status}: {error_text}")
                        raise Exception(f"HTTP error: {response.status}")

        except Exception as e:
            if retry_count < self.retry_count:
                await asyncio.sleep(self.retry_delay)
                return await self._make_request(endpoint, params, retry_count + 1)
            else:
                self.logger.log_error(
                    "APIリクエストに失敗しました",
                    error=e,
                    context={'endpoint': endpoint, 'params': params}
                )
                raise

    async def search_products(
        self,
        keyword: str = None,
        sort: str = 'rank',
        floor: str = 'doujin',
        offset: int = 1,
        hits: int = 100,
        article: Optional[List[str]] = None,
        article_id: Optional[List[str]] = None,
        gte_date: Optional[str] = None,
        lte_date: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        商品を検索

        Args:
            keyword: 検索キーワード
            sort: ソート順 (rank, date, price, -price, review, match)
            floor: フロア (doujin, videoa, etc.)
            offset: オフセット
            hits: 取得件数（最大100）
            article: 絞り込み項目 (genre, actress, maker, series, etc.)
            article_id: 絞り込みID
            gte_date: 発売日以降 (YYYY-MM-DDThh:mm:ss)
            lte_date: 発売日以前 (YYYY-MM-DDThh:mm:ss)
            **kwargs: その他APIパラメータ

        Returns:
            商品リスト
        """
        cache_key = f"search:{keyword}:{sort}:{floor}:{offset}:{hits}:{article}:{article_id}:{gte_date}:{lte_date}:{kwargs}"
        
        # キャッシュから取得を試みる
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data

        # APIから取得
        params = {
            'keyword': keyword,
            'sort': sort,
            'floor': floor,
            'offset': offset,
            'hits': min(hits, 100)  # 最大100件まで
        }
        # 絞り込み条件の追加
        if article and article_id:
            for i, (a, aid) in enumerate(zip(article, article_id)):
                params[f'article[{i}]'] = a
                params[f'article_id[{i}]'] = aid
        # 日付範囲の追加
        if gte_date:
            params['gte_date'] = gte_date
        if lte_date:
            params['lte_date'] = lte_date
        # その他のパラメータを追加
        params.update(kwargs)

        data = await self._make_request('ItemList', params)
        products = data.get('result', {}).get('items', [])
        # キャッシュに保存
        self.cache.set(cache_key, products, expiry=1800)  # 30分
        return products

    async def get_product_info(self, product_id: str) -> Dict[str, Any]:
        """
        商品情報を取得

        Args:
            product_id: 商品ID

        Returns:
            商品情報
        """
        cache_key = f"product:{product_id}"
        
        # キャッシュから取得を試みる
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data

        # APIから取得
        params = {
            'article': 'actress',
            'article_id': product_id
        }
        
        data = await self._make_request('ItemList', params)
        product_info = data.get('result', {}).get('items', [{}])[0]
        
        # キャッシュに保存
        self.cache.set(cache_key, product_info, expiry=3600)  # 1時間
        
        return product_info

    async def get_latest_products(
        self,
        floor: str = 'doujin',
        offset: int = 1,
        hits: int = 100,
        sort: str = 'date'
    ) -> List[Dict[str, Any]]:
        """
        最新商品を取得

        Args:
            floor: フロア
            offset: オフセット
            hits: 取得件数
            sort: ソート順

        Returns:
            商品リスト
        """
        cache_key = f"latest:{floor}:{offset}:{hits}:{sort}"
        
        # キャッシュから取得を試みる
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data

        # APIから取得
        params = {
            'floor': floor,
            'offset': offset,
            'hits': min(hits, 100),  # 最大100件まで
            'sort': sort
        }
        
        data = await self._make_request('ItemList', params)
        products = data.get('result', {}).get('items', [])
        
        # キャッシュに保存
        self.cache.set(cache_key, products, expiry=900)  # 15分
        
        return products

    async def get_actress_info(self, actress_id: str) -> Dict[str, Any]:
        """
        女優情報を取得

        Args:
            actress_id: 女優ID

        Returns:
            女優情報
        """
        cache_key = f"actress:{actress_id}"
        
        # キャッシュから取得を試みる
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data

        # APIから取得
        params = {
            'article': 'actress',
            'article_id': actress_id
        }
        
        data = await self._make_request('ActressSearch', params)
        actress_info = data.get('result', {}).get('actress', [{}])[0]
        
        # キャッシュに保存
        self.cache.set(cache_key, actress_info, expiry=86400)  # 24時間
        
        return actress_info 