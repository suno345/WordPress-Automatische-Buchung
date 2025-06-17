import os
from typing import Dict, Any, Optional
import requests
from dotenv import load_dotenv
from ..utils.logger import setup_logger

class Grok_Analyzer:
    """FANZAの商品情報を分析するクラス"""

    def __init__(self):
        """初期化処理"""
        load_dotenv()
        self.logger = setup_logger(__name__)
        
        # Grok API設定
        self.api_key = os.getenv('GROK_API_KEY')
        self.api_url = os.getenv('GROK_API_URL')
        
        if not all([self.api_key, self.api_url]):
            raise ValueError("Grok API設定が不足しています")

    def analyze_product(self, product_info: Dict[str, Any]) -> Dict[str, str]:
        """商品情報を分析する
        
        Args:
            product_info: FANZAの商品情報
            
        Returns:
            分析結果の辞書
        """
        try:
            # 分析用のテキストを準備
            text = self._prepare_analysis_text(product_info)
            
            # Grok APIにリクエスト
            response = self._make_api_request(text)
            
            # 分析結果を整形
            result = self._format_analysis_result(response)
            
            return result
            
        except Exception as e:
            self.logger.error(f"商品分析エラー: {str(e)}")
            return {}

    def _prepare_analysis_text(self, product_info: Dict[str, Any]) -> str:
        """分析用のテキストを準備する"""
        text_parts = []
        
        # タイトル
        if 'title' in product_info:
            text_parts.append(f"タイトル: {product_info['title']}")
        
        # 説明文
        if 'description' in product_info:
            text_parts.append(f"説明文: {product_info['description']}")
        
        # 作者名
        if 'author' in product_info:
            authors = product_info['author'] if isinstance(product_info['author'], list) else [product_info['author']]
            text_parts.append(f"作者名: {', '.join(authors)}")
        
        # サークル名
        if 'maker' in product_info:
            makers = product_info['maker'] if isinstance(product_info['maker'], list) else [product_info['maker']]
            text_parts.append(f"サークル名: {', '.join(makers)}")
        
        return "\n".join(text_parts)

    def _make_api_request(self, text: str) -> Dict[str, Any]:
        """Grok APIにリクエストを送信する"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'text': text,
            'analysis_type': 'character_and_original'
        }
        
        response = requests.post(
            self.api_url,
            headers=headers,
            json=data
        )
        response.raise_for_status()
        
        return response.json()

    def _format_analysis_result(self, response: Dict[str, Any]) -> Dict[str, str]:
        """分析結果を整形する"""
        result = {}
        
        # キャラクター名の抽出
        if 'character_name' in response:
            result['character_name'] = response['character_name']
        
        # 原作名の抽出
        if 'original_work' in response:
            result['original_work'] = response['original_work']
        
        # その他の分析結果
        if 'additional_info' in response:
            for key, value in response['additional_info'].items():
                result[key] = value
        
        return result 