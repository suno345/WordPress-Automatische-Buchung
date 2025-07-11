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
        # 新しいsample_imagesフィールドに対応
        sample_images = product_info.get('sample_images', [])
        
        # 従来のsampleImageURLとの互換性維持
        if not sample_images and 'sampleImageURL' in product_info:
            sample_images = list(product_info['sampleImageURL'].values())
        
        if not sample_images:
            return ""
            
        gallery = [
            "<!-- wp:gallery -->",
            "<figure class='wp-block-gallery'>"
        ]
        
        for image_url in sample_images:
            if image_url:  # 空文字列チェック
                gallery.append(f"<figure class='wp-block-image'><img src='{image_url}' alt='サンプル画像'/></figure>")
        
        gallery.extend([
            "</figure>",
            "<!-- /wp:gallery -->"
        ])
        
        return '\n'.join(gallery)
    
    def _generate_story(self, product_info: Dict[str, Any]) -> str:
        """ストーリーを生成"""
        # 複数のソースから説明文を取得
        story_content = ""
        
        # 1. FANZA の説明文
        if 'description' in product_info and product_info['description']:
            story_content = product_info['description']
        
        # 2. Grok/AI生成の説明文（より詳細な場合は置き換え）
        if 'generated_description' in product_info and product_info['generated_description']:
            ai_desc = product_info['generated_description']
            if len(ai_desc) > len(story_content):  # より詳細な場合
                story_content = ai_desc
        
        # 3. フォールバック説明文
        if not story_content:
            title = product_info.get('title', '作品')
            circle_name = product_info.get('circle_name', '作者')
            story_content = f"{title}は{circle_name}によって制作された同人作品です。詳細な内容については、FANZAの商品ページをご確認ください。"
        
        return f"<!-- wp:paragraph -->\n<p>{story_content}</p>\n<!-- /wp:paragraph -->"
    
    def _generate_affiliate_link(self, product_info: Dict[str, Any]) -> str:
        """アフィリエイトリンクを生成"""
        # 既存のaffiliateURLがある場合はそれを使用
        if 'affiliateURL' in product_info and product_info['affiliateURL']:
            affiliate_url = product_info['affiliateURL']
        else:
            # FANZAアフィリエイトIDから動的生成
            affiliate_id = os.getenv('FANZA_AFFILIATE_ID', '')
            product_url = product_info.get('url', '')
            
            if not affiliate_id or not product_url:
                return ""
            
            # FANZAアフィリエイトリンクの生成
            if 'dmm.co.jp' in product_url:
                # 商品IDを抽出
                import re
                product_id_match = re.search(r'/([a-zA-Z0-9_]+)/?(?:\?|$)', product_url)
                if product_id_match:
                    product_id = product_id_match.group(1)
                    affiliate_url = f"https://al.dmm.co.jp/?lurl=https%3A%2F%2Fwww.dmm.co.jp%2Fdc%2Fdoujin%2F-%2Fdetail%2F%3D%2Fcid%3D{product_id}%2F&af_id={affiliate_id}&ch=toolbar&ch_id=link"
                else:
                    # フォールバック：元のURLをアフィリエイト化
                    affiliate_url = f"https://al.dmm.co.jp/?lurl={product_url.replace('https://', 'https%3A%2F%2F').replace('/', '%2F')}&af_id={affiliate_id}&ch=toolbar&ch_id=link"
            else:
                # FANZA以外の場合は元のURLを使用
                affiliate_url = product_url
        
        if not affiliate_url:
            return ""
            
        return (
            "<!-- wp:button -->\n"
            f"<div class='wp-block-button'><a class='wp-block-button__link' href='{affiliate_url}' target='_blank' rel='noopener'>"
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