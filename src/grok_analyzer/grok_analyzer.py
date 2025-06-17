import requests
from typing import Dict, List, Optional
from ..config.config_manager import ConfigManager
from ..utils.error_logger import ErrorLogger

class Grok_Analyzer:
    """Grok APIを使用してコンテンツを分析するクラス"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.logger = ErrorLogger()
        self.api_key = self.config.get('XAI_API_KEY')
        self.base_url = "https://api.grok.ai/v1"  # Grok APIの実際のエンドポイント
    
    def analyze_content(self, content: str) -> Optional[Dict]:
        """コンテンツを分析し、特徴を抽出する
        
        Args:
            content: 分析対象のコンテンツ
            
        Returns:
            分析結果の辞書。エラーの場合はNone
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'text': content,
                'analysis_type': 'content_analysis',
                'language': 'ja',
                'max_keywords': 10,
                'max_entities': 5
            }
            
            response = requests.post(
                f"{self.base_url}/analyze",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            
            # 分析結果を整形
            return {
                'keywords': result.get('keywords', []),
                'entities': result.get('entities', []),
                'sentiment': result.get('sentiment', {}),
                'summary': result.get('summary', ''),
                'tags': self._extract_tags(result)
            }
            
        except Exception as e:
            self.logger.log_error(
                str(e),
                'Grok_Analyzer',
                'analyze_content',
                {'content_length': len(content)}
            )
            return None
    
    def generate_tags(self, content: str, max_tags: int = 10) -> List[str]:
        """コンテンツからタグを生成する
        
        Args:
            content: タグ生成の対象コンテンツ
            max_tags: 生成する最大タグ数
            
        Returns:
            生成されたタグのリスト
        """
        try:
            analysis_result = self.analyze_content(content)
            if not analysis_result:
                return []
            
            # キーワードとエンティティからタグを生成
            tags = set()
            
            # キーワードをタグとして追加
            if 'keywords' in analysis_result:
                tags.update(k['text'] for k in analysis_result['keywords'])
            
            # エンティティをタグとして追加
            if 'entities' in analysis_result:
                tags.update(e['text'] for e in analysis_result['entities'])
            
            return list(tags)[:max_tags]
            
        except Exception as e:
            self.logger.log_error(
                str(e),
                'Grok_Analyzer',
                'generate_tags',
                {'content_length': len(content)}
            )
            return []
    
    def analyze_sentiment(self, content: str) -> Optional[Dict]:
        """コンテンツの感情分析を行う
        
        Args:
            content: 分析対象のコンテンツ
            
        Returns:
            感情分析結果の辞書。エラーの場合はNone
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'text': content,
                'analysis_type': 'sentiment',
                'language': 'ja',
                'detailed': True
            }
            
            response = requests.post(
                f"{self.base_url}/analyze",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            
            return {
                'overall_sentiment': result.get('sentiment', {}),
                'aspects': result.get('aspects', []),
                'emotions': result.get('emotions', {})
            }
            
        except Exception as e:
            self.logger.log_error(
                str(e),
                'Grok_Analyzer',
                'analyze_sentiment',
                {'content_length': len(content)}
            )
            return None
    
    def _extract_tags(self, analysis_result: Dict) -> List[str]:
        """分析結果からタグを抽出する
        
        Args:
            analysis_result: 分析結果の辞書
            
        Returns:
            抽出されたタグのリスト
        """
        tags = set()
        
        # キーワードからタグを抽出
        if 'keywords' in analysis_result:
            tags.update(k['text'] for k in analysis_result['keywords'])
        
        # エンティティからタグを抽出
        if 'entities' in analysis_result:
            tags.update(e['text'] for e in analysis_result['entities'])
        
        return list(tags) 