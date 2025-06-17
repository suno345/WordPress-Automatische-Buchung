import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from dotenv import load_dotenv
from ..utils.logger import setup_logger
from ..utils.cache_manager import CacheManager

class WordPress_Article_Generator:
    """WordPress用の記事コンテンツを生成するクラス"""

    def __init__(self):
        """初期化処理"""
        load_dotenv()
        self.logger = setup_logger(__name__)
        self.cache_manager = CacheManager()
        
        # キャッシュ設定
        self.cache_expiry = {
            'article_content': 3600  # 1時間
        }

    def generate_article_content(
        self,
        product_info: Dict[str, Any],
        grok_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """記事コンテンツを生成する
        
        Args:
            product_info: FANZAの商品情報
            grok_result: Grokの分析結果
            
        Returns:
            生成された記事データ
        """
        cache_key = f"article_content_{product_info.get('content_id', '')}"
        
        # キャッシュから取得を試みる
        cached_data = self.cache_manager.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # タイトルの生成
            title = self._generate_title(product_info, grok_result)
            
            # 本文の生成
            content = self._generate_content(product_info, grok_result)
            
            # カテゴリーとタグの設定
            categories = self._get_categories(product_info, grok_result)
            tags = self._get_tags(product_info, grok_result)
            
            # カスタムタクソノミーの設定
            custom_taxonomies = self._get_custom_taxonomies(product_info, grok_result)
            
            # 記事データの生成
            article_data = {
                'title': title,
                'content': content,
                'categories': categories,
                'tags': tags,
                'custom_taxonomies': custom_taxonomies,
                'status': 'draft'  # 下書きとして保存
            }
            
            # キャッシュに保存
            self.cache_manager.set(cache_key, article_data, self.cache_expiry['article_content'])
            
            return article_data
            
        except Exception as e:
            self.logger.error(f"記事生成エラー: {str(e)}")
            return None

    def _generate_title(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> str:
        """記事タイトルを生成する"""
        title = f"【{product_info['title']}】"
        if grok_result.get('character_name'):
            title += f"【{grok_result['character_name']}】"
        return title

    def _generate_content(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> str:
        """記事本文を生成する"""
        content = []
        
        # リード文
        content.append(self._generate_lead(product_info, grok_result))
        
        # 作品情報テーブル
        content.append(self._generate_info_table(product_info, grok_result))
        
        # サンプル画像
        content.append(self._generate_image_gallery(product_info))
        
        # ストーリー/紹介文
        content.append(self._generate_story(product_info, grok_result))
        
        # アフィリエイトリンク
        content.append(self._generate_affiliate_link(product_info))
        
        return "\n\n".join(content)

    def _generate_lead(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> str:
        """リード文を生成する"""
        catchphrase = grok_result.get('catchphrase')
        if catchphrase:
            return f"<p>{catchphrase}</p>"
        else:
            lead = "<p>"
            if grok_result.get('character_name'):
                lead += f"{grok_result['character_name']}が登場する"
            lead += f"{product_info['title']}をご紹介します。</p>"
            return lead

    def _generate_info_table(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> str:
        """作品情報テーブルを生成する"""
        self.logger.info(f"作品情報テーブル生成開始。grok_result: {grok_result}, product_info iteminfo: {product_info.get('iteminfo')}")
        table = ["<table class='wp-block-table'>"]
        table.append("<tbody>")
        
        # サークル名
        circle_name = grok_result.get('circle_name')
        if not circle_name and product_info.get('iteminfo', {}).get('maker'):
            maker_info = product_info['iteminfo']['maker']
            if isinstance(maker_info, list) and maker_info:
                if isinstance(maker_info[0], dict) and 'name' in maker_info[0]:
                    circle_name = maker_info[0]['name']
                elif isinstance(maker_info[0], str):
                    circle_name = maker_info[0]
        if circle_name:
            table.append(f"<tr><th>サークル名</th><td>{circle_name}</td></tr>")
        
        # 作者名
        author_name = grok_result.get('author_name')
        if not author_name and product_info.get('iteminfo', {}).get('author'):
            author_info = product_info['iteminfo']['author']
            if isinstance(author_info, list) and author_info:
                if isinstance(author_info[0], dict) and 'name' in author_info[0]:
                    author_name = author_info[0]['name']
                elif isinstance(author_info[0], str): # 例: "author": ["作者A"]
                    author_name = author_info[0]
        if author_name:
            table.append(f"<tr><th>作者名</th><td>{author_name}</td></tr>")
        
        # 原作名
        original_work = grok_result.get('original_work')
        if not original_work and product_info.get('iteminfo', {}).get('series'):
            series_info = product_info['iteminfo']['series']
            if isinstance(series_info, list) and series_info:
                if isinstance(series_info[0], dict) and 'name' in series_info[0]:
                    original_work = series_info[0]['name']
        if original_work:
            table.append(f"<tr><th>原作名</th><td>{original_work}</td></tr>")
        
        # キャラクター名
        character_name = grok_result.get('character_name')
        if not character_name and product_info.get('iteminfo', {}).get('actress'): # 女優・声優情報からキャラ名を取得するケースを想定
            actress_info = product_info['iteminfo']['actress']
            if isinstance(actress_info, list) and actress_info:
                if isinstance(actress_info[0], dict) and 'name' in actress_info[0]:
                    character_name = actress_info[0]['name']
        if character_name:
            table.append(f"<tr><th>キャラクター名</th><td>{character_name}</td></tr>")

        # 作品形式
        work_type = product_info.get('iteminfo', {}).get('work_type') # 例: "同人音声", "イラスト集" など
        if not work_type: # work_type がない場合、product_format も試す
            work_type = product_info.get('iteminfo', {}).get('product_format')
        if work_type:
            table.append(f"<tr><th>作品形式</th><td>{work_type}</td></tr>")
            
        # ページ数 (既存のものを流用、存在確認を強化)
        volume = product_info.get('volume')
        if volume:
             table.append(f"<tr><th>ページ数</th><td>{volume}</td></tr>")

        table.append("</tbody>")
        table.append("</table>")
        
        return "\n".join(table)

    def _generate_image_gallery(self, product_info: Dict[str, Any]) -> str:
        """画像ギャラリーを生成する"""
        if 'sample_images' not in product_info:
            return ""
        
        gallery = ["<div class='wp-block-gallery'>"]
        for image_url in product_info['sample_images'].get('sample_l', [])[:5]:  # 最大5枚
            gallery.append(f"<figure class='wp-block-image'><img src='{image_url}' alt='サンプル画像'/></figure>")
        gallery.append("</div>")
        
        return "\n".join(gallery)

    def _generate_story(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> str:
        """ストーリー/紹介文を生成する (Grokの要約を使用)"""
        summary = grok_result.get('summary', '')
        if summary:
            return f"<p>{summary}</p>"
        # Grokの要約がない場合は、元の商品説明を使用する（フォールバック）
        elif 'description' in product_info:
            return f"<p>{product_info['description']}</p>"
        return ""

    def _generate_affiliate_link(self, product_info: Dict[str, Any]) -> str:
        """アフィリエイトリンクを生成する"""
        if 'affiliateURL' not in product_info:
            return ""
        
        button_text = "FANZAでこの作品をチェックする" # ボタンのテキスト
        affiliate_url = product_info['affiliateURL']

        return f"""
        <div class="wp-block-swell-button is-style-solid">
            <a class="wp-block-button__link swl-block-button__button" href="{affiliate_url}">
                {button_text}
            </a>
        </div>
        """

    def _get_categories(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> List[str]:
        """カテゴリーを取得する"""
        self.logger.info(f"カテゴリ取得開始。grok_result: {grok_result}, product_info iteminfo: {product_info.get('iteminfo')}")
        categories = ['同人'] # 基本カテゴリ

        # Grokの原作名
        original_work_grok = grok_result.get('original_work')
        if original_work_grok:
            categories.append(original_work_grok)

        # Grokのキャラ名
        character_name_grok = grok_result.get('character_name')
        if character_name_grok:
            categories.append(character_name_grok)

        # FANZAのジャンル情報
        if product_info.get('iteminfo', {}).get('genre'):
            genre_info = product_info['iteminfo']['genre']
            if isinstance(genre_info, list):
                for g in genre_info:
                    if isinstance(g, dict) and 'name' in g and g['name'] not in categories:
                        categories.append(g['name'])
        
        # 作品形式
        work_type = product_info.get('iteminfo', {}).get('work_type') or product_info.get('iteminfo', {}).get('product_format')
        if work_type and work_type not in categories:
            categories.append(work_type)
            
        self.logger.info(f"最終的なカテゴリリスト: {categories}")
        return list(set(categories)) # 重複を削除して返す

    def _get_tags(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> List[str]:
        """タグを取得する"""
        self.logger.info(f"タグ取得開始。grok_result: {grok_result}, product_info iteminfo: {product_info.get('iteminfo')}")
        tags = []
        
        # 作者名
        author_name = grok_result.get('author_name')
        if not author_name and product_info.get('iteminfo', {}).get('author'):
            author_info = product_info['iteminfo']['author']
            if isinstance(author_info, list) and author_info:
                if isinstance(author_info[0], dict) and 'name' in author_info[0]:
                    author_name = author_info[0]['name']
                elif isinstance(author_info[0], str):
                     author_name = author_info[0]
        if author_name:
            tags.append(author_name)
        
        # キャラクター名
        character_name = grok_result.get('character_name')
        if not character_name and product_info.get('iteminfo', {}).get('actress'):
            actress_info = product_info['iteminfo']['actress']
            if isinstance(actress_info, list) and actress_info:
                if isinstance(actress_info[0], dict) and 'name' in actress_info[0]:
                    character_name = actress_info[0]['name']
        if character_name:
            tags.append(character_name)

        # 原作名
        original_work = grok_result.get('original_work')
        if not original_work and product_info.get('iteminfo', {}).get('series'):
            series_info = product_info['iteminfo']['series']
            if isinstance(series_info, list) and series_info:
                if isinstance(series_info[0], dict) and 'name' in series_info[0]:
                    original_work = series_info[0]['name']
        if original_work:
            tags.append(original_work)

        # 作品形式
        work_type = product_info.get('iteminfo', {}).get('work_type') or product_info.get('iteminfo', {}).get('product_format')
        if work_type:
            tags.append(work_type)

        # FANZAのジャンル情報もタグとして追加 (カテゴリと重複する可能性はあるが、タグとしての意味合いも持つため)
        if product_info.get('iteminfo', {}).get('genre'):
            genre_info = product_info['iteminfo']['genre']
            if isinstance(genre_info, list):
                for g in genre_info:
                    if isinstance(g, dict) and 'name' in g:
                        tags.append(g['name'])
        
        self.logger.info(f"最終的なタグリスト: {tags}")
        return list(set(tags)) # 重複を削除

    def _get_custom_taxonomies(
        self,
        product_info: Dict[str, Any],
        grok_result: Dict[str, Any]
    ) -> Dict[str, str]:
        """カスタムタクソノミーを取得する"""
        self.logger.info(f"カスタムタクソノミー取得開始。grok_result: {grok_result}, product_info iteminfo: {product_info.get('iteminfo')}")
        taxonomies = {}
        
        # 原作名 (タクソノミースラッグ: original_work)
        original_work = grok_result.get('original_work')
        if not original_work and product_info.get('iteminfo', {}).get('series'):
            series_info = product_info['iteminfo']['series']
            if isinstance(series_info, list) and series_info:
                if isinstance(series_info[0], dict) and 'name' in series_info[0]:
                    original_work = series_info[0]['name']
        if original_work:
            taxonomies['original_work'] = original_work
        
        # キャラクター名 (タクソノミースラッグ: character_name)
        character_name = grok_result.get('character_name')
        if not character_name and product_info.get('iteminfo', {}).get('actress'):
            actress_info = product_info['iteminfo']['actress']
            if isinstance(actress_info, list) and actress_info:
                if isinstance(actress_info[0], dict) and 'name' in actress_info[0]:
                    character_name = actress_info[0]['name']
        if character_name:
            taxonomies['character_name'] = character_name
        
        # サークル名 (タクソノミースラッグ: circle_name)
        circle_name = grok_result.get('circle_name')
        if not circle_name and product_info.get('iteminfo', {}).get('maker'):
            maker_info = product_info['iteminfo']['maker']
            if isinstance(maker_info, list) and maker_info:
                if isinstance(maker_info[0], dict) and 'name' in maker_info[0]:
                    circle_name = maker_info[0]['name']
                elif isinstance(maker_info[0], str):
                    circle_name = maker_info[0]
        if circle_name:
            taxonomies['circle_name'] = circle_name

        # 作者名 (タクソノミースラッグ: author_name)
        author_name = grok_result.get('author_name')
        if not author_name and product_info.get('iteminfo', {}).get('author'):
            author_info = product_info['iteminfo']['author']
            if isinstance(author_info, list) and author_info:
                if isinstance(author_info[0], dict) and 'name' in author_info[0]:
                    author_name = author_info[0]['name']
                elif isinstance(author_info[0], str):
                    author_name = author_info[0]
        if author_name:
            taxonomies['author_name'] = author_name # カスタムタクソノミーのスラッグを 'author_name' と仮定

        # 作品形式 (タクソノミースラッグ: work_type)
        work_type = product_info.get('iteminfo', {}).get('work_type') or product_info.get('iteminfo', {}).get('product_format')
        if work_type:
            taxonomies['work_type'] = work_type # カスタムタクソノミーのスラッグを 'work_type' と仮定
        
        self.logger.info(f"最終的なカスタムタクソノミー: {taxonomies}")
        return taxonomies 