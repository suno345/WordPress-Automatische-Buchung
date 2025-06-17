import os
from typing import Dict, Any, Optional
from datetime import datetime
import requests
from dotenv import load_dotenv
from ..utils.logger import setup_logger

class WordPress_Poster:
    """WordPressに記事を投稿するクラス"""

    def __init__(self):
        """初期化処理"""
        load_dotenv()
        self.logger = setup_logger(__name__)
        
        # WordPress API設定
        self.wp_url = os.getenv('WP_URL')
        self.wp_username = os.getenv('WP_USERNAME')
        self.wp_password = os.getenv('WP_PASSWORD')
        
        if not all([self.wp_url, self.wp_username, self.wp_password]):
            raise ValueError("WordPress API設定が不足しています")
        
        # APIエンドポイント
        self.posts_endpoint = f"{self.wp_url}/wp-json/wp/v2/posts"
        self.media_endpoint = f"{self.wp_url}/wp-json/wp/v2/media"
        
        # セッション設定
        self.session = requests.Session()
        self.session.auth = (self.wp_username, self.wp_password)

    def post_article(self, article_data: Dict[str, Any]) -> Optional[int]:
        """記事を投稿する
        
        Args:
            article_data: 投稿する記事データ
            
        Returns:
            投稿ID（成功時）、None（失敗時）
        """
        try:
            # 記事データの準備
            post_data = {
                'title': article_data['title'],
                'content': article_data['content'],
                'status': article_data.get('status', 'draft'),
                'categories': self._get_category_ids(article_data.get('categories', [])),
                'tags': self._get_tag_ids(article_data.get('tags', [])),
                'meta': self._prepare_meta_data(article_data)
            }
            
            # 記事の投稿
            response = self.session.post(self.posts_endpoint, json=post_data)
            response.raise_for_status()
            
            # 投稿IDを取得
            post_id = response.json().get('id')
            self.logger.info(f"記事の投稿に成功しました: ID={post_id}")
            
            return post_id
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"記事の投稿に失敗しました: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"予期せぬエラーが発生しました: {str(e)}")
            return None

    def update_article(self, post_id: int, article_data: Dict[str, Any]) -> bool:
        """記事を更新する
        
        Args:
            post_id: 更新する記事のID
            article_data: 更新する記事データ
            
        Returns:
            更新成功時True、失敗時False
        """
        try:
            # 更新データの準備
            update_data = {
                'title': article_data['title'],
                'content': article_data['content'],
                'status': article_data.get('status', 'draft'),
                'categories': self._get_category_ids(article_data.get('categories', [])),
                'tags': self._get_tag_ids(article_data.get('tags', [])),
                'meta': self._prepare_meta_data(article_data)
            }
            
            # 記事の更新
            response = self.session.post(
                f"{self.posts_endpoint}/{post_id}",
                json=update_data
            )
            response.raise_for_status()
            
            self.logger.info(f"記事の更新に成功しました: ID={post_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"記事の更新に失敗しました: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"予期せぬエラーが発生しました: {str(e)}")
            return False

    def delete_article(self, post_id: int) -> bool:
        """記事を削除する
        
        Args:
            post_id: 削除する記事のID
            
        Returns:
            削除成功時True、失敗時False
        """
        try:
            response = self.session.delete(f"{self.posts_endpoint}/{post_id}")
            response.raise_for_status()
            
            self.logger.info(f"記事の削除に成功しました: ID={post_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"記事の削除に失敗しました: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"予期せぬエラーが発生しました: {str(e)}")
            return False

    def upload_media(self, image_url: str) -> Optional[int]:
        """メディアをアップロードする
        
        Args:
            image_url: アップロードする画像のURL
            
        Returns:
            メディアID（成功時）、None（失敗時）
        """
        try:
            # 画像データの取得
            image_response = requests.get(image_url)
            image_response.raise_for_status()
            
            # ファイル名の取得
            filename = image_url.split('/')[-1]
            
            # メディアのアップロード
            files = {
                'file': (filename, image_response.content)
            }
            response = self.session.post(self.media_endpoint, files=files)
            response.raise_for_status()
            
            # メディアIDを取得
            media_id = response.json().get('id')
            self.logger.info(f"メディアのアップロードに成功しました: ID={media_id}")
            
            return media_id
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"メディアのアップロードに失敗しました: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"予期せぬエラーが発生しました: {str(e)}")
            return None

    def _get_category_ids(self, category_names: list) -> list:
        """カテゴリー名からIDを取得する"""
        try:
            response = self.session.get(f"{self.wp_url}/wp-json/wp/v2/categories")
            response.raise_for_status()
            
            categories = response.json()
            category_ids = []
            
            for category in categories:
                if category['name'] in category_names:
                    category_ids.append(category['id'])
            
            return category_ids
            
        except Exception as e:
            self.logger.error(f"カテゴリーIDの取得に失敗しました: {str(e)}")
            return []

    def _get_tag_ids(self, tag_names: list) -> list:
        """タグ名からIDを取得する"""
        try:
            response = self.session.get(f"{self.wp_url}/wp-json/wp/v2/tags")
            response.raise_for_status()
            
            tags = response.json()
            tag_ids = []
            
            for tag in tags:
                if tag['name'] in tag_names:
                    tag_ids.append(tag['id'])
            
            return tag_ids
            
        except Exception as e:
            self.logger.error(f"タグIDの取得に失敗しました: {str(e)}")
            return []

    def _prepare_meta_data(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """メタデータを準備する"""
        meta = {}
        
        # カスタムタクソノミーの設定
        if 'custom_taxonomies' in article_data:
            for taxonomy, value in article_data['custom_taxonomies'].items():
                meta[taxonomy] = value
        
        return meta 