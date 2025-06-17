import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# API.envを明示的にロード
load_dotenv(dotenv_path="同人WordPress自動投稿/API.env")
WP_URL = os.getenv('WP_URL')
WP_USERNAME = os.getenv('WP_USERNAME')
WP_APP_PASSWORD = os.getenv('WP_APP_PASSWORD')

POSTS_ENDPOINT = WP_URL.rstrip('/') + '/wp-json/wp/v2/posts'

def post_to_wordpress(title: str, content: str, status: str = 'publish', **kwargs) -> str:
    """
    WordPress REST APIで記事を投稿する
    :param title: 投稿タイトル
    :param content: 投稿本文
    :param status: 投稿ステータス（publish, draft など）
    :param kwargs: カスタムフィールド等（辞書）
    :return: 投稿URL
    :raises: Exception（失敗時）
    """
    if not (WP_URL and WP_USERNAME and WP_APP_PASSWORD):
        raise Exception('WordPress API認証情報が不足しています')
    data = {
        'title': title,
        'content': content,
        'status': status
    }
    data.update(kwargs)
    response = requests.post(
        POSTS_ENDPOINT,
        auth=HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD),
        json=data
    )
    if response.status_code not in (200, 201):
        raise Exception(f'WordPress投稿失敗: {response.status_code} {response.text}')
    post_json = response.json()
    return post_json.get('link') 