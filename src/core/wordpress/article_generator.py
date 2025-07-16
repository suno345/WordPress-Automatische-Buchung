"""
WordPress記事生成モジュール
"""
from typing import Dict, Any
import os
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

class WordPressArticleGenerator:
    """WordPress記事生成クラス"""
    
    def __init__(self):
        """初期化"""
        load_dotenv()
        self.logger = None  # ロガーは後で設定
        
        # テンプレートエンジンの初期化
        self.template_env = None
        self._init_template_engine()
        
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
            # カスタムフィールド（meta_input）を生成
            meta_input = self._generate_meta_input(product_info, grok_result)
            
            # スラッグ（商品ID）を生成
            slug = self._generate_slug(product_info)
            
            # 記事データの生成
            article_data = {
                'title': self._generate_title(product_info, grok_result),
                'content': self._generate_content_with_template(product_info, grok_result),
                'status': 'draft',  # 下書きとして保存
                'categories': self._get_categories(product_info),
                'tags': self._get_tags(product_info, grok_result),
                'custom_taxonomies': self._get_custom_taxonomies(product_info, grok_result),
                'meta_input': meta_input,  # カスタムフィールド追加
                'slug': slug  # スラッグ追加
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
        
        # 無料で読める？セクション
        content_parts.append(self._generate_free_reading_section(product_info, grok_result))
        
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
        
        # サークル名（複数フィールド対応）
        circle_name = product_info.get('circle_name', '')
        if not circle_name and 'maker' in product_info:
            if isinstance(product_info['maker'], list) and product_info['maker']:
                circle_name = product_info['maker'][0]['name'] if isinstance(product_info['maker'][0], dict) else product_info['maker'][0]
            elif isinstance(product_info['maker'], str):
                circle_name = product_info['maker']
        if self._is_valid_data(circle_name):
            table.append(f"<tr><td>サークル名</td><td>{circle_name.strip()}</td></tr>")
        
        # 作者名（複数フィールド対応）
        author_name = product_info.get('author_name', '') or product_info.get('author', '')
        if author_name:
            if isinstance(author_name, list) and author_name:
                author_name = author_name[0]['name'] if isinstance(author_name[0], dict) else author_name[0]
            if self._is_valid_data(author_name):
                table.append(f"<tr><td>作者名</td><td>{author_name.strip()}</td></tr>")
        
        # 原作名（複数ソース対応）
        original_work = grok_result.get('original_work', '') or product_info.get('original_work', '')
        if self._is_valid_data(original_work):
            table.append(f"<tr><td>原作名</td><td>{original_work.strip()}</td></tr>")
        
        # キャラクター名（複数ソース対応）
        character_name = grok_result.get('character_name', '') or product_info.get('character_name', '')
        if self._is_valid_data(character_name):
            table.append(f"<tr><td>キャラクター名</td><td>{character_name.strip()}</td></tr>")
        
        # 商品形式（新規追加）
        product_format = product_info.get('product_format', '')
        if self._is_valid_data(product_format):
            table.append(f"<tr><td>形式</td><td>{product_format.strip()}</td></tr>")
        
        # ページ数（新規追加）
        page_count = product_info.get('page_count', '')
        if page_count and str(page_count).strip() and str(page_count).strip() != '0':
            table.append(f"<tr><td>ページ数</td><td>{str(page_count).strip()}</td></tr>")
        
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
    
    def _generate_free_reading_section(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> str:
        """無料で読める？セクションを生成（SEO強化版）"""
        title = product_info.get('title', '')
        character_name = grok_result.get('character_name', '') or product_info.get('character_name', '')
        original_work = grok_result.get('original_work', '') or product_info.get('original_work', '')
        
        # タイトルとキャラクター名の組み合わせ
        if character_name and self._is_valid_data(character_name):
            full_title = f"{title}【{character_name}】"
            seo_keyword = f"{character_name} 同人"
        else:
            full_title = title
            seo_keyword = f"{title} 同人"
        
        # 原作名がある場合はSEOキーワードに追加
        if original_work and self._is_valid_data(original_work):
            seo_keyword = f"{original_work} {seo_keyword}"
        
        section_html = f'''<!-- wp:heading -->
<h2>漫画『{full_title}』は漫甾rawやhitomiで無料で読める？</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>漫甾rawやhitomi、momon:GA（モモンガ）などの海賊版サイトを使えば、{full_title}を全巻無料で読めるかもしれません。しかし、海賊版サイトを利用するのは控えましょう。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>無断転載している違法の海賊版サイトを使うと、{full_title}を全巻無料で読める反面、以下のリスクが生じるからです。</p>
<!-- /wp:paragraph -->

<!-- wp:list -->
<ul>
<li>デバイスの故障</li>
<li>ウイルス感染</li>
<li>個人情報の漏洩</li>
<li>摘発・逮捕</li>
</ul>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p>{full_title}を全巻無料で読めるのは魅力的ですが、違法の海賊版サイトを使うことで、より大きなお金や社会的地位を失う恐れがあります。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>そのため、違法の海賊版サイトを使うのは控えるべきです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>{full_title}を無料で読むなら、合法的に無料配信している電子書籍サイトを利用しましょう。</p>
<!-- /wp:paragraph -->

<!-- wp:heading {{"level":3}} -->
<h3>{seo_keyword} rawで検索しても危険！</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>「{seo_keyword} raw」などで検索して海賊版サイトを探すのは、前述のリスクがあるため大変危険です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>本作品はFANZA公式サイトで正規購入できます。高品質な作品を適正な価格で楽しみ、クリエイターを応援しましょう。</p>
<!-- /wp:paragraph -->'''
        
        return section_html
    
    def _init_template_engine(self):
        """テンプレートエンジンを初期化"""
        try:
            # プロジェクトのルートディレクトリを取得
            project_root = Path(__file__).parent.parent.parent.parent
            template_dir = project_root / "templates"
            
            if template_dir.exists():
                self.template_env = Environment(
                    loader=FileSystemLoader(str(template_dir)),
                    autoescape=select_autoescape(['html', 'xml']),
                    trim_blocks=True,
                    lstrip_blocks=True
                )
                if self.logger:
                    self.logger.info(f"テンプレートディレクトリを初期化: {template_dir}")
            else:
                if self.logger:
                    self.logger.warning(f"テンプレートディレクトリが見つかりません: {template_dir}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"テンプレートエンジン初期化エラー: {str(e)}")
            self.template_env = None
    
    def _load_template(self, template_name: str):
        """テンプレートを読み込み"""
        if not self.template_env:
            return None
        
        try:
            return self.template_env.get_template(template_name)
        except Exception as e:
            if self.logger:
                self.logger.error(f"テンプレート読み込みエラー: {template_name} - {str(e)}")
            return None
    
    def _prepare_template_data(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> Dict[str, Any]:
        """テンプレート用のデータ構造を準備"""
        # キャラクター名と原作名を取得
        character_name = grok_result.get('character_name', '') or product_info.get('character_name', '')
        original_work = grok_result.get('original_work', '') or product_info.get('original_work', '')
        
        # テンプレート用データ構造
        template_data = {
            'product': {
                'title': product_info.get('title', ''),
                'description': product_info.get('description', ''),
                'affiliate_url': product_info.get('affiliateURL', ''),
                'sample_images': self._format_sample_images(product_info),
                'page_count': product_info.get('page_count', '')
            },
            'taxonomies': {
                'custom': {
                    'circle_name': [product_info.get('circle_name', '')] if product_info.get('circle_name') else [],
                    'character_name': [character_name] if character_name and self._is_valid_data(character_name) else [],
                    'original_work': [original_work] if original_work and self._is_valid_data(original_work) else [],
                    'product_format': [product_info.get('product_format', '')] if product_info.get('product_format') else []
                },
                'tags': self._get_tags(product_info, grok_result)
            }
        }
        
        return template_data
    
    def _format_sample_images(self, product_info: Dict[str, Any]) -> list:
        """サンプル画像をテンプレート用にフォーマット"""
        sample_images = product_info.get('sample_images', [])
        
        # 旧形式との互換性
        if not sample_images and 'sampleImageURL' in product_info:
            sample_images = list(product_info['sampleImageURL'].values())
        
        # テンプレート用にフォーマット
        formatted_images = []
        for img_url in sample_images:
            if img_url:  # 空文字列チェック
                formatted_images.append({
                    'url': img_url,
                    'alt': 'サンプル画像'
                })
        
        return formatted_images
    
    def _generate_content_with_template(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> str:
        """テンプレートを使用してコンテンツを生成"""
        template = self._load_template('article.html')
        
        if not template:
            # テンプレートが利用できない場合は既存ロジックを使用
            return self._generate_content_legacy(product_info, grok_result)
        
        try:
            # テンプレート用データを準備
            template_data = self._prepare_template_data(product_info, grok_result)
            
            # テンプレートをレンダリング
            rendered_content = template.render(**template_data)
            
            if self.logger:
                self.logger.info("テンプレートを使用してコンテンツを生成")
            
            return rendered_content
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"テンプレートレンダリングエラー: {str(e)}")
            # エラー時は既存ロジックを使用
            return self._generate_content_legacy(product_info, grok_result)
    
    def _generate_content_legacy(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> str:
        """既存のコンテンツ生成ロジック（フォールバック）"""
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
        
        # 無料で読める？セクション
        content_parts.append(self._generate_free_reading_section(product_info, grok_result))
        
        return '\n\n'.join(content_parts)
    
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
            f"<div class='swell-block-button'><a class='swell-block-button__link' href='{affiliate_url}' target='_blank' rel='noopener'>"
            "FANZAでこの作品をチェックする</a></div>\n"
            "<!-- /wp:button -->"
        )
    
    def _get_categories(self, product_info: Dict[str, Any]) -> list:
        """カテゴリーを取得"""
        categories = []
        
        # 新しいgenresフィールドに対応
        if 'genres' in product_info and product_info['genres']:
            # 有効なジャンルのみ追加
            valid_genres = [g.strip() for g in product_info['genres'] if g and g.strip()]
            categories.extend(valid_genres)
        
        # 従来のgenreフィールドとの互換性維持
        elif 'genre' in product_info and product_info['genre']:
            if isinstance(product_info['genre'], list):
                categories.extend(product_info['genre'])
            else:
                categories.append(product_info['genre'])
        
        # 作品形式もカテゴリに追加
        product_format = product_info.get('product_format', '')
        if product_format and product_format not in categories:
            categories.append(product_format)
        
        # 「不明」関連を完全除去、重複除去、空文字除去
        categories = self._clean_data_list(categories)
        
        # フォールバック：基本カテゴリ（有効なカテゴリが1つもない場合のみ）
        if not categories:
            categories.append('同人作品')
        
        return categories
    
    def _get_tags(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> list:
        """タグを取得"""
        tags = []
        
        # サークル名をタグとして追加
        circle_name = product_info.get('circle_name', '')
        if circle_name and circle_name.strip():
            tags.append(circle_name.strip())
        
        # 作者名をタグとして追加（サークル名と異なる場合のみ）
        author_name = product_info.get('author_name', '') or product_info.get('author', '')
        if author_name:
            if isinstance(author_name, list) and author_name:
                author_name = author_name[0]
            
            if isinstance(author_name, str) and author_name.strip():
                author_name = author_name.strip()
                # サークル名と異なる場合のみ追加
                if author_name != circle_name:
                    tags.append(author_name)
        
        # 「不明」関連を完全除去、重複除去、空文字除去
        tags = self._clean_data_list(tags)
        
        # 商品形式・ページ数はカスタムフィールドで管理（タグには含めない）
        # キャラクター名・原作名もカスタムフィールドで管理（タグには含めない）
        
        return tags
    
    def _get_custom_taxonomies(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> Dict[str, Any]:
        """カスタムタクソノミーを取得"""
        taxonomies = {}
        
        # 原作名（複数ソース対応）
        original_work = grok_result.get('original_work', '') or product_info.get('original_work', '')
        if self._is_valid_data(original_work):
            taxonomies['original_work'] = original_work.strip()
        
        # キャラクター名（複数ソース対応）
        character_name = grok_result.get('character_name', '') or product_info.get('character_name', '')
        if self._is_valid_data(character_name):
            taxonomies['character_name'] = character_name.strip()
        
        # サークル名（複数フィールド対応）
        circle_name = product_info.get('circle_name', '')
        if not circle_name and 'maker' in product_info:
            if isinstance(product_info['maker'], list) and product_info['maker']:
                circle_name = product_info['maker'][0]
            elif isinstance(product_info['maker'], str):
                circle_name = product_info['maker']
        
        if self._is_valid_data(circle_name):
            taxonomies['circle_name'] = circle_name.strip()
        
        # 作者名
        author_name = product_info.get('author_name', '') or product_info.get('author', '')
        if author_name:
            if isinstance(author_name, list) and author_name:
                author_name = author_name[0]
            if isinstance(author_name, str) and self._is_valid_data(author_name):
                taxonomies['author_name'] = author_name.strip()
        
        # 商品形式
        product_format = product_info.get('product_format', '')
        if self._is_valid_data(product_format):
            taxonomies['product_format'] = product_format.strip()
        
        # ページ数
        page_count = product_info.get('page_count', '')
        if page_count and str(page_count).strip() and str(page_count).strip() != '0':
            taxonomies['page_count'] = str(page_count).strip()
        
        return taxonomies 
    
    def _generate_meta_input(self, product_info: Dict[str, Any], grok_result: Dict[str, Any]) -> Dict[str, Any]:
        """カスタムフィールド（meta_input）を生成"""
        meta_input = {}
        
        # 原作名（複数ソース対応）
        original_work = grok_result.get('original_work', '') or product_info.get('original_work', '')
        if self._is_valid_data(original_work):
            meta_input['original_work'] = original_work.strip()
        
        # キャラクター名（複数ソース対応）
        character_name = grok_result.get('character_name', '') or product_info.get('character_name', '')
        if self._is_valid_data(character_name):
            meta_input['character_name'] = character_name.strip()
        
        # サークル名
        circle_name = product_info.get('circle_name', '')
        if not circle_name and 'maker' in product_info:
            if isinstance(product_info['maker'], list) and product_info['maker']:
                circle_name = product_info['maker'][0]
            elif isinstance(product_info['maker'], str):
                circle_name = product_info['maker']
        if self._is_valid_data(circle_name):
            meta_input['circle_name'] = circle_name.strip()
        
        # 作者名
        author_name = product_info.get('author_name', '') or product_info.get('author', '')
        if author_name:
            if isinstance(author_name, list) and author_name:
                author_name = author_name[0]
            if isinstance(author_name, str) and self._is_valid_data(author_name):
                meta_input['author_name'] = author_name.strip()
        
        # 商品形式
        product_format = product_info.get('product_format', '')
        if self._is_valid_data(product_format):
            meta_input['product_format'] = product_format.strip()
        
        # ページ数
        page_count = product_info.get('page_count', '')
        if page_count and str(page_count).strip() and str(page_count).strip() != '0':
            meta_input['page_count'] = str(page_count).strip()
        
        # FANZA商品ID
        product_id = product_info.get('product_id', '')
        if not product_id and 'url' in product_info:
            # URLから商品IDを抽出
            import re
            url = product_info['url']
            match = re.search(r'/([a-zA-Z0-9_]+)/?(?:\?|$)', url)
            if match:
                product_id = match.group(1)
        if self._is_valid_data(product_id):
            meta_input['fanza_product_id'] = product_id.strip()
        
        # AI分析信頼度
        ai_confidence = product_info.get('ai_confidence', 0)
        if ai_confidence and ai_confidence > 0:
            meta_input['ai_confidence'] = str(ai_confidence)
        
        # 分析ソース
        analysis_source = product_info.get('analysis_source', '')
        if self._is_valid_data(analysis_source):
            meta_input['analysis_source'] = analysis_source.strip()
        
        return meta_input
    
    def _generate_slug(self, product_info: Dict[str, Any]) -> str:
        """スラッグ（商品ID）を生成"""
        # 1. 既存のproduct_idを使用
        product_id = product_info.get('product_id', '')
        if product_id and product_id.strip():
            return self._clean_slug(product_id.strip())
        
        # 2. URLから商品IDを抽出
        url = product_info.get('url', '')
        if url:
            import re
            match = re.search(r'/([a-zA-Z0-9_]+)/?(?:\?|$)', url)
            if match:
                extracted_id = match.group(1)
                return self._clean_slug(extracted_id)
        
        # 3. フォールバック：タイトルベース
        title = product_info.get('title', 'product')
        import re
        # 日本語文字、英数字、ハイフンのみ残す
        clean_title = re.sub(r'[^\w\-]', '-', title)
        clean_title = re.sub(r'-+', '-', clean_title)  # 連続ハイフンを1つに
        clean_title = clean_title.strip('-')[:50]  # 最大50文字
        
        return clean_title or 'product'
    
    def _clean_slug(self, slug: str) -> str:
        """スラッグをクリーン化"""
        import re
        # 英数字、ハイフン、アンダースコアのみ許可
        cleaned = re.sub(r'[^a-zA-Z0-9\-_]', '', slug)
        # 先頭末尾のハイフン・アンダースコア除去
        cleaned = cleaned.strip('-_')
        return cleaned or 'product'
    
    def _is_valid_data(self, data: str) -> bool:
        """データが有効かどうかをチェック（「不明」関連を除外）"""
        if not data or not isinstance(data, str):
            return False
        
        data_lower = data.strip().lower()
        
        # 除外する値のリスト
        invalid_values = {
            '', '不明', 'unknown', 'なし', 'none', 'null', '未設定', '未定', 
            '情報なし', 'no data', 'n/a', 'na', '---', '--', '-',
            'tbd', 'to be determined', '後日発表', '詳細不明', '調査中',
            'raw', '不明 raw', 'unknown raw'
        }
        
        return data_lower not in invalid_values
    
    def _clean_data_list(self, data_list: list) -> list:
        """データリストから無効な値を除去し、重複を排除"""
        if not data_list:
            return []
        
        # 有効なデータのみフィルタリング
        valid_data = []
        for item in data_list:
            if isinstance(item, str) and self._is_valid_data(item):
                cleaned_item = item.strip()
                if cleaned_item and cleaned_item not in valid_data:
                    valid_data.append(cleaned_item)
        
        return valid_data