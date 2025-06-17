import os
import json
import base64
import requests
from typing import Dict, List, Optional, Union
from tenacity import retry, stop_after_attempt, wait_exponential

class GrokApiError(Exception):
    """Grok APIのエラー基底クラス"""
    pass

class GrokApiAuthenticationError(GrokApiError):
    """認証エラー"""
    pass

class GrokApiRateLimitError(GrokApiError):
    """レート制限エラー"""
    pass

class GrokApiTimeoutError(GrokApiError):
    """タイムアウトエラー"""
    pass

class GrokApiValidationError(GrokApiError):
    """バリデーションエラー"""
    pass

class GrokApiClient:
    """Grok APIクライアント"""

    def __init__(self):
        """初期化"""
        self.api_key = os.getenv('GROK_API_KEY')
        if not self.api_key:
            raise GrokApiAuthenticationError("GROK_API_KEY is not set")
        
        self.base_url = "https://api.grok.x/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        # リトライ設定
        self.max_retries = 3
        self.retry_delay = 1  # 秒

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    def _make_request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict] = None,
        timeout: int = 30
    ) -> Dict:
        """
        APIリクエストを実行

        Args:
            endpoint: APIエンドポイント
            method: HTTPメソッド
            data: リクエストデータ
            timeout: タイムアウト時間（秒）

        Returns:
            Dict: APIレスポンス

        Raises:
            GrokApiAuthenticationError: 認証エラー
            GrokApiRateLimitError: レート制限エラー
            GrokApiTimeoutError: タイムアウトエラー
            GrokApiValidationError: バリデーションエラー
            GrokApiError: その他のAPIエラー
        """
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise GrokApiAuthenticationError("Invalid API key or authentication failed")
            elif response.status_code == 429:
                raise GrokApiRateLimitError("Rate limit exceeded")
            elif response.status_code == 400:
                raise GrokApiValidationError(f"Invalid request: {str(e)}")
            else:
                raise GrokApiError(f"API request failed: {str(e)}")

        except requests.exceptions.Timeout:
            raise GrokApiTimeoutError("Request timed out")

        except requests.exceptions.RequestException as e:
            raise GrokApiError(f"Request failed: {str(e)}")

        except json.JSONDecodeError as e:
            raise GrokApiError(f"Failed to parse API response: {str(e)}")

    def analyze_face_images(
        self,
        images: List[bytes],
        max_faces: int = 5
    ) -> Dict:
        """
        顔画像の分析

        Args:
            images: 画像データのリスト（最大5枚）
            max_faces: 分析する最大顔数

        Returns:
            Dict: 分析結果
        """
        if not images:
            raise GrokApiValidationError("No images provided")
        
        if len(images) > max_faces:
            raise GrokApiValidationError(f"Too many images. Maximum allowed: {max_faces}")

        try:
            encoded_images = [self._encode_image(img) for img in images]
            data = {
                "images": encoded_images,
                "max_faces": max_faces
            }
            return self._make_request("analyze/faces", data=data)

        except Exception as e:
            raise GrokApiError(f"Face analysis failed: {str(e)}")

    def generate_product_description(
        self,
        product_info: Dict,
        character_info: Dict,
        requirements: Optional[Dict] = None
    ) -> Dict:
        """
        商品説明の生成

        Args:
            product_info: 商品情報
            character_info: キャラクター情報
            requirements: 生成要件

        Returns:
            Dict: 生成された説明
        """
        try:
            data = {
                "product_info": product_info,
                "character_info": character_info,
                "requirements": requirements or {}
            }
            return self._make_request("generate/description", data=data)

        except Exception as e:
            raise GrokApiError(f"Description generation failed: {str(e)}")

    def optimize_content(
        self,
        content: str,
        content_type: str,
        requirements: Optional[Dict] = None
    ) -> Dict:
        """
        コンテンツの最適化

        Args:
            content: 最適化するコンテンツ
            content_type: コンテンツタイプ
            requirements: 最適化要件

        Returns:
            Dict: 最適化結果
        """
        try:
            data = {
                "content": content,
                "content_type": content_type,
                "requirements": requirements or {}
            }
            return self._make_request("optimize/content", data=data)

        except Exception as e:
            raise GrokApiError(f"Content optimization failed: {str(e)}")

    def _encode_image(self, image_data: bytes) -> str:
        """
        画像データをBase64エンコード

        Args:
            image_data: 画像データ

        Returns:
            str: Base64エンコードされた画像データ
        """
        try:
            return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            raise GrokApiError(f"Image encoding failed: {str(e)}")

    def _parse_face_analysis_response(self, response: Dict) -> Dict:
        """
        顔分析レスポンスのパース

        Args:
            response: APIレスポンス

        Returns:
            Dict: パースされた結果
        """
        try:
            return {
                "characters": response.get("characters", []),
                "original_works": response.get("original_works", []),
                "confidence_scores": response.get("confidence_scores", {})
            }
        except Exception as e:
            raise GrokApiError(f"Failed to parse face analysis response: {str(e)}")

    def _parse_description_response(self, response: Dict) -> Dict:
        """
        商品説明レスポンスのパース

        Args:
            response: APIレスポンス

        Returns:
            Dict: パースされた結果
        """
        try:
            return {
                "description": response.get("description", ""),
                "catch_copy": response.get("catch_copy", ""),
                "tags": response.get("tags", [])
            }
        except Exception as e:
            raise GrokApiError(f"Failed to parse description response: {str(e)}")

    def _parse_optimization_response(self, response: Dict) -> Dict:
        """
        最適化レスポンスのパース

        Args:
            response: APIレスポンス

        Returns:
            Dict: パースされた結果
        """
        try:
            return {
                "optimized_content": response.get("optimized_content", ""),
                "improvement_suggestions": response.get("improvement_suggestions", []),
                "metrics": response.get("metrics", {})
            }
        except Exception as e:
            raise GrokApiError(f"Failed to parse optimization response: {str(e)}") 