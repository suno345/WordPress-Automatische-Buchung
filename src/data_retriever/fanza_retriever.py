import requests
from typing import Dict, List, Optional
from ..config.config_manager import ConfigManager
from ..utils.error_logger import ErrorLogger

class FANZA_Data_Retriever:
    """FANZAのAPIからデータを取得するクラス"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.logger = ErrorLogger()
        self.api_id = self.config.get('DMM_API_ID')
        self.affiliate_id = self.config.get('DMM_AFFILIATE_ID')
        self.base_url = "https://api.dmm.com/affiliate/v3"
        self.target_url = self.config.get('DMM_TARGET_SEARCH_PAGE_URL')
    
    def get_latest_product_ids(self, limit: int = 24) -> List[str]:
        """最新の商品IDを取得する
        
        Args:
            limit: 取得する商品数の上限
            
        Returns:
            商品IDのリスト
        """
        try:
            params = {
                'api_id': self.api_id,
                'affiliate_id': self.affiliate_id,
                'site': 'FANZA',
                'service': 'digital',
                'floor': 'videoa',
                'hits': limit,
                'offset': 1,
                'sort': 'date',
                'output': 'json'
            }
            
            response = requests.get(f"{self.base_url}/ItemList", params=params)
            response.raise_for_status()
            
            data = response.json()
            if 'items' not in data:
                return []
            
            # 商品IDを抽出
            product_ids = []
            for item in data['items']:
                if 'content_id' in item:
                    product_ids.append(item['content_id'])
            
            return product_ids[:limit]
            
        except Exception as e:
            self.logger.log_error(
                str(e),
                'FANZA_Data_Retriever',
                'get_latest_product_ids',
                {'limit': limit}
            )
            return []
    
    def get_product_info(self, product_id: str) -> Optional[Dict]:
        """商品情報を取得する
        
        Args:
            product_id: 商品ID
            
        Returns:
            商品情報の辞書。エラーの場合はNone
        """
        try:
            params = {
                'api_id': self.api_id,
                'affiliate_id': self.affiliate_id,
                'site': 'FANZA',
                'service': 'digital',
                'floor': 'videoa',
                'hits': 1,
                'offset': 1,
                'keyword': product_id,
                'output': 'json'
            }
            
            response = requests.get(f"{self.base_url}/ItemList", params=params)
            response.raise_for_status()
            
            data = response.json()
            if 'items' in data and len(data['items']) > 0:
                return data['items'][0]
            return None
            
        except Exception as e:
            self.logger.log_error(
                str(e),
                'FANZA_Data_Retriever',
                'get_product_info',
                {'product_id': product_id}
            )
            return None
    
    def get_sample_images(self, product_id: str, max_images: int = 15) -> List[str]:
        """サンプル画像のURLを取得する
        
        Args:
            product_id: 商品ID
            max_images: 取得する最大画像数
            
        Returns:
            サンプル画像URLのリスト
        """
        try:
            product_info = self.get_product_info(product_id)
            if not product_info or 'sampleImageURL' not in product_info:
                return []
            
            sample_images = []
            for image in product_info['sampleImageURL'].get('sample_s', [])[:max_images]:
                sample_images.append(image['image'])
            
            return sample_images
            
        except Exception as e:
            self.logger.log_error(
                str(e),
                'FANZA_Data_Retriever',
                'get_sample_images',
                {'product_id': product_id}
            )
            return []
    
    def get_product_details(self, product_id: str) -> Optional[Dict]:
        """商品の詳細情報を取得する
        
        Args:
            product_id: 商品ID
            
        Returns:
            商品詳細情報の辞書。エラーの場合はNone
        """
        try:
            product_info = self.get_product_info(product_id)
            if not product_info:
                return None
            
            return {
                'title': product_info.get('title', ''),
                'description': product_info.get('description', ''),
                'price': product_info.get('prices', {}).get('price', ''),
                'release_date': product_info.get('date', ''),
                'actress': [actress['name'] for actress in product_info.get('iteminfo', {}).get('actress', [])],
                'genre': [genre['name'] for genre in product_info.get('iteminfo', {}).get('genre', [])],
                'maker': product_info.get('maker', {}).get('name', ''),
                'label': product_info.get('label', {}).get('name', ''),
                'sample_images': self.get_sample_images(product_id)
            }
            
        except Exception as e:
            self.logger.log_error(
                str(e),
                'FANZA_Data_Retriever',
                'get_product_details',
                {'product_id': product_id}
            )
            return None 