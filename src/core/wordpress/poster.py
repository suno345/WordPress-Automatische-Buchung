import os
import json
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from src.utils.logger import get_logger
from src.utils.config_manager import ConfigManager

class WordPressPoster:
    """WordPress投稿クラス"""

    def __init__(self, wp_url: str, wp_username: str, wp_password: str):
        self.logger = get_logger(__name__)
        self.config = ConfigManager()
        # URLの末尾のスラッシュを除去
        self.wp_url = wp_url.rstrip('/')
        self.wp_username = wp_username
        self.wp_password = wp_password
        self.api_url = f"{self.wp_url}/wp-json/wp/v2"
        self.session = requests.Session()
        self.session.auth = (self.wp_username, self.wp_password)

    def create_post(self, title: str, content: str, categories: List[int] = None, tags: List[int] = None, featured_media: int = None, status: str = 'publish', date: str = None, meta_input: Dict[str, Any] = None, slug: str = None, custom_taxonomies: Dict[str, Any] = None) -> Dict[str, Any]:
        """投稿の作成"""
        # カテゴリとタグが文字列のリストの場合、IDに変換
        if categories and isinstance(categories, list) and len(categories) > 0 and isinstance(categories[0], str):
            categories = self.convert_categories_to_ids(categories)
        if tags and isinstance(tags, list) and len(tags) > 0 and isinstance(tags[0], str):
            tags = self.convert_tags_to_ids(tags)
        
        data = {
            'title': title,
            'content': content,
            'status': status  # publish（公開）またはdraft（下書き）またはfuture（予約投稿）
        }
        if categories:
            data['categories'] = categories
        if tags:
            data['tags'] = tags
        if featured_media:
            data['featured_media'] = featured_media
        if date and status == 'future':
            # 予約投稿の場合は日時を設定
            data['date'] = date
            data['date_gmt'] = date  # GMT時間も設定
        if meta_input:
            # カスタムフィールド（メタデータ）を設定
            data['meta'] = meta_input
        if slug:
            # スラッグ（URL末尾）を設定
            data['slug'] = slug
        if custom_taxonomies:
            # カスタムタクソノミーをIDに変換して設定
            converted_taxonomies = self.convert_custom_taxonomies_to_ids(custom_taxonomies)
            for taxonomy_name, taxonomy_ids in converted_taxonomies.items():
                data[taxonomy_name] = taxonomy_ids

        response = self.session.post(f"{self.api_url}/posts", json=data)
        response.raise_for_status()
        return response.json()

    def upload_media(self, file_path: str) -> Dict[str, Any]:
        """メディアのアップロード"""
        if not os.path.exists(file_path):
            self.logger.error(f"ファイルが存在しません: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = self.session.post(f"{self.api_url}/media", files=files)
            response.raise_for_status()
            return response.json()

    def attach_gallery_images(self, post_id: int, image_paths: List[str]) -> None:
        """ギャラリー画像の添付"""
        media_ids = []
        for image_path in image_paths:
            media = self.upload_media(image_path)
            media_ids.append(media['id'])

        gallery_shortcode = f'[gallery ids="{",".join(map(str, media_ids))}"]'
        post = self.session.get(f"{self.api_url}/posts/{post_id}").json()
        content = post['content']['rendered'] + gallery_shortcode

        self.session.post(
            f"{self.api_url}/posts/{post_id}",
            json={'content': content}
        )

    def create_category(self, name: str, description: str = '') -> Dict[str, Any]:
        """カテゴリの作成"""
        data = {
            'name': name,
            'description': description
        }
        response = self.session.post(f"{self.api_url}/categories", json=data)
        response.raise_for_status()
        return response.json()

    def create_tag(self, name: str, description: str = '') -> Dict[str, Any]:
        """タグの作成"""
        data = {
            'name': name,
            'description': description
        }
        response = self.session.post(f"{self.api_url}/tags", json=data)
        response.raise_for_status()
        return response.json()

    def get_category_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """名前でカテゴリを取得"""
        response = self.session.get(f"{self.api_url}/categories", params={'search': name})
        response.raise_for_status()
        categories = response.json()
        return next((cat for cat in categories if cat['name'] == name), None)

    def get_tag_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """名前でタグを取得"""
        response = self.session.get(f"{self.api_url}/tags", params={'search': name})
        response.raise_for_status()
        tags = response.json()
        return next((tag for tag in tags if tag['name'] == name), None)

    def ensure_category_exists(self, name: str, description: str = '') -> Dict[str, Any]:
        """カテゴリの存在確認と作成"""
        category = self.get_category_by_name(name)
        if not category:
            category = self.create_category(name, description)
        return category

    def ensure_tag_exists(self, name: str, description: str = '') -> Dict[str, Any]:
        """タグの存在確認と作成"""
        tag = self.get_tag_by_name(name)
        if not tag:
            tag = self.create_tag(name, description)
        return tag
    
    def convert_tags_to_ids(self, tag_names: List[str]) -> List[int]:
        """タグ名のリストをIDのリストに変換"""
        tag_ids = []
        for tag_name in tag_names:
            if isinstance(tag_name, str) and tag_name.strip():
                try:
                    tag = self.ensure_tag_exists(tag_name.strip())
                    if tag and 'id' in tag:
                        tag_ids.append(tag['id'])
                        self.logger.debug(f"タグ変換: '{tag_name}' -> ID {tag['id']}")
                except Exception as e:
                    self.logger.warning(f"タグ変換失敗: {tag_name} - {str(e)}")
        return tag_ids
    
    def convert_categories_to_ids(self, category_names: List[str]) -> List[int]:
        """カテゴリ名のリストをIDのリストに変換"""
        category_ids = []
        for category_name in category_names:
            if isinstance(category_name, str) and category_name.strip():
                try:
                    category = self.ensure_category_exists(category_name.strip())
                    if category and 'id' in category:
                        category_ids.append(category['id'])
                        self.logger.debug(f"カテゴリ変換: '{category_name}' -> ID {category['id']}")
                except Exception as e:
                    self.logger.warning(f"カテゴリ変換失敗: {category_name} - {str(e)}")
        return category_ids
    
    def get_custom_taxonomy_term(self, taxonomy: str, term_name: str) -> Optional[Dict[str, Any]]:
        """カスタムタクソノミーのタームを取得"""
        try:
            response = self.session.get(f"{self.api_url}/{taxonomy}", params={'search': term_name})
            response.raise_for_status()
            terms = response.json()
            return next((term for term in terms if term['name'] == term_name), None)
        except Exception as e:
            self.logger.error(f"カスタムタクソノミー取得エラー ({taxonomy}/{term_name}): {str(e)}")
            return None
    
    def create_custom_taxonomy_term(self, taxonomy: str, term_name: str) -> Optional[Dict[str, Any]]:
        """カスタムタクソノミーのタームを作成"""
        try:
            data = {'name': term_name}
            response = self.session.post(f"{self.api_url}/{taxonomy}", json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"カスタムタクソノミー作成エラー ({taxonomy}/{term_name}): {str(e)}")
            return None
    
    def ensure_custom_taxonomy_exists(self, taxonomy: str, term_name: str) -> Optional[Dict[str, Any]]:
        """カスタムタクソノミーのタームの存在確認と作成"""
        term = self.get_custom_taxonomy_term(taxonomy, term_name)
        if not term:
            term = self.create_custom_taxonomy_term(taxonomy, term_name)
        return term
    
    def convert_custom_taxonomies_to_ids(self, custom_taxonomies: Dict[str, str]) -> Dict[str, List[int]]:
        """カスタムタクソノミーの値をIDに変換"""
        converted = {}
        for taxonomy_name, taxonomy_value in custom_taxonomies.items():
            if taxonomy_value and isinstance(taxonomy_value, str):
                try:
                    term = self.ensure_custom_taxonomy_exists(taxonomy_name, taxonomy_value.strip())
                    if term and 'id' in term:
                        converted[taxonomy_name] = [term['id']]
                        self.logger.debug(f"カスタムタクソノミー変換: {taxonomy_name} '{taxonomy_value}' -> ID {term['id']}")
                except Exception as e:
                    self.logger.warning(f"カスタムタクソノミー変換失敗 ({taxonomy_name}/{taxonomy_value}): {str(e)}")
        return converted

    def test_media_upload(self, file_path: str) -> Dict[str, Any]:
        """メディアアップロードのテスト"""
        return self.upload_media(file_path)

    def test_category_creation(self, name: str) -> Dict[str, Any]:
        """カテゴリ作成のテスト"""
        return self.ensure_category_exists(name)

    def test_tag_creation(self, name: str) -> Dict[str, Any]:
        """タグ作成のテスト"""
        return self.ensure_tag_exists(name)
    
    def create_draft(self, title: str, content: str, categories: List[int] = None, tags: List[int] = None, featured_media: int = None) -> Dict[str, Any]:
        """下書きの作成"""
        return self.create_post(title, content, categories, tags, featured_media, status='draft')
    
    def create_scheduled_post(self, title: str, content: str, scheduled_date: str, categories: List[int] = None, tags: List[int] = None, featured_media: int = None, meta_input: Dict[str, Any] = None, slug: str = None, custom_taxonomies: Dict[str, Any] = None) -> Dict[str, Any]:
        """予約投稿の作成"""
        data = {
            'title': title,
            'content': content,
            'status': 'future',  # 予約投稿ステータス
            'date': scheduled_date  # ISO形式の日時
        }
        if categories:
            data['categories'] = categories
        if tags:
            data['tags'] = tags
        if featured_media:
            data['featured_media'] = featured_media
        if meta_input:
            data['meta'] = meta_input
        if slug:
            data['slug'] = slug
        if custom_taxonomies:
            # カスタムタクソノミーをIDに変換して設定
            converted_taxonomies = self.convert_custom_taxonomies_to_ids(custom_taxonomies)
            for taxonomy_name, taxonomy_ids in converted_taxonomies.items():
                data[taxonomy_name] = taxonomy_ids

        try:
            self.logger.debug(f"WordPress予約投稿リクエスト - URL: {self.api_url}/posts")
            self.logger.debug(f"投稿データ: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            response = self.session.post(f"{self.api_url}/posts", json=data)
            self.logger.debug(f"WordPressレスポンス ステータス: {response.status_code}")
            
            if response.status_code != 201:
                error_detail = response.text
                self.logger.error(f"WordPress投稿エラー - ステータス: {response.status_code}, 詳細: {error_detail}")
                
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"WordPress予約投稿例外: {str(e)}")
            raise
    
    async def post_article(self, article_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """記事投稿（互換性維持）"""
        try:
            title = article_data.get('title', '')
            content = article_data.get('content', '')
            categories = article_data.get('categories', [])
            tags = article_data.get('tags', [])
            featured_media = article_data.get('featured_media')
            
            # タグ・カテゴリをIDに変換
            if categories and isinstance(categories[0], str):
                categories = self.convert_categories_to_ids(categories)
            if tags and isinstance(tags[0], str):
                tags = self.convert_tags_to_ids(tags)
            
            result = self.create_post(title, content, categories, tags, featured_media)
            return {'post_id': result.get('id'), 'url': result.get('link')}
        except Exception as e:
            self.logger.error(f"記事投稿エラー: {str(e)}")
            return None
    
    async def post_draft(self, article_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """下書き投稿（互換性維持）"""
        try:
            title = article_data.get('title', '')
            content = article_data.get('content', '')
            categories = article_data.get('categories', [])
            tags = article_data.get('tags', [])
            featured_media = article_data.get('featured_media')
            
            # タグ・カテゴリをIDに変換
            if categories and isinstance(categories[0], str):
                categories = self.convert_categories_to_ids(categories)
            if tags and isinstance(tags[0], str):
                tags = self.convert_tags_to_ids(tags)
            
            result = self.create_draft(title, content, categories, tags, featured_media)
            return {'post_id': result.get('id'), 'url': result.get('link')}
        except Exception as e:
            self.logger.error(f"下書き投稿エラー: {str(e)}")
            return None
    
    async def post_scheduled_article(self, article_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """予約投稿（互換性維持）"""
        try:
            title = article_data.get('title', '')
            content = article_data.get('content', '')
            scheduled_date = article_data.get('scheduled_date', '')
            categories = article_data.get('categories', [])
            tags = article_data.get('tags', [])
            featured_media = article_data.get('featured_media')
            meta_input = article_data.get('meta_input', {})  # カスタムフィールド追加
            slug = article_data.get('slug', '')  # スラッグ追加
            custom_taxonomies = article_data.get('custom_taxonomies', {})  # カスタムタクソノミー追加
            
            # タグ・カテゴリをIDに変換
            if categories and len(categories) > 0 and isinstance(categories[0], str):
                categories = self.convert_categories_to_ids(categories)
            if tags and len(tags) > 0 and isinstance(tags[0], str):
                tags = self.convert_tags_to_ids(tags)
            
            result = self.create_scheduled_post(title, content, scheduled_date, categories, tags, featured_media, meta_input, slug, custom_taxonomies)
            return {'post_id': result.get('id'), 'url': result.get('link')}
        except Exception as e:
            self.logger.error(f"予約投稿エラー: {str(e)}")
            return None
    
    def get_last_scheduled_post_time(self) -> Optional[datetime]:
        """最後の予約投稿の時間を取得"""
        try:
            # 予約投稿（future）ステータスの投稿を取得
            response = self.session.get(
                f"{self.api_url}/posts",
                params={
                    'status': 'future',
                    'orderby': 'date',
                    'order': 'desc',
                    'per_page': 1
                }
            )
            response.raise_for_status()
            posts = response.json()
            
            if posts:
                # WordPressの日時文字列をdatetimeオブジェクトに変換
                date_str = posts[0].get('date_gmt', posts[0].get('date'))
                if date_str:
                    # ISO 8601形式の日時をパース
                    from datetime import datetime
                    return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
            
            return None
            
        except Exception as e:
            self.logger.error(f"予約投稿時間取得エラー: {str(e)}")
            return None

if __name__ == '__main__':
    # テスト実行
    poster = WordPressPoster('https://your-wordpress-site.com', 'your_username', 'your_password')
    poster.test_media_upload('path/to/image.jpg')
    poster.test_category_creation('Test Category')
    poster.test_tag_creation('Test Tag') 