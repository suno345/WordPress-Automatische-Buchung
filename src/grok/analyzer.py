import os
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from PIL import Image
import io
import base64
from dotenv import load_dotenv
from ..utils.logger import setup_logger
from ..utils.cache_manager import CacheManager

class Grok_Analyzer:
    """Grok APIを使用して画像分析とキャラクター推測を行うクラス"""

    def __init__(self):
        """初期化処理"""
        load_dotenv()
        self.logger = setup_logger(__name__)
        self.cache_manager = CacheManager()
        
        # API設定
        self.api_key = os.getenv('GROK_API_KEY')
        self.api_url = os.getenv('GROK_API_URL', 'https://api.grok.ai/v1')
        
        if not self.api_key:
            raise ValueError("Grok APIキーが設定されていません")
        
        # キャッシュ設定
        self.cache_expiry = 86400  # 24時間

    async def get_anime_face_image_data(self, image_url: str) -> Optional[List[bytes]]:
        """画像から顔部分を抽出する
        
        Args:
            image_url: 画像のURL
            
        Returns:
            顔画像データのリスト。エラーの場合はNone
        """
        try:
            # 画像のダウンロード
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        self.logger.error(f"画像のダウンロードに失敗: {response.status}")
                        return None
                    
                    image_data = await response.read()
            
            # TODO: 顔検出とトリミングの実装
            # 現在はダミーデータを返す
            return [image_data]
            
        except Exception as e:
            self.logger.error(f"顔画像データ取得エラー: {str(e)}")
            return None

    async def infer_origin_and_character(
        self,
        face_images: List[bytes],
        title: str,
        description: str
    ) -> Optional[Dict[str, str]]:
        """原作名とキャラクター名を推測する
        
        Args:
            face_images: 顔画像データのリスト
            title: 商品タイトル
            description: 商品説明文
            
        Returns:
            推測結果の辞書。エラーの場合はNone
        """
        try:
            # キャッシュキーの生成
            cache_key = f"grok_inference_{title}"
            
            # キャッシュから取得を試みる
            cached_result = self.cache_manager.get(cache_key)
            if cached_result:
                return cached_result
            
            # TODO: Grok APIの実装
            # 現在はダミーデータを返す
            result = {
                'original_work': '推測された原作名',
                'character_name': '推測されたキャラクター名'
            }
            
            # キャッシュに保存
            self.cache_manager.set(cache_key, result, self.cache_expiry)
            
            return result
            
        except Exception as e:
            self.logger.error(f"原作・キャラクター推測エラー: {str(e)}")
            return None

    async def _call_grok_api(self, endpoint: str, data: Dict[str, Any]) -> Optional[Dict]:
        """Grok APIを呼び出す
        
        Args:
            endpoint: APIエンドポイント
            data: リクエストデータ
            
        Returns:
            APIレスポンス。エラーの場合はNone
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/{endpoint}",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.error(f"Grok APIエラー: {response.status}")
                        return None
                        
        except Exception as e:
            self.logger.error(f"Grok API呼び出しエラー: {str(e)}")
            return None

    async def _download_image(self, image_url: str) -> Optional[bytes]:
        """画像をダウンロードする"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        self.logger.error(f"画像ダウンロードエラー: {response.status}")
                        return None
        except Exception as e:
            self.logger.error(f"画像ダウンロードエラー: {str(e)}")
            return None

    def _detect_and_crop_faces(self, image_data: bytes) -> List[bytes]:
        """画像から顔を検出してトリミングする"""
        try:
            # 画像を開く
            image = Image.open(io.BytesIO(image_data))
            
            # TODO: アニメ顔検出ライブラリを使用して顔を検出
            # 現在は仮の実装として、画像を中央で分割
            width, height = image.size
            face_regions = [
                image.crop((0, 0, width//2, height//2)),
                image.crop((width//2, 0, width, height//2)),
                image.crop((0, height//2, width//2, height)),
                image.crop((width//2, height//2, width, height))
            ]
            
            # トリミングした画像をバイト列に変換
            cropped_faces = []
            for face in face_regions:
                buffer = io.BytesIO()
                face.save(buffer, format='JPEG')
                cropped_faces.append(buffer.getvalue())
            
            return cropped_faces[:5]  # 最大5枚まで返す
            
        except Exception as e:
            self.logger.error(f"顔検出・トリミングエラー: {str(e)}")
            return []

    def _encode_image(self, image_data: bytes) -> str:
        """画像データをBase64エンコードする"""
        return base64.b64encode(image_data).decode('utf-8')

    async def get_anime_face_image_data(self, image_url: str) -> Optional[List[str]]:
        """FANZA商品ページから取得したサンプル画像URLを元に顔画像データを取得"""
        cache_key = f"face_analysis_{image_url}"
        
        # キャッシュから取得を試みる
        cached_data = self.cache_manager.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # 画像をダウンロード
            image_data = await self._download_image(image_url)
            if not image_data:
                return None
            
            # 顔を検出してトリミング
            cropped_faces = self._detect_and_crop_faces(image_data)
            if not cropped_faces:
                return None
            
            # トリミングした画像をBase64エンコード
            encoded_faces = [self._encode_image(face) for face in cropped_faces]
            
            # キャッシュに保存
            self.cache_manager.set(cache_key, encoded_faces, self.cache_expiry)
            
            return encoded_faces
            
        except Exception as e:
            self.logger.error(f"顔画像データ取得エラー: {str(e)}")
            return None

    async def infer_origin_and_character(
        self,
        face_images: List[str],
        product_title: str,
        product_description: str
    ) -> Dict[str, str]:
        """トリミングした顔画像データから原作名・キャラ名を推測"""
        cache_key = f"character_inference_{product_title}"
        
        # キャッシュから取得を試みる
        cached_data = self.cache_manager.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # プロンプトテンプレートの作成
            prompt = self._create_analysis_prompt(
                face_images,
                product_title,
                product_description
            )
            
            # Grok APIにリクエスト
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/analyze",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "prompt": prompt,
                        "images": face_images
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # 結果を整形
                        inference_result = {
                            "original_work": result.get("original_work", ""),
                            "character_name": result.get("character_name", ""),
                            "confidence_score": result.get("confidence_score", 0.0)
                        }
                        
                        # キャッシュに保存
                        self.cache_manager.set(
                            cache_key,
                            inference_result,
                            self.cache_expiry
                        )
                        
                        return inference_result
                    else:
                        self.logger.error(f"Grok APIエラー: {response.status}")
                        return {
                            "original_work": "",
                            "character_name": "",
                            "confidence_score": 0.0
                        }
                        
        except Exception as e:
            self.logger.error(f"キャラクター推測エラー: {str(e)}")
            return {
                "original_work": "",
                "character_name": "",
                "confidence_score": 0.0
            }

    def _create_analysis_prompt(
        self,
        face_images: List[str],
        product_title: str,
        product_description: str
    ) -> str:
        """分析用のプロンプトを作成"""
        return f"""
        以下の情報から、アニメ作品の原作名とキャラクター名を推測してください：

        商品タイトル: {product_title}
        商品説明: {product_description}

        提供された画像は、この商品のキャラクターの顔画像です。
        画像の特徴から、以下の情報を推測してください：
        1. 原作作品名
        2. キャラクター名
        3. 推測の確信度（0.0-1.0）

        回答は以下のJSON形式で返してください：
        {{
            "original_work": "原作作品名",
            "character_name": "キャラクター名",
            "confidence_score": 0.0
        }}
        """ 