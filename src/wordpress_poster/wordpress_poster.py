import requests
from typing import Dict, List, Optional
from datetime import datetime
from ..config.config_manager import ConfigManager
from ..utils.error_logger import ErrorLogger

class WordPress_Poster:
    """WordPressに記事を投稿するクラス"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.logger = ErrorLogger()
        self.wp_url = self.config.get('WP_URL')
        self.wp_username = self.config.get('WP_USERNAME')
        self.wp_app_password = self.config.get('WP_APP_PASSWORD')
        self.api_url = f"{self.wp_url}/wp-json/wp/v2"
    
    def post_article(
        self,
        article_data: Dict,
        publish_date: Optional[datetime] = None
    ) -> Optional[Dict]:
        """記事をWordPressに投稿する
        
        Args:
            article_data: 記事データの辞書
            publish_date: 公開日時（オプション）
            
        Returns:
            投稿結果の辞書。エラーの場合はNone
        """
        try:
            # 認証情報の設定
            auth = (self.wp_username, self.wp_app_password)
            
            # 投稿データの準備
            post_data = {
                'title': article_data['title'],
                'content': article_data['content'],
                'status': 'draft' if publish_date else 'publish',
                'categories': self._get_category_ids(article_data['categories']),
                'tags': self._get_tag_ids(article_data['tags'])
            }
            
            # 公開日時の設定
            if publish_date:
                post_data['date'] = publish_date.isoformat()
            
            # 記事の投稿
            response = requests.post(
                f"{self.api_url}/posts",
                auth=auth,
                json=post_data
            )
            response.raise_for_status()
            
            post_result = response.json()
            
            # メタディスクリプションの設定
            if 'meta_description' in article_data:
                self._set_meta_description(post_result['id'], article_data['meta_description'])
            
            return post_result
            
        except Exception as e:
            self.logger.log_error(
                str(e),
                'WordPress_Poster',
                'post_article',
                {'title': article_data.get('title', 'unknown')}
            )
            return None
    
    def _get_category_ids(self, category_names: List[str]) -> List[int]:
        """カテゴリー名からカテゴリーIDを取得する
        
        Args:
            category_names: カテゴリー名のリスト
            
        Returns:
            カテゴリーIDのリスト
        """
        try:
            auth = (self.wp_username, self.wp_app_password)
            category_ids = []
            
            for name in category_names:
                # カテゴリーの検索
                response = requests.get(
                    f"{self.api_url}/categories",
                    auth=auth,
                    params={'search': name}
                )
                response.raise_for_status()
                
                categories = response.json()
                if categories:
                    category_ids.append(categories[0]['id'])
                else:
                    # カテゴリーが存在しない場合は新規作成
                    response = requests.post(
                        f"{self.api_url}/categories",
                        auth=auth,
                        json={'name': name}
                    )
                    response.raise_for_status()
                    category_ids.append(response.json()['id'])
            
            return category_ids
            
        except Exception as e:
            self.logger.log_error(
                str(e),
                'WordPress_Poster',
                '_get_category_ids',
                {'category_names': category_names}
            )
            return []
    
    def _get_tag_ids(self, tag_names: List[str]) -> List[int]:
        """タグ名からタグIDを取得する
        
        Args:
            tag_names: タグ名のリスト
            
        Returns:
            タグIDのリスト
        """
        try:
            auth = (self.wp_username, self.wp_app_password)
            tag_ids = []
            
            for name in tag_names:
                # タグの検索
                response = requests.get(
                    f"{self.api_url}/tags",
                    auth=auth,
                    params={'search': name}
                )
                response.raise_for_status()
                
                tags = response.json()
                if tags:
                    tag_ids.append(tags[0]['id'])
                else:
                    # タグが存在しない場合は新規作成
                    response = requests.post(
                        f"{self.api_url}/tags",
                        auth=auth,
                        json={'name': name}
                    )
                    response.raise_for_status()
                    tag_ids.append(response.json()['id'])
            
            return tag_ids
            
        except Exception as e:
            self.logger.log_error(
                str(e),
                'WordPress_Poster',
                '_get_tag_ids',
                {'tag_names': tag_names}
            )
            return []
    
    def _set_meta_description(self, post_id: int, description: str) -> bool:
        """記事のメタディスクリプションを設定する
        
        Args:
            post_id: 記事ID
            description: メタディスクリプション
            
        Returns:
            設定が成功した場合はTrue
        """
        try:
            auth = (self.wp_username, self.wp_app_password)
            
            # メタディスクリプションの設定
            response = requests.post(
                f"{self.api_url}/posts/{post_id}/meta",
                auth=auth,
                json={
                    'key': '_yoast_wpseo_metadesc',
                    'value': description
                }
            )
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            self.logger.log_error(
                str(e),
                'WordPress_Poster',
                '_set_meta_description',
                {'post_id': post_id}
            )
            return False 