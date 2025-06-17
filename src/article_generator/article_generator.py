from typing import Dict, List, Optional
from ..config.config_manager import ConfigManager
from ..utils.error_logger import ErrorLogger
from ..grok_analyzer.grok_analyzer import Grok_Analyzer

class WordPress_Article_Generator:
    """WordPress記事を生成するクラス"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.logger = ErrorLogger()
        self.grok_analyzer = Grok_Analyzer()
    
    def generate_article_content(
        self,
        product_info: Dict,
        analysis_result: Optional[Dict] = None
    ) -> Dict:
        """記事コンテンツを生成する
        
        Args:
            product_info: 商品情報の辞書
            analysis_result: Grok APIの分析結果（オプション）
            
        Returns:
            生成された記事コンテンツの辞書
        """
        try:
            # 商品情報から基本コンテンツを生成
            content = self._generate_basic_content(product_info)
            
            # 分析結果がある場合は、それを活用してコンテンツを拡張
            if analysis_result:
                content = self._enhance_content_with_analysis(content, analysis_result)
            
            # タグを生成
            tags = self.grok_analyzer.generate_tags(content)
            
            return {
                'title': self._generate_title(product_info),
                'content': content,
                'tags': tags,
                'categories': self._determine_categories(product_info),
                'meta_description': self._generate_meta_description(content)
            }
            
        except Exception as e:
            self.logger.log_error(
                str(e),
                'WordPress_Article_Generator',
                'generate_article_content',
                {'product_id': product_info.get('id', 'unknown')}
            )
            return {}
    
    def _generate_basic_content(self, product_info: Dict) -> str:
        """商品情報から基本コンテンツを生成する
        
        Args:
            product_info: 商品情報の辞書
            
        Returns:
            生成された基本コンテンツ
        """
        content_parts = []
        
        # タイトル
        content_parts.append(f"# {product_info.get('title', '')}")
        
        # 商品説明
        if 'description' in product_info:
            content_parts.append("\n## 商品説明")
            content_parts.append(product_info['description'])
        
        # 出演者情報
        if 'actress' in product_info and product_info['actress']:
            content_parts.append("\n## 出演者")
            content_parts.append(", ".join(product_info['actress']))
        
        # ジャンル情報
        if 'genre' in product_info and product_info['genre']:
            content_parts.append("\n## ジャンル")
            content_parts.append(", ".join(product_info['genre']))
        
        # メーカー情報
        if 'maker' in product_info:
            content_parts.append("\n## メーカー")
            content_parts.append(product_info['maker'])
        
        # レーベル情報
        if 'label' in product_info:
            content_parts.append("\n## レーベル")
            content_parts.append(product_info['label'])
        
        # 価格情報
        if 'price' in product_info:
            content_parts.append("\n## 価格")
            content_parts.append(f"¥{product_info['price']}")
        
        return "\n".join(content_parts)
    
    def _enhance_content_with_analysis(self, content: str, analysis_result: Dict) -> str:
        """分析結果を活用してコンテンツを拡張する
        
        Args:
            content: 基本コンテンツ
            analysis_result: 分析結果の辞書
            
        Returns:
            拡張されたコンテンツ
        """
        # 分析結果に基づいてコンテンツを拡張するロジックを実装
        # 例: キーワードの強調、関連情報の追加など
        return content
    
    def _generate_title(self, product_info: Dict) -> str:
        """記事のタイトルを生成する
        
        Args:
            product_info: 商品情報の辞書
            
        Returns:
            生成されたタイトル
        """
        title = product_info.get('title', '')
        if 'actress' in product_info and product_info['actress']:
            actress = product_info['actress'][0]
            title = f"{actress}出演 {title}"
        return title
    
    def _determine_categories(self, product_info: Dict) -> List[str]:
        """記事のカテゴリーを決定する
        
        Args:
            product_info: 商品情報の辞書
            
        Returns:
            カテゴリーのリスト
        """
        categories = ['FANZA']
        if 'genre' in product_info:
            categories.extend(product_info['genre'][:3])  # 上位3つのジャンルをカテゴリーとして使用
        return categories
    
    def _generate_meta_description(self, content: str) -> str:
        """メタディスクリプションを生成する
        
        Args:
            content: 記事コンテンツ
            
        Returns:
            生成されたメタディスクリプション
        """
        # コンテンツの最初の200文字を取得し、HTMLタグを除去
        description = content.split('\n')[0]
        description = description.replace('#', '').strip()
        return description[:200] + '...' if len(description) > 200 else description 