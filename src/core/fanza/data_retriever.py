"""
FANZAデータ取得モジュール
"""
from typing import Dict, Any, List, Optional
import os
import aiohttp
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json
import os.path
from bs4 import BeautifulSoup
from src.utils.fanza_scraper import search_fanza_products_by_keyword, extract_product_id_from_url, verify_image_urls

class FANZA_Data_Retriever:
    """FANZAデータ取得クラス"""
    
    def __init__(self):
        """初期化"""
        load_dotenv()
        
        # FANZA API設定
        self.api_id = os.getenv('FANZA_API_ID')
        self.affiliate_id = os.getenv('FANZA_AFFILIATE_ID')
        self.base_url = "https://api.dmm.com/affiliate/v3"
        
        if not all([self.api_id, self.affiliate_id]):
            raise ValueError("FANZA APIの認証情報が設定されていません")
        
        # キャッシュ設定
        self.cache_dir = os.getenv('CACHE_DIR', 'cache')
        self.cache_expiry = {
            'default': 3600,  # 1時間
            'product_info': 86400,  # 24時間
            'search_results': 1800  # 30分
        }
        
        # キャッシュディレクトリの作成
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # レート制限設定
        self.requests_per_second = 1
        self.last_request_time = datetime.now()
        self.request_interval = 1.0 / self.requests_per_second
    
    async def get_doujin_floor_codes(self) -> List[Dict[str, str]]:
        """フロアAPIから同人系floorコードを取得"""
        print("[DEBUG] フロアコードの取得を開始")
        params = {
            "api_id": self.api_id,
            "affiliate_id": self.affiliate_id,
            "output": "json"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/FloorList", params=params) as resp:
                    if resp.status != 200:
                        print(f"[ERROR] フロアAPI呼び出しエラー: ステータスコード {resp.status}")
                        return []
                        
                    data = await resp.json()
                    print(f"[DEBUG] フロアAPIのレスポンス: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    
                    doujin_floors = []
                    if "result" not in data:
                        print("[ERROR] フロアAPIのレスポンスに 'result' キーがありません")
                        return []
                        
                    if "site" not in data["result"] or not data["result"]["site"]:
                        print("[ERROR] フロアAPIのレスポンスに 'site' データがありません")
                        return []
                        
                    for service in data["result"]["site"][0].get("service", []):
                        if service.get("service_code") == "doujin":
                            for floor in service.get("floor", []):
                                doujin_floors.append({
                                    "floor_code": floor["floor_code"],
                                    "floor_name": floor["floor_name"]
                                })
                    
                    print(f"[DEBUG] 取得した同人フロア: {json.dumps(doujin_floors, ensure_ascii=False, indent=2)}")
                    return doujin_floors
                    
        except Exception as e:
            print(f"[ERROR] フロアコード取得中にエラーが発生: {str(e)}")
            return []

    async def get_latest_products(self, hits: int = 10, limit: int = None, sort: str = "rank") -> List[Dict[str, Any]]:
        """
        同人系floorすべてから商品情報を取得（人気順）
        Args:
            hits (int): 各floorごとの取得件数
            limit (int): limitパラメータの互換性対応（hitsと同じ）
            sort (str): ソート順
        Returns:
            List[Dict[str, Any]]: 商品情報のリスト
        """
        print("[DEBUG] 最新商品情報の取得を開始")
        all_products = []
        
        # limitパラメータの互換性対応
        if limit is not None:
            hits = limit
        
        # 同人フロアのパラメータを直接指定
        params = {
            'api_id': self.api_id,
            'affiliate_id': self.affiliate_id,
            'site': 'FANZA',
            'service': 'doujin',
            'floor': 'digital_doujin',  # 修正: doujin -> digital_doujin
            'hits': str(hits),
            'sort': sort,
            'output': 'json'
        }
        
        print("[DEBUG] FANZAのAPIリクエストを実行")
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/ItemList", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"[DEBUG] APIレスポンス: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    if 'result' in data and 'items' in data['result']:
                        products = data['result']['items']
                        print(f"[DEBUG] 取得した商品数: {len(products)}")
                        all_products.extend(products)
                    else:
                        print("[WARNING] 商品データが不正な形式です")
                else:
                    print(f"[ERROR] APIリクエストが失敗: {response.status}")
                    error_text = await response.text()
                    print(f"[ERROR] エラー詳細: {error_text}")
        
        print(f"[DEBUG] 合計 {len(all_products)} 件の商品を取得完了")
        return all_products
    
    async def get_product_info(self, product_id: str) -> Dict[str, Any]:
        """
        商品IDから商品情報を取得
        
        Args:
            product_id: 商品ID
            
        Returns:
            Dict[str, Any]: 商品情報
        """
        try:
            # キャッシュの確認
            cache_key = f"product_info_{product_id}"
            cached_data = await self._get_cache(cache_key)
            if cached_data:
                return cached_data

            # APIリクエストの準備
            params = {
                'api_id': self.api_id,
                'affiliate_id': self.affiliate_id,
                'site': 'FANZA',
                'service': 'doujin',  # 修正: サービスをdoujinに
                'floor': 'digital_doujin',  # 修正: フロアをdigital_doujinに
                'cid': product_id,
                'output': 'json'
            }

            # APIリクエストの実行
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/ItemList", params=params) as response:
                    if response.status != 200:
                        raise Exception(f"APIリクエスト失敗: {response.status}")
                    
                    data = await response.json()
                    if 'items' not in data or not data['items']:
                        raise Exception("商品情報が見つかりません")
                    
                    product_info = data['items'][0]
                    
                    # キャッシュに保存
                    await self._save_cache(cache_key, product_info)
                    
                    return product_info

        except Exception as e:
            print(f"商品情報の取得に失敗: {str(e)}")
            return {}

    async def get_playback_url(self, product_id: str) -> Optional[str]:
        """
        商品IDから再生URLを取得
        
        Args:
            product_id: 商品ID
            
        Returns:
            Optional[str]: 再生URL
        """
        try:
            product_info = await self.get_product_info(product_id)
            if not product_info:
                return None

            # サンプル動画URLの取得
            sample_movie = product_info.get('sampleMovieURL', {})
            if not sample_movie:
                return None

            # 最適なサイズの動画URLを選択
            preferred_sizes = ['size_720_480', 'size_644_414', 'size_560_360', 'size_476_306']
            for size in preferred_sizes:
                if size in sample_movie:
                    return sample_movie[size]

            return None

        except Exception as e:
            print(f"再生URLの取得に失敗: {str(e)}")
            return None

    async def _get_cache(self, key: str) -> Optional[Dict]:
        """キャッシュからデータを取得"""
        try:
            cache_file = os.path.join(self.cache_dir, f"{key}.json")
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    if datetime.fromisoformat(cache_data['timestamp']) + timedelta(seconds=self.cache_expiry['default']) > datetime.now():
                        return cache_data['data']
            return None
        except Exception:
            return None

    async def _save_cache(self, key: str, data: Dict):
        """データをキャッシュに保存"""
        try:
            cache_file = os.path.join(self.cache_dir, f"{key}.json")
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"キャッシュの保存に失敗: {str(e)}")

    async def search_products(self, keyword: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        キーワードで商品を検索する
        
        Args:
            keyword (str): 検索キーワード
            limit (int): 取得件数
            
        Returns:
            List[Dict[str, Any]]: 商品情報のリスト
        """
        # キャッシュの確認
        cache_key = f"search_{keyword}_{limit}"
        cached_data = await self._get_cache(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # レート制限の遵守
            await self._respect_rate_limit()
            
            # APIリクエスト
            params = {
                'api_id': self.api_id,
                'affiliate_id': self.affiliate_id,
                'site': 'FANZA',
                'service': 'doujin',  # 修正: サービスをdoujinに
                'floor': 'digital_doujin',  # 修正: フロアをdigital_doujinに
                'hits': str(limit),
                'keyword': keyword,
                'sort': 'rank'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/ItemList", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'items' in data:
                            products = data['items']
                            
                            # キャッシュに保存
                            await self._save_cache(cache_key, products)
                            
                            return products
                        else:
                            raise Exception("商品情報が見つかりません")
                    else:
                        error_text = await response.text()
                        raise Exception(f"APIリクエストに失敗: {error_text}")
                        
        except Exception as e:
            raise Exception(f"商品検索中にエラーが発生: {str(e)}")
    
    async def _respect_rate_limit(self):
        """レート制限を遵守"""
        now = datetime.now()
        elapsed = (now - self.last_request_time).total_seconds()
        
        if elapsed < self.request_interval:
            await asyncio.sleep(self.request_interval - elapsed)
        
        self.last_request_time = datetime.now()

    async def scrape_fanza_product_details(self, product_url: str) -> dict:
        """FANZA商品ページから説明文・キャッチコピー・サンプル画像URL等を抽出"""
        async with aiohttp.ClientSession() as session:
            async with session.get(product_url) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                # 説明文の抽出
                description = soup.select_one('.p-main__description')
                catch_copy = soup.select_one('.p-main__catchcopy')
                # サンプル画像URLの抽出（#sample-image-block img, .d-item__sample__img img 両対応）
                sample_images = []
                for img in soup.select('#sample-image-block img, .d-item__sample__img img'):
                    src = img.get('src')
                    if src:
                        sample_images.append(src)
                return {
                    'description': description.text.strip() if description else '',
                    'catch_copy': catch_copy.text.strip() if catch_copy else '',
                    'sample_images': sample_images
                }

    async def hybrid_search_products(self, keyword: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        APIでヒットしなければスクレイピングで商品ID・URLを取得するハイブリッド検索
        Args:
            keyword (str): 検索キーワード
            limit (int): 最大取得件数
        Returns:
            List[Dict[str, Any]]: 商品情報またはURL/IDリスト
        """
        try:
            # 1. まずAPIで検索
            products = await self.search_products(keyword, limit)
            if products:
                return products
        except Exception as e:
            pass  # API失敗時はスクレイピングにフォールバック

        # 2. APIでヒットしなければスクレイピング
        urls = await search_fanza_products_by_keyword(keyword)
        product_ids = [extract_product_id_from_url(url) for url in urls if extract_product_id_from_url(url)]
        # 必要に応じて詳細情報も取得可能だが、ここではIDとURLのみ返す
        return [{"product_id": pid, "url": url} for pid, url in zip(product_ids, urls)][:limit] 