import os
import json
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from src.utils.logger import Logger
from src.utils.config_manager import ConfigManager
from src.utils.security_manager import SecurityManager

class WordPressPoster:
    """WordPress投稿クラス"""

    def __init__(self, wp_url: str, wp_username: str, wp_password: str):
        self.logger = Logger.get_logger(__name__)
        self.config = ConfigManager()
        self.security = SecurityManager()
        self.wp_url = wp_url
        self.wp_username = wp_username
        self.wp_password = wp_password
        self.api_url = f"{wp_url}/wp-json/wp/v2"
        self.session = requests.Session()
        self.session.auth = (self.wp_username, self.wp_password)

    def create_post(self, title: str, content: str, categories: List[int] = None, tags: List[int] = None, featured_media: int = None, status: str = 'publish') -> Dict[str, Any]:
        """投稿の作成"""
        data = {
            'title': title,
            'content': content,
            'status': status  # publish（公開）またはdraft（下書き）
        }
        if categories:
            data['categories'] = categories
        if tags:
            data['tags'] = tags
        if featured_media:
            data['featured_media'] = featured_media

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
    
    def create_scheduled_post(self, title: str, content: str, scheduled_date: str, categories: List[int] = None, tags: List[int] = None, featured_media: int = None) -> Dict[str, Any]:
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

        response = self.session.post(f"{self.api_url}/posts", json=data)
        response.raise_for_status()
        return response.json()
    
    async def post_article(self, article_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """記事投稿（互換性維持）"""
        try:
            title = article_data.get('title', '')
            content = article_data.get('content', '')
            categories = article_data.get('categories', [])
            tags = article_data.get('tags', [])
            featured_media = article_data.get('featured_media')
            
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
            
            result = self.create_scheduled_post(title, content, scheduled_date, categories, tags, featured_media)
            return {'post_id': result.get('id'), 'url': result.get('link')}
        except Exception as e:
            self.logger.error(f"予約投稿エラー: {str(e)}")
            return None

if __name__ == '__main__':
    # テスト実行
    poster = WordPressPoster('https://your-wordpress-site.com', 'your_username', 'your_password')
    poster.test_media_upload('path/to/image.jpg')
    poster.test_category_creation('Test Category')
    poster.test_tag_creation('Test Tag') 