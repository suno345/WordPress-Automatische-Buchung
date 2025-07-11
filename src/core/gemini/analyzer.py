"""
Gemini API を使用した画像解析・キャラクター認識モジュール
Grok APIからの移行版
"""

import os
import base64
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
from dotenv import load_dotenv

from src.utils.logger import get_logger
from src.utils.error_logger import Error_Logger

class Gemini_Analyzer:
    """Gemini APIを使用した画像解析クラス"""
    
    def __init__(self):
        """初期化"""
        load_dotenv()
        
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model = os.getenv('GEMINI_MODEL', 'gemini-2.5-pro')
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        
        # ログ設定
        self.logger = get_logger(__name__)
        self.error_logger = Error_Logger()
        
        # API制限設定
        self.max_requests_per_minute = int(os.getenv('GEMINI_RPM_LIMIT', '15'))
        self.request_delay = 60 / self.max_requests_per_minute
        
        # プロンプト設定
        self.load_prompts()
        
        if not self.api_key:
            self.logger.warning("GEMINI_API_KEY が設定されていません - Gemini分析は無効化されます")
            self.api_key = None
    
    def load_prompts(self):
        """プロンプトを読み込み"""
        try:
            prompts_dir = Path(__file__).parent.parent.parent.parent / "prompts"
            
            # キャラクター分析用プロンプト
            character_prompt_file = prompts_dir / "gemini_character_prompt.txt"
            if character_prompt_file.exists():
                with open(character_prompt_file, 'r', encoding='utf-8') as f:
                    self.character_prompt = f.read()
            else:
                self.character_prompt = self.get_default_character_prompt()
            
                
        except Exception as e:
            self.logger.warning(f"プロンプトファイル読み込み失敗、デフォルトを使用: {e}")
            self.character_prompt = self.get_default_character_prompt()
    
    def get_default_character_prompt(self) -> str:
        """デフォルトキャラクター分析プロンプト"""
        return """この画像を分析して、以下の情報をJSON形式で回答してください：

1. character_name: 描かれているキャラクターの名前（不明な場合は空文字）
2. original_work: そのキャラクターの原作作品名（アニメ、ゲーム、漫画等）
3. confidence: 識別の信頼度（0-100の数値）
4. character_features: キャラクターの特徴（髪色、服装、特徴的な装身具等）
5. art_style: 画像の画風（イラスト、3DCG、写実的等）

特にアニメ、ゲーム、漫画のキャラクターに注目して分析してください。
同人作品でよく描かれる人気キャラクターの場合は、可能な限り具体的な名前と作品名を特定してください。

回答は必ずJSON形式でお願いします：
{
  "character_name": "キャラクター名",
  "original_work": "作品名", 
  "confidence": 85,
  "character_features": "特徴の説明",
  "art_style": "画風の説明"
}"""
    
    async def encode_image_to_base64(self, image_url: str) -> Optional[str]:
        """画像URLをBase64エンコード"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        return base64.b64encode(image_data).decode('utf-8')
            return None
        except Exception as e:
            self.logger.error(f"画像エンコードエラー: {e}")
            return None
    
    async def analyze_character_from_images(self, image_urls: List[str], product_info: Dict[str, Any]) -> Dict[str, Any]:
        """画像からキャラクター情報を分析"""
        try:
            if not image_urls:
                return self.get_empty_result("画像URLが提供されていません")
            
            # 最初の画像を使用（複数画像対応は将来実装）
            main_image_url = image_urls[0]
            
            # 画像をBase64エンコード
            image_base64 = await self.encode_image_to_base64(main_image_url)
            if not image_base64:
                return self.get_empty_result("画像の取得・エンコードに失敗")
            
            # Gemini APIリクエスト
            result = await self.call_gemini_api(image_base64, self.character_prompt, product_info)
            
            if result:
                # JSONパース
                try:
                    parsed_result = json.loads(result)
                    
                    # 信頼度チェック
                    confidence = parsed_result.get('confidence', 0)
                    if confidence < 50:  # 信頼度50%未満は失敗扱い
                        return self.get_empty_result(f"信頼度不足: {confidence}%")
                    
                    return {
                        'character_name': parsed_result.get('character_name', ''),
                        'original_work': parsed_result.get('original_work', ''),
                        'confidence': confidence,
                        'character_features': parsed_result.get('character_features', ''),
                        'art_style': parsed_result.get('art_style', ''),
                        'analysis_source': 'gemini'
                    }
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON解析エラー: {e}")
                    return self.get_empty_result("API応答の解析に失敗")
            
            return self.get_empty_result("API呼び出しに失敗")
            
        except Exception as e:
            self.error_logger.log_error("GEMINI_ANALYSIS_ERROR", f"キャラクター分析エラー: {str(e)}")
            return self.get_empty_result(f"分析中にエラー: {str(e)}")
    
    async def call_gemini_api(self, image_base64: Optional[str], prompt: str, product_info: Dict[str, Any]) -> Optional[str]:
        """Gemini APIを呼び出し"""
        try:
            url = f"{self.base_url}/models/{self.model}:generateContent"
            
            # リクエストボディ構築
            content_parts = [{"text": prompt}]
            
            # 画像がある場合は追加
            if image_base64:
                content_parts.append({
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image_base64
                    }
                })
            
            request_body = {
                "contents": [{
                    "parts": content_parts
                }],
                "generationConfig": {
                    "temperature": 0.1,  # 一貫性重視
                    "maxOutputTokens": 1000,
                    "topP": 0.8,
                    "topK": 10
                }
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # API呼び出し
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{url}?key={self.api_key}",
                    json=request_body,
                    headers=headers
                ) as response:
                    
                    if response.status == 200:
                        response_data = await response.json()
                        
                        # レスポンス解析
                        if 'candidates' in response_data and response_data['candidates']:
                            candidate = response_data['candidates'][0]
                            if 'content' in candidate and 'parts' in candidate['content']:
                                text_part = candidate['content']['parts'][0]
                                if 'text' in text_part:
                                    text_content = text_part['text'].strip()
                                    if text_content:  # 空文字列でないことを確認
                                        return text_content
                                    else:
                                        self.logger.warning("Gemini APIから空のレスポンス")
                                        return None
                        
                        self.logger.warning(f"Gemini APIレスポンスの構造が不正: {response_data}")
                        return None
                    
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Gemini API エラー {response.status}: {error_text}")
                        return None
            
            # レート制限対応
            await asyncio.sleep(self.request_delay)
            return None
            
        except Exception as e:
            self.error_logger.log_error("GEMINI_API_ERROR", f"API呼び出しエラー: {str(e)}")
            return None
    
    async def analyze_product(self, product_info: Dict[str, Any]) -> Dict[str, Any]:
        """商品のキャラクター分析のみ実行（説明文生成はGrokが担当）"""
        try:
            self.logger.debug(f"Gemini分析開始: {product_info.get('title', 'unknown')}")
            
            # APIキーチェック
            if not self.api_key:
                self.logger.warning("GEMINI_API_KEY が設定されていないため、分析をスキップします")
                return self.get_empty_result("APIキー未設定")
            
            # 画像URL取得
            image_urls = product_info.get('sample_images', [])
            if not image_urls and 'imageURL' in product_info:
                # FANZA APIの画像URLフォーマット対応
                if isinstance(product_info['imageURL'], dict):
                    image_urls = [product_info['imageURL'].get('large', '')]
                else:
                    image_urls = [product_info['imageURL']]
            
            self.logger.debug(f"分析対象画像数: {len(image_urls)}")
            
            # キャラクター分析のみ実行
            character_result = await self.analyze_character_from_images(image_urls, product_info)
            
            # 結果統合（説明文は含めない）
            final_result = {
                **character_result,
                'analysis_timestamp': asyncio.get_event_loop().time(),
                'api_provider': 'gemini',
                'analysis_type': 'character_only'  # キャラクター分析のみを示すフラグ
            }
            
            self.logger.info(f"Gemini キャラクター分析完了: {character_result.get('character_name', 'unknown')}")
            return final_result
            
        except Exception as e:
            self.error_logger.log_error("GEMINI_CHARACTER_ERROR", f"キャラクター分析エラー: {str(e)}")
            return self.get_empty_result(f"キャラクター分析エラー: {str(e)}")
    
    def get_empty_result(self, reason: str) -> Dict[str, Any]:
        """空の結果を返す"""
        return {
            'character_name': '',
            'original_work': '',
            'confidence': 0,
            'character_features': '',
            'art_style': '',
            'analysis_source': 'gemini',
            'error_reason': reason
        }
    

# 旧Grok_Analyzerとの互換性のためのエイリアス
Grok_Analyzer = Gemini_Analyzer