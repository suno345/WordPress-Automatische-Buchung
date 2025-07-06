"""
ハイブリッド分析クラス
Gemini: キャラクター・顔認識
Grok: 商品説明文生成
"""

import asyncio
from typing import Dict, Any
from dotenv import load_dotenv

from src.core.gemini.analyzer import Gemini_Analyzer
from src.core.grok.description_generator import Grok_Description_Generator
from src.utils.logger import get_logger
from src.utils.error_logger import Error_Logger

class Hybrid_Analyzer:
    """Gemini + Grok ハイブリッド分析クラス"""
    
    def __init__(self):
        """初期化"""
        load_dotenv()
        
        # 各APIアナライザーを初期化
        self.gemini_analyzer = Gemini_Analyzer()
        self.grok_generator = Grok_Description_Generator()
        
        # ログ設定
        self.logger = get_logger(__name__)
        self.error_logger = Error_Logger()
    
    async def analyze_product(self, product_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        商品を総合分析
        1. Gemini: キャラクター・顔認識
        2. Grok: 説明文生成
        """
        try:
            self.logger.info(f"ハイブリッド分析開始: {product_info.get('title', 'unknown')}")
            
            # Step 1: Geminiでキャラクター分析
            self.logger.debug("Gemini キャラクター分析開始")
            character_result = await self.gemini_analyzer.analyze_product(product_info)
            
            # キャラクター分析結果をログ
            character_name = character_result.get('character_name', '')
            confidence = character_result.get('confidence', 0)
            self.logger.info(f"Gemini 分析結果: {character_name} (信頼度: {confidence}%)")
            
            # Step 2: Grokで説明文生成
            self.logger.debug("Grok 説明文生成開始")
            description = await self.grok_generator.generate_description(product_info, character_result)
            
            # 結果統合
            final_result = {
                # Geminiからのキャラクター情報
                'character_name': character_result.get('character_name', ''),
                'original_work': character_result.get('original_work', ''),
                'confidence': character_result.get('confidence', 0),
                'character_features': character_result.get('character_features', ''),
                'art_style': character_result.get('art_style', ''),
                
                # Grokからの説明文
                'generated_description': description,
                
                # 分析メタデータ
                'analysis_timestamp': asyncio.get_event_loop().time(),
                'character_analyzer': 'gemini',
                'description_generator': 'grok',
                'analysis_method': 'hybrid',
                
                # エラー情報（あれば）
                'character_error': character_result.get('error_reason', ''),
            }
            
            # 分析結果の品質チェック
            quality_score = self.calculate_quality_score(final_result)
            final_result['quality_score'] = quality_score
            
            self.logger.info(f"ハイブリッド分析完了: {character_name} (品質スコア: {quality_score})")
            return final_result
            
        except Exception as e:
            self.error_logger.log_error("HYBRID_ANALYSIS_ERROR", f"ハイブリッド分析エラー: {str(e)}")
            return self.get_fallback_result(product_info, str(e))
    
    def calculate_quality_score(self, result: Dict[str, Any]) -> int:
        """分析結果の品質スコアを計算（0-100）"""
        score = 0
        
        # キャラクター認識の信頼度（0-50点）
        confidence = result.get('confidence', 0)
        score += min(confidence * 0.5, 50)
        
        # キャラクター名の有無（0-20点）
        if result.get('character_name', '').strip():
            score += 20
        
        # 原作名の有無（0-15点）
        if result.get('original_work', '').strip():
            score += 15
        
        # 説明文の品質（0-15点）
        description = result.get('generated_description', '')
        if description and len(description) >= 100:
            score += 15
        elif description and len(description) >= 50:
            score += 10
        elif description:
            score += 5
        
        return min(int(score), 100)
    
    def get_fallback_result(self, product_info: Dict[str, Any], error_reason: str) -> Dict[str, Any]:
        """フォールバック結果を生成"""
        title = product_info.get('title', '商品')
        circle = product_info.get('circle_name', '')
        
        # 基本的な説明文
        if circle:
            fallback_description = f"{circle}による{title}。高品質な作品をお楽しみください。"
        else:
            fallback_description = f"{title}。魅力的な内容の作品です。"
        
        return {
            'character_name': '',
            'original_work': '',
            'confidence': 0,
            'character_features': '',
            'art_style': '',
            'generated_description': fallback_description,
            'analysis_timestamp': asyncio.get_event_loop().time(),
            'character_analyzer': 'gemini',
            'description_generator': 'grok', 
            'analysis_method': 'hybrid_fallback',
            'quality_score': 20,  # 最低限のスコア
            'error_reason': error_reason
        }

# 旧Grok_Analyzerとの互換性のためのエイリアス
# VPSオーケストレーターで使用される
Grok_Analyzer = Hybrid_Analyzer