import os
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from ..utils.logger import setup_logger
from ..utils.cache_manager import CacheManager

class FANZA_Data_Retriever:
    """FANZA APIからのデータ取得を担当するクラス"""

    def __init__(self):
        """初期化処理"""
        load_dotenv()
        self.logger = setup_logger(__name__)
        self.cache_manager = CacheManager()
        
        # API設定
        self.api_id = os.getenv('FANZA_API_ID')
        self.affiliate_id = os.getenv('FANZA_AFFILIATE_ID')
        self.base_url = "https://api.dmm.com/affiliate/v3"
        
        if not all([self.api_id, self.affiliate_id]):
            raise ValueError("FANZA API設定が不足しています")
        
        # レート制限管理
        self.request_count = 0
        self.last_request_time = datetime.now()
        self.rate_limit = 1  # 1秒あたりのリクエスト数
        
        # キャッシュ設定
        self.cache_expiry = {
            'product_info': 86400,  # 24時間
            'search_results': 1800  # 30分
        }

    async def _wait_for_rate_limit(self):
        """レート制限に基づいて待機時間を計算"""
        now = datetime.now()
        time_diff = (now - self.last_request_time).total_seconds()
        
        if time_diff < 1.0 / self.rate_limit:
            await asyncio.sleep(1.0 / self.rate_limit - time_diff)
        
        self.last_request_time = datetime.now()
        self.request_count += 1

    async def _make_api_request(self, endpoint: str, params: Dict[str, Any]) -> Dict:
        """APIリクエストを実行"""
        await self._wait_for_rate_limit()
        
        params.update({
            'api_id': self.api_id,
            'affiliate_id': self.affiliate_id,
            'site': 'FANZA',
            'service': 'digital',
            'floor': 'doujin'
        })
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/{endpoint}", params=params) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                self.logger.error(f"APIリクエストエラー: {str(e)}")
                raise

    async def get_product_info(self, product_id: str) -> Optional[Dict]:
        """商品IDに基づいて商品情報を取得する
        
        Args:
            product_id: 商品ID
            
        Returns:
            商品情報の辞書。エラーの場合はNone
        """
        cache_key = f"product_info_{product_id}"
        
        # キャッシュから取得を試みる
        cached_data = self.cache_manager.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # APIリクエストのパラメータ
            params = {
                'api_id': self.api_id,
                'affiliate_id': self.affiliate_id,
                'site': 'FANZA',
                'service': 'digital',
                'floor': 'doujin',
                'article': product_id
            }
            
            # APIリクエスト
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/Item", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'items' in data and data['items']:
                            product_info = data['items'][0]
                            
                            # キャッシュに保存
                            self.cache_manager.set(
                                cache_key,
                                product_info,
                                self.cache_expiry['product_info']
                            )
                            
                            return product_info
                    else:
                        self.logger.error(f"商品情報取得エラー: {response.status}")
                        return None
                        
        except Exception as e:
            self.logger.error(f"商品情報取得エラー: {str(e)}")
            return None

    async def get_latest_products(
        self,
        hits: int = 100,
        offset: int = 0,
        keyword: Optional[str] = None,
        sort: str = 'date'
    ) -> List[Dict]:
        """最新の商品情報を取得する
        
        Args:
            hits: 取得件数（最大100）
            offset: 取得開始位置
            keyword: 検索キーワード
            sort: ソート順（rank, date, price）
            
        Returns:
            商品情報のリスト
        """
        cache_key = f"search_results_{hits}_{offset}_{keyword}_{sort}"
        
        # キャッシュから取得を試みる
        cached_data = self.cache_manager.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # APIリクエストのパラメータ
            params = {
                'api_id': self.api_id,
                'affiliate_id': self.affiliate_id,
                'site': 'FANZA',
                'service': 'digital',
                'floor': 'doujin',
                'hits': min(hits, 100),  # 最大100件まで
                'offset': offset,
                'sort': sort
            }
            
            if keyword:
                params['keyword'] = keyword
            
            # APIリクエスト
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/ItemList", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'items' in data:
                            products = data['items']
                            
                            # キャッシュに保存
                            self.cache_manager.set(
                                cache_key,
                                products,
                                self.cache_expiry['search_results']
                            )
                            
                            return products
                    else:
                        self.logger.error(f"商品一覧取得エラー: {response.status}")
                        return []
                        
        except Exception as e:
            self.logger.error(f"商品一覧取得エラー: {str(e)}")
            return []

    async def get_product_details(self, product_id: str) -> Optional[Dict]:
        """商品の詳細情報を取得する（スクレイピングを含む）
        
        Args:
            product_id: 商品ID
            
        Returns:
            商品詳細情報の辞書。エラーの場合はNone
        """
        # 基本情報の取得
        product_info = await self.get_product_info(product_id)
        if not product_info:
            return None
        
        try:
            # TODO: スクレイピングによる詳細情報の取得
            # 現在は基本情報のみを返す
            return product_info
            
        except Exception as e:
            self.logger.error(f"商品詳細取得エラー: {str(e)}")
            return None

    def _validate_api_response(self, response: aiohttp.ClientResponse) -> bool:
        """APIレスポンスの検証
        
        Args:
            response: APIレスポンス
            
        Returns:
            検証結果（True: 有効, False: 無効）
        """
        if response.status != 200:
            return False
        
        # TODO: レスポンスの内容検証
        return True 