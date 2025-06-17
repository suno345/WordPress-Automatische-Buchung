"""
WordPress記事生成モジュール
"""
from typing import Dict, Any
import os
from dotenv import load_dotenv

class WordPressArticleGenerator:
    """WordPress記事生成クラス"""
    
    def __init__(self):
        """初期化"""
        load_dotenv()
        self.logger = None  # ロガーは後で設定
        
    def generate_article_content(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        記事コンテンツを生成する
        
        Args:
            product_info (Dict[str, Any]): 商品情報
            grok_result (Dict[str, Any]): Grok分析結果
            
        Returns:
            Dict[str, Any]: 生成された記事データ
        """
        try:
            # 記事データの生成
            article_data = {
                'title': self._generate_title(product_info, grok_result),
                'content': self._generate_content(product_info, grok_result),
                'status': 'draft',  # 下書きとして保存
                'categories': self._get_categories(product_info),
                'tags': self._get_tags(product_info, grok_result),
                'custom_taxonomies': self._get_custom_taxonomies(product_info, grok_result)
            }
            
            return article_data
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"記事生成中にエラーが発生: {str(e)}")
            raise
    
    def _generate_title(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> str:
        """タイトルを生成"""
        title = product_info.get('title', '')
        character_name = grok_result.get('character_name', '')
        
        if character_name:
            return f"【{title}】{character_name}"
        return title
    
    def _generate_content(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> str:
        """本文を生成"""
        content_parts = []
        
        # リード文
        content_parts.append(self._generate_lead(product_info, grok_result))
        
        # 情報テーブル
        content_parts.append(self._generate_info_table(product_info, grok_result))
        
        # 画像ギャラリー
        content_parts.append(self._generate_image_gallery(product_info))
        
        # ストーリー
        content_parts.append(self._generate_story(product_info))
        
        # アフィリエイトリンク
        content_parts.append(self._generate_affiliate_link(product_info))
        
        return '\n\n'.join(content_parts)
    
    def _generate_lead(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> str:
        """リード文を生成"""
        title = product_info.get('title', '')
        character_name = grok_result.get('character_name', '')
        original_work = grok_result.get('original_work', '')
        
        lead = f"{title}は"
        if character_name:
            lead += f"{character_name}が"
        if original_work:
            lead += f"{original_work}の"
        lead += "同人作品です。"
        
        return lead
    
    def _generate_info_table(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> str:
        """情報テーブルを生成"""
        table = [
            "<!-- wp:table -->",
            "<figure class='wp-block-table'><table><tbody>"
        ]
        
        # サークル名
        if 'maker' in product_info:
            table.append(f"<tr><td>サークル名</td><td>{product_info['maker'][0]}</td></tr>")
        
        # 作者名
        if 'author' in product_info:
            table.append(f"<tr><td>作者名</td><td>{product_info['author'][0]}</td></tr>")
        
        # 原作名
        if 'original_work' in grok_result:
            table.append(f"<tr><td>原作名</td><td>{grok_result['original_work']}</td></tr>")
        
        # キャラクター名
        if 'character_name' in grok_result:
            table.append(f"<tr><td>キャラクター名</td><td>{grok_result['character_name']}</td></tr>")
        
        table.extend([
            "</tbody></table></figure>",
            "<!-- /wp:table -->"
        ])
        
        return '\n'.join(table)
    
    def _generate_image_gallery(self, product_info: Dict[str, Any]) -> str:
        """画像ギャラリーを生成"""
        if 'sampleImageURL' not in product_info:
            return ""
            
        gallery = [
            "<!-- wp:gallery -->",
            "<figure class='wp-block-gallery'>"
        ]
        
        for image_url in product_info['sampleImageURL'].values():
            gallery.append(f"<figure class='wp-block-image'><img src='{image_url}' alt='サンプル画像'/></figure>")
        
        gallery.extend([
            "</figure>",
            "<!-- /wp:gallery -->"
        ])
        
        return '\n'.join(gallery)
    
    def _generate_story(self, product_info: Dict[str, Any]) -> str:
        """ストーリーを生成"""
        if 'description' not in product_info:
            return ""
            
        return f"<!-- wp:paragraph -->\n<p>{product_info['description']}</p>\n<!-- /wp:paragraph -->"
    
    def _generate_affiliate_link(self, product_info: Dict[str, Any]) -> str:
        """アフィリエイトリンクを生成"""
        if 'affiliateURL' not in product_info:
            return ""
            
        return (
            "<!-- wp:button -->\n"
            f"<div class='wp-block-button'><a class='wp-block-button__link' href='{product_info['affiliateURL']}'>"
            "FANZAでこの作品をチェックする</a></div>\n"
            "<!-- /wp:button -->"
        )
    
    def _get_categories(self, product_info: Dict[str, Any]) -> list:
        """カテゴリーを取得"""
        categories = []
        if 'genre' in product_info:
            categories.extend(product_info['genre'])
        return categories
    
    def _get_tags(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> list:
        """タグを取得"""
        tags = []
        
        # 作者名をタグとして追加
        if 'author' in product_info:
            tags.extend(product_info['author'])
        
        # キャラクター名をタグとして追加
        if 'character_name' in grok_result:
            tags.append(grok_result['character_name'])
        
        return tags
    
    def _get_custom_taxonomies(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> Dict[str, Any]:
        """カスタムタクソノミーを取得"""
        taxonomies = {}
        
        # 原作名
        if 'original_work' in grok_result:
            taxonomies['original_work'] = grok_result['original_work']
        
        # キャラクター名
        if 'character_name' in grok_result:
            taxonomies['character_name'] = grok_result['character_name']
        
        # サークル名
        if 'maker' in product_info:
            taxonomies['circle_name'] = product_info['maker'][0]
        
        return taxonomies 