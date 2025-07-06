"""
Grok API を使用した商品説明文生成モジュール
キャラクター情報（Gemini）と商品情報を元に魅力的な説明文を生成
"""

import os
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from pathlib import Path
import json
from dotenv import load_dotenv

from src.utils.logger import get_logger
from src.utils.error_logger import Error_Logger

class Grok_Description_Generator:
    """Grok APIを使用した商品説明文生成クラス"""
    
    def __init__(self):
        """初期化"""
        load_dotenv()
        
        self.api_key = os.getenv('GROK_API_KEY')
        self.base_url = os.getenv('GROK_BASE_URL', 'https://api.x.ai/v1')
        self.model = os.getenv('GROK_MODEL', 'grok-beta')
        
        # ログ設定
        self.logger = get_logger(__name__)
        self.error_logger = Error_Logger()
        
        # API制限設定
        self.max_requests_per_minute = int(os.getenv('GROK_RPM_LIMIT', '50'))
        self.request_delay = 60 / self.max_requests_per_minute
        
        # プロンプト読み込み
        self.load_prompts()
        
        if not self.api_key:
            raise ValueError("GROK_API_KEY が設定されていません")
    
    def load_prompts(self):
        """プロンプトを読み込み"""
        try:
            prompts_dir = Path(__file__).parent.parent.parent.parent / "prompts"
            
            # 説明文生成用プロンプト
            description_prompt_file = prompts_dir / "grok_description_prompt.txt"
            if description_prompt_file.exists():
                with open(description_prompt_file, 'r', encoding='utf-8') as f:
                    self.description_prompt = f.read()
            else:
                self.description_prompt = self.get_default_description_prompt()
                
        except Exception as e:
            self.logger.warning(f"プロンプトファイル読み込み失敗、デフォルトを使用: {e}")
            self.description_prompt = self.get_default_description_prompt()
    
    def get_default_description_prompt(self) -> str:
        """デフォルト説明文生成プロンプト"""
        return """以下の商品情報とキャラクター分析結果を元に、魅力的で読みやすい商品説明文を生成してください。

## 商品情報
- タイトル: {title}
- ジャンル: {genre}
- サークル名: {circle}
- 価格: {price}
- 発売日: {release_date}

## キャラクター分析結果（Gemini AI）
- キャラクター名: {character_name}
- 原作作品: {original_work}
- 信頼度: {confidence}%
- キャラクター特徴: {character_features}
- 画風: {art_style}

## 説明文生成要件

### 基本要件
- 文字数: 200-400字程度
- 構成: 2-3段落
- 文体: 丁寧で親しみやすい
- ターゲット: 同人作品ファン、原作ファン

### 内容要件
1. **キャラクターの魅力**: 分析結果を活用した特徴的な要素
2. **原作への言及**: ファンが共感できる原作要素
3. **作品の特色**: サークルの特徴、画風、ストーリー要素
4. **読者への訴求**: なぜこの作品が特別なのか

### 避けるべき内容
- 主観的な評価やレビュー
- 価格に関する言及
- 過度な宣伝文句
- 不適切な表現

### 特別な配慮
- キャラクター信頼度が低い場合（50%未満）は、キャラクター名を使わず一般的な表現にする
- 原作不明の場合は、画風やジャンルを中心とした説明にする
- サークル名は必ず言及する

## 出力形式
説明文のみをプレーンテキストで出力してください。JSON形式やマークダウンは不要です。

## 出力例
「この作品では、○○（原作）で人気の△△（キャラクター）が美しく描かれています。◇◇（サークル）による繊細なタッチで、キャラクターの魅力的な□□が印象的に表現されています。

原作ファンにとって見逃せない、△△の新たな一面を楽しめる内容となっており、高品質なイラストと丁寧な構成が作品の魅力を引き立てています。

○○の世界観を存分に味わえる、ファン必見の作品です。」"""
    
    async def generate_description(self, product_info: Dict[str, Any], character_info: Dict[str, Any]) -> str:
        """商品説明文を生成"""
        try:
            # キャラクター情報の信頼度チェック
            confidence = character_info.get('confidence', 0)
            character_name = character_info.get('character_name', '') if confidence >= 50 else ''
            original_work = character_info.get('original_work', '') if confidence >= 50 else ''
            
            # プロンプトに情報を埋め込み
            formatted_prompt = self.description_prompt.format(
                title=product_info.get('title', ''),
                genre=product_info.get('genre', ''),
                circle=product_info.get('circle_name', ''),
                price=product_info.get('price', ''),
                release_date=product_info.get('release_date', ''),
                character_name=character_name,
                original_work=original_work,
                confidence=confidence,
                character_features=character_info.get('character_features', ''),
                art_style=character_info.get('art_style', '')
            )
            
            # Grok API呼び出し
            result = await self.call_grok_api(formatted_prompt)
            
            if result:
                return result.strip()
            else:
                return self.get_default_description(product_info, character_info)
                
        except Exception as e:
            self.error_logger.log_error("GROK_DESCRIPTION_ERROR", f"説明文生成エラー: {str(e)}")
            return self.get_default_description(product_info, character_info)
    
    async def call_grok_api(self, prompt: str) -> Optional[str]:
        """Grok APIを呼び出し"""
        try:
            url = f"{self.base_url}/chat/completions"
            
            request_body = {
                "messages": [
                    {
                        "role": "system",
                        "content": "あなたは同人作品の魅力的な商品説明文を生成する専門家です。与えられた情報を元に、ファンに響く自然で読みやすい説明文を作成してください。"
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "model": self.model,
                "temperature": 0.7,  # 創作性とバランス
                "max_tokens": 500,
                "top_p": 0.9
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # API呼び出し
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=request_body, headers=headers) as response:
                    
                    if response.status == 200:
                        response_data = await response.json()
                        
                        if 'choices' in response_data and response_data['choices']:
                            choice = response_data['choices'][0]
                            if 'message' in choice and 'content' in choice['message']:
                                return choice['message']['content']
                    
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Grok API エラー {response.status}: {error_text}")
                        return None
            
            # レート制限対応
            await asyncio.sleep(self.request_delay)
            return None
            
        except Exception as e:
            self.error_logger.log_error("GROK_API_ERROR", f"API呼び出しエラー: {str(e)}")
            return None
    
    def get_default_description(self, product_info: Dict[str, Any], character_info: Dict[str, Any]) -> str:
        """デフォルト説明文を生成"""
        title = product_info.get('title', '商品')
        circle = product_info.get('circle_name', '')
        character_name = character_info.get('character_name', '')
        original_work = character_info.get('original_work', '')
        
        # キャラクター名がある場合
        if character_name and original_work:
            description = f"{original_work}の{character_name}を題材とした{title}。"
        else:
            description = f"{title}。"
        
        # サークル名を追加
        if circle:
            description += f"{circle}による高品質なイラストと魅力的な内容で、ファンにおすすめの作品です。"
        else:
            description += f"高品質なイラストと魅力的な内容の作品です。"
        
        return description