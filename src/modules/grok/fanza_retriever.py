import asyncio
import aiohttp
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

class FanzaDataRetriever:
    """FANZAデータ取得クラス"""

    def __init__(self, cache_dir: str = "cache", cache_expiry: int = 3600):
        self.cache_dir = cache_dir
        self.cache_expiry = cache_expiry
        self.rate_limit_value = 2
        self.rate_limit_window = 1
        self.last_request_time = 0
        
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_path(self, product_id: str) -> str:
        """キャッシュファイルのパスを取得"""
        return os.path.join(self.cache_dir, f"{product_id}.json")

    def _save_to_cache(self, product_id: str, data: Dict) -> None:
        """データをキャッシュに保存"""
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        cache_path = self._get_cache_path(product_id)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False)

    def _load_from_cache(self, product_id: str) -> Optional[Dict]:
        """キャッシュからデータを読み込み"""
        cache_path = self._get_cache_path(product_id)
        if not os.path.exists(cache_path):
            return None
        
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            # キャッシュの有効期限チェック
            cache_time = datetime.fromisoformat(cache_data["timestamp"])
            if datetime.now() - cache_time > timedelta(seconds=self.cache_expiry):
                return None
            
            return cache_data["data"]
        except Exception:
            return None

    async def rate_limit(self) -> None:
        """レート制限の実装"""
        current_time = datetime.now().timestamp()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit_window:
            await asyncio.sleep(self.rate_limit_window - time_since_last_request)
        
        self.last_request_time = datetime.now().timestamp()

    async def get_product_info_from_api(self, product_id: str) -> Dict:
        """APIから商品情報を取得"""
        await self.rate_limit()
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.example.com/products/{product_id}") as response:
                response.raise_for_status()
                data = await response.json()
                return data["items"][0]

    async def get_product_info_from_cache(self, product_id: str) -> Optional[Dict]:
        """キャッシュから商品情報を取得"""
        return self._load_from_cache(product_id)

    async def get_product_info(self, product_id: str) -> Dict:
        """商品情報を取得（キャッシュまたはAPI）"""
        # キャッシュから取得を試みる
        cached_data = await self.get_product_info_from_cache(product_id)
        if cached_data:
            return cached_data
        
        # APIから取得
        product_info = await self.get_product_info_from_api(product_id)
        self._save_to_cache(product_id, product_info)
        return product_info

    async def get_latest_products(self, limit: int = 10) -> List[Dict]:
        """最新の商品情報を取得"""
        await self.rate_limit()
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.example.com/latest?limit={limit}") as response:
                response.raise_for_status()
                data = await response.json()
                
                # 各商品の情報をキャッシュに保存
                for product in data["items"]:
                    self._save_to_cache(product["content_id"], product)
                
                return data["items"]

    def clear_cache(self) -> None:
        """キャッシュをクリア"""
        for filename in os.listdir(self.cache_dir):
            file_path = os.path.join(self.cache_dir, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

    def test_cache_expiry(self) -> bool:
        """キャッシュの有効期限切れをテスト"""
        test_id = "test_product"
        test_data = {"title": "Test Product"}
        
        # 期限切れのデータを追加
        expired_cache = {
            "timestamp": (datetime.now() - timedelta(seconds=self.cache_expiry + 1)).isoformat(),
            "data": test_data
        }
        with open(self._get_cache_path(test_id), "w", encoding="utf-8") as f:
            json.dump(expired_cache, f)
        
        # 期限切れのデータが取得できないことを確認
        if self.get_product_info_from_cache(test_id) is not None:
            return False
        
        # 有効期限内のデータを追加
        self._save_to_cache(test_id, test_data)
        
        # 有効期限内のデータが取得できることを確認
        return self.get_product_info_from_cache(test_id) == test_data

if __name__ == '__main__':
    # テスト実行
    retriever = FanzaDataRetriever(cache_dir='cache', cache_expiry=3600)
    asyncio.run(retriever.test_cache_expiry()) 