"""
WordPress投稿モジュール
"""
from typing import Dict, Any, Optional, List
import os
import aiohttp
from dotenv import load_dotenv
import base64
import json
from datetime import datetime

class WordPress_Poster:
    """WordPress投稿クラス"""
    
    def __init__(self, api_url, username, app_password):
        """初期化"""
        self.api_url = api_url
        self.username = username
        self.app_password = app_password
        self.auth_token = base64.b64encode(f"{username}:{app_password}".encode()).decode()
        
        # WordPress APIの設定（URLの正規化）
        self.wp_url = api_url.rstrip('/')  # 末尾のスラッシュを除去
        self.wp_username = username
        self.wp_password = app_password
        
        if not all([self.wp_url, self.wp_username, self.wp_password]):
            raise ValueError("WordPress APIの認証情報が設定されていません")
        
        # APIエンドポイント
        self.posts_endpoint = f"{self.wp_url}/wp-json/wp/v2/posts"
        self.media_endpoint = f"{self.wp_url}/wp-json/wp/v2/media"
        
        # セッションの設定
        self.session = None
    
    async def __aenter__(self):
        """非同期コンテキストマネージャーのエントリー"""
        self.session = aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self.wp_username, self.wp_password)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャーのエグジット"""
        if self.session:
            await self.session.close()
    
    async def post_article(self, article_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        記事を投稿する
        
        Args:
            article_data (Dict[str, Any]): 記事データ
            
        Returns:
            Optional[Dict[str, Any]]: 投稿結果
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    auth=aiohttp.BasicAuth(self.wp_username, self.wp_password)
                )
            
            # カテゴリーIDの取得
            category_ids = await self._get_category_ids(article_data.get('categories', []))
            
            # タグIDの取得
            tag_ids = await self._get_tag_ids(article_data.get('tags', []))
            
            # 投稿データの準備
            post_data = {
                'title': article_data['title'],
                'content': article_data['content'],
                'status': article_data.get('status', 'draft'),
                'categories': category_ids,
                'tags': tag_ids,
                'meta': self._prepare_meta_data(article_data)
            }
            
            # 記事の投稿
            async with self.session.post(self.posts_endpoint, json=post_data) as response:
                if response.status == 201:
                    post = await response.json()
                    return {
                        'post_id': post['id'],
                        'post_url': post['link']
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"記事の投稿に失敗: {error_text}")
                
        except Exception as e:
            raise Exception(f"記事の投稿中にエラーが発生: {str(e)}")
    
    async def update_article(self, post_id: int, article_data: Dict[str, Any]) -> bool:
        """
        記事を更新する
        
        Args:
            post_id (int): 記事ID
            article_data (Dict[str, Any]): 更新データ
            
        Returns:
            bool: 更新の成功/失敗
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    auth=aiohttp.BasicAuth(self.wp_username, self.wp_password)
                )
            
            # カテゴリーIDの取得
            category_ids = await self._get_category_ids(article_data.get('categories', []))
            
            # タグIDの取得
            tag_ids = await self._get_tag_ids(article_data.get('tags', []))
            
            # 更新データの準備
            update_data = {
                'title': article_data['title'],
                'content': article_data['content'],
                'categories': category_ids,
                'tags': tag_ids,
                'meta': self._prepare_meta_data(article_data)
            }
            
            # 記事の更新
            async with self.session.post(
                f"{self.posts_endpoint}/{post_id}",
                json=update_data
            ) as response:
                return response.status == 200
                
        except Exception as e:
            raise Exception(f"記事の更新中にエラーが発生: {str(e)}")
    
    async def delete_article(self, post_id: int) -> bool:
        """
        記事を削除する
        
        Args:
            post_id (int): 記事ID
            
        Returns:
            bool: 削除の成功/失敗
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    auth=aiohttp.BasicAuth(self.wp_username, self.wp_password)
                )
            
            # 記事の削除
            async with self.session.delete(f"{self.posts_endpoint}/{post_id}") as response:
                return response.status == 200
                
        except Exception as e:
            raise Exception(f"記事の削除中にエラーが発生: {str(e)}")
    
    async def upload_media(self, file_path: str) -> Optional[int]:
        """
        メディアをアップロードする
        
        Args:
            file_path (str): ファイルパス
            
        Returns:
            Optional[int]: メディアID
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    auth=aiohttp.BasicAuth(self.wp_username, self.wp_password)
                )
            
            # ファイルの読み込み
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # メディアのアップロード
            data = aiohttp.FormData()
            data.add_field(
                'file',
                file_data,
                filename=os.path.basename(file_path)
            )
            
            async with self.session.post(self.media_endpoint, data=data) as response:
                if response.status == 201:
                    media = await response.json()
                    return media['id']
                else:
                    error_text = await response.text()
                    raise Exception(f"メディアのアップロードに失敗: {error_text}")
                
        except Exception as e:
            raise Exception(f"メディアのアップロード中にエラーが発生: {str(e)}")

    async def upload_media_from_url(self, image_url: str, filename: str = None) -> Optional[int]:
        """
        URLから画像をダウンロードしてWordPressにアップロードする
        
        Args:
            image_url (str): 画像のURL
            filename (str): ファイル名（省略時はURLから自動生成）
            
        Returns:
            Optional[int]: メディアID
        """
        try:
            # ファイル名の生成
            if not filename:
                import urllib.parse
                parsed_url = urllib.parse.urlparse(image_url)
                filename = os.path.basename(parsed_url.path)
                if not filename or '.' not in filename:
                    filename = f"featured_image_{hash(image_url) % 10000}.jpg"
            
            print(f"Debug: 画像ダウンロード開始 - URL: {image_url}")
            
            # 画像をダウンロード
            async with aiohttp.ClientSession() as download_session:
                async with download_session.get(image_url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        print(f"Debug: 画像ダウンロード成功 - サイズ: {len(image_data)} bytes")
                    else:
                        print(f"Error: 画像ダウンロード失敗 - Status: {response.status}")
                        return None
            
            # WordPressにアップロード
            headers = {
                "Authorization": f"Basic {self.auth_token}",
            }
            
            data = aiohttp.FormData()
            data.add_field(
                'file',
                image_data,
                filename=filename,
                content_type='image/jpeg'
            )
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.media_endpoint, headers=headers, data=data) as response:
                    if response.status == 201:
                        media = await response.json()
                        print(f"Debug: メディアアップロード成功 - ID: {media['id']}, URL: {media.get('source_url', '')}")
                        return media['id']
                    else:
                        error_text = await response.text()
                        print(f"Error: メディアアップロード失敗 - Status: {response.status}")
                        print(f"Error: Response: {error_text}")
                        return None
                        
        except Exception as e:
            print(f"Error: URLからのメディアアップロード中にエラー: {str(e)}")
            return None

    async def verify_and_set_featured_image(self, post_id: int, media_id: int) -> bool:
        """
        投稿のアイキャッチ画像を確認し、設定されていない場合は設定する
        
        Args:
            post_id (int): 投稿ID
            media_id (int): メディアID
            
        Returns:
            bool: 設定の成功/失敗
        """
        try:
            headers = {
                "Authorization": f"Basic {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            # まず投稿の現在の状態を確認
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.posts_endpoint}/{post_id}", headers=headers) as response:
                    if response.status == 200:
                        post_data = await response.json()
                        current_featured_media = post_data.get('featured_media', 0)
                        
                        if current_featured_media == media_id:
                            print(f"✅ アイキャッチ画像は既に正しく設定されています - Post ID: {post_id}, Media ID: {media_id}")
                            return True
                        else:
                            print(f"⚠️  アイキャッチ画像が未設定または異なります - 現在: {current_featured_media}, 期待: {media_id}")
                    else:
                        print(f"❌ 投稿の確認に失敗 - Status: {response.status}")
                
                # アイキャッチ画像を設定
                return await self.set_featured_image(post_id, media_id)
                
        except Exception as e:
            print(f"❌ アイキャッチ画像確認・設定中にエラー: {str(e)}")
            return False

    async def set_featured_image(self, post_id: int, media_id: int) -> bool:
        """
        投稿にアイキャッチ画像を設定する（複数の方法を試行）
        
        Args:
            post_id (int): 投稿ID
            media_id (int): メディアID
            
        Returns:
            bool: 設定の成功/失敗
        """
        try:
            headers = {
                "Authorization": f"Basic {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                # 方法1: PUTメソッドでfeatured_mediaを設定
                print(f"🔄 方法1: PUTメソッドでアイキャッチ画像を設定中...")
                update_data = {"featured_media": media_id}
                
                async with session.put(f"{self.posts_endpoint}/{post_id}", headers=headers, json=update_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('featured_media') == media_id:
                            print(f"✅ アイキャッチ画像設定成功（PUT） - Post ID: {post_id}, Media ID: {media_id}")
                            return True
                        else:
                            print(f"⚠️  PUTレスポンスでfeatured_mediaが一致しません - 期待: {media_id}, 実際: {result.get('featured_media')}")
                    else:
                        error_text = await response.text()
                        print(f"❌ PUT方法失敗 - Status: {response.status}: {error_text}")
                
                # 方法2: POSTメソッドでfeatured_mediaを設定
                print(f"🔄 方法2: POSTメソッドでアイキャッチ画像を設定中...")
                async with session.post(f"{self.posts_endpoint}/{post_id}", headers=headers, json=update_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('featured_media') == media_id:
                            print(f"✅ アイキャッチ画像設定成功（POST） - Post ID: {post_id}, Media ID: {media_id}")
                            return True
                        else:
                            print(f"⚠️  POSTレスポンスでfeatured_mediaが一致しません - 期待: {media_id}, 実際: {result.get('featured_media')}")
                    else:
                        error_text = await response.text()
                        print(f"❌ POST方法失敗 - Status: {response.status}: {error_text}")
                
                # 方法3: メタデータ経由で_thumbnail_idを設定
                print(f"🔄 方法3: メタデータ経由でアイキャッチ画像を設定中...")
                meta_data = {
                    "meta": {
                        "_thumbnail_id": str(media_id)
                    }
                }
                
                async with session.post(f"{self.posts_endpoint}/{post_id}", headers=headers, json=meta_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        print(f"✅ メタデータ経由でアイキャッチ画像設定完了 - Post ID: {post_id}, Media ID: {media_id}")
                        
                        # 設定確認
                        async with session.get(f"{self.posts_endpoint}/{post_id}", headers=headers) as check_response:
                            if check_response.status == 200:
                                check_result = await check_response.json()
                                final_featured_media = check_result.get('featured_media', 0)
                                if final_featured_media == media_id:
                                    print(f"✅ アイキャッチ画像設定確認完了 - Featured Media: {final_featured_media}")
                                    return True
                                else:
                                    print(f"⚠️  最終確認でfeatured_mediaが一致しません - 期待: {media_id}, 実際: {final_featured_media}")
                    else:
                        error_text = await response.text()
                        print(f"❌ メタデータ方法失敗 - Status: {response.status}: {error_text}")
                
                print(f"❌ すべての方法でアイキャッチ画像設定に失敗しました")
                return False
                        
        except Exception as e:
            print(f"❌ アイキャッチ画像設定中にエラー: {str(e)}")
            return False
    
    async def _get_or_create_term(self, taxonomy: str, term_name: str) -> Optional[int]:
        """
        タクソノミーのタームを取得または作成する
        
        Args:
            taxonomy (str): タクソノミー名（categories, tags, original_work, character_name, product_format）
            term_name (str): ターム名
            
        Returns:
            Optional[int]: タームID。失敗時はNone
        """
        if not term_name.strip():
            return None
            
        headers = {
            "Authorization": f"Basic {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # タクソノミーのエンドポイントを決定
                if taxonomy == 'categories':
                    endpoint = f"{self.wp_url}/wp-json/wp/v2/categories"
                elif taxonomy == 'tags':
                    endpoint = f"{self.wp_url}/wp-json/wp/v2/tags"
                else:
                    # カスタムタクソノミーの場合
                    endpoint = f"{self.wp_url}/wp-json/wp/v2/{taxonomy}"
                
                # 既存のタームを検索
                search_params = {"search": term_name, "per_page": 100}
                print(f"Debug: タクソノミー検索 - Endpoint: {endpoint}, Term: {term_name}")
                
                async with session.get(endpoint, params=search_params, headers=headers) as response:
                    if response.status == 200:
                        terms = await response.json()
                        # 完全一致するタームを探す
                        for term in terms:
                            if term.get('name', '').lower() == term_name.lower():
                                print(f"Debug: 既存ターム発見 - {taxonomy}: {term_name} (ID: {term['id']})")
                                return term['id']
                    elif response.status == 404:
                        # カスタムタクソノミーが存在しない場合
                        print(f"Warning: カスタムタクソノミー '{taxonomy}' が存在しません。WordPressでタクソノミーを作成してください。")
                        return None
                
                # タームが見つからない場合は新規作成
                create_data = {"name": term_name}
                async with session.post(endpoint, headers=headers, json=create_data) as response:
                    if response.status == 201:
                        new_term = await response.json()
                        print(f"Debug: 新規ターム作成 - {taxonomy}: {term_name} (ID: {new_term['id']})")
                        return new_term['id']
                    else:
                        error_text = await response.text()
                        print(f"Error: ターム作成失敗 - {taxonomy}: {term_name}")
                        print(f"Error: Status {response.status}: {error_text}")
                        return None
                        
        except Exception as e:
            print(f"Error in _get_or_create_term for {taxonomy} '{term_name}': {str(e)}")
            return None

    async def _get_category_ids(self, category_names: List[str]) -> List[int]:
        """カテゴリー名からIDリストを取得"""
        category_ids = []
        for name in category_names:
            if name.strip():
                term_id = await self._get_or_create_term('categories', name.strip())
                if term_id:
                    category_ids.append(term_id)
        return category_ids

    async def _get_tag_ids(self, tag_names: List[str]) -> List[int]:
        """タグ名からIDリストを取得"""
        tag_ids = []
        for name in tag_names:
            if name.strip():
                term_id = await self._get_or_create_term('tags', name.strip())
                if term_id:
                    tag_ids.append(term_id)
        return tag_ids
    
    def _prepare_meta_data(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """メタデータを準備"""
        meta_data = {}
        
        # カスタムタクソノミーの追加
        if 'custom_taxonomies' in article_data:
            for taxonomy, value in article_data['custom_taxonomies'].items():
                meta_data[f'custom_{taxonomy}'] = value
        
        return meta_data

    async def create_post(self, post_data):
        """
        WordPressに投稿を作成する
        
        Args:
            post_data (dict): 投稿データ
            
        Returns:
            dict: 投稿レスポンス。失敗時はNone
        """
        headers = {
            "Authorization": f"Basic {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        try:
            # カテゴリーとタグのIDを取得
            category_ids = await self._get_category_ids(post_data.get('categories', []))
            tag_ids = await self._get_tag_ids(post_data.get('tags', []))
            
            # カスタムタクソノミーの処理
            custom_taxonomies = post_data.get('custom_taxonomies', {})
            taxonomy_data = {}
            
            # 原作名のタクソノミー処理
            if custom_taxonomies.get('original_work'):
                original_work_id = await self._get_or_create_term('original_work', custom_taxonomies['original_work'])
                if original_work_id:
                    taxonomy_data['original_work'] = [original_work_id]
            
            # キャラクター名のタクソノミー処理
            if custom_taxonomies.get('character_name'):
                character_id = await self._get_or_create_term('character_name', custom_taxonomies['character_name'])
                if character_id:
                    taxonomy_data['character_name'] = [character_id]
            
            # 作品形式のタクソノミー処理
            if custom_taxonomies.get('product_format'):
                format_id = await self._get_or_create_term('product_format', custom_taxonomies['product_format'])
                if format_id:
                    taxonomy_data['product_format'] = [format_id]
            
            # 投稿データの準備（カスタムタクソノミーは投稿作成後に別途設定）
            wp_post_data = {
                "title": post_data.get('title', ''),
                "content": post_data.get('content', ''),
                "status": post_data.get('status', 'draft'),
                "excerpt": post_data.get('excerpt', ''),
                "categories": category_ids,
                "tags": tag_ids
                # カスタムタクソノミーは投稿作成後に別途設定するため、ここでは含めない
            }
            
            # スラッグが指定されている場合は追加
            if post_data.get('slug'):
                wp_post_data["slug"] = post_data.get('slug')
                print(f"🔗 スラッグを設定: {post_data.get('slug')}")
            
            # 日時が指定されている場合のみ追加
            if post_data.get('date'):
                wp_post_data["date"] = post_data.get('date')
            
            # アイキャッチ画像IDが指定されている場合は投稿作成時に設定
            if post_data.get('featured_media_id'):
                featured_media_id = post_data.get('featured_media_id')
                wp_post_data["featured_media"] = featured_media_id
                print(f"🖼️  投稿作成時にアイキャッチ画像を設定 - Media ID: {featured_media_id}")
                
                # メタデータでもアイキャッチ画像を設定（WordPress管理画面での表示確保）
                wp_post_data["meta"] = {
                    "_thumbnail_id": str(featured_media_id),
                    "_wp_attachment_metadata": "",  # WordPressの内部処理用
                }
                
                print(f"🔧 メタデータにも_thumbnail_idを設定: {featured_media_id}")
            
            print(f"Debug: WordPress投稿データ準備完了")
            print(f"Debug: Categories: {category_ids}")
            print(f"Debug: Tags: {tag_ids}")
            print(f"Debug: Custom Taxonomies (投稿作成後に設定): {post_data.get('custom_taxonomies', {})}")
            print(f"Debug: 投稿データ: {wp_post_data}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.posts_endpoint, headers=headers, json=wp_post_data) as response:
                    if response.status in [200, 201]:
                        result = await response.json()
                        post_id = result.get('id')
                        print(f"✅ WordPress投稿作成成功 - Post ID: {post_id}")
                        
                        # アイキャッチ画像の設定確認
                        featured_media_id = post_data.get('featured_media_id')
                        if featured_media_id:
                            result_featured_media = result.get('featured_media', 0)
                            if result_featured_media == featured_media_id:
                                print(f"✅ アイキャッチ画像が投稿作成時に正常設定 - Media ID: {featured_media_id}")
                            else:
                                print(f"⚠️  投稿作成時のアイキャッチ画像設定を確認中...")
                                # 投稿作成後に再度アイキャッチ画像を設定
                                featured_success = await self.set_featured_image(post_id, featured_media_id)
                                if featured_success:
                                    print(f"✅ アイキャッチ画像を投稿作成後に設定完了")
                                else:
                                    print(f"❌ アイキャッチ画像の投稿作成後設定に失敗")
                        
                        # カスタムタクソノミーの投稿作成後設定
                        custom_taxonomies = post_data.get('custom_taxonomies', {})
                        if custom_taxonomies:
                            print(f"🔧 カスタムタクソノミーを投稿作成後に設定中...")
                            for taxonomy, value in custom_taxonomies.items():
                                if value:  # 値が存在する場合のみ設定
                                    term_id = await self._get_or_create_term(taxonomy, value)
                                    if term_id:
                                        await self._set_taxonomy_terms(post_id, taxonomy, [term_id])
                                        print(f"✅ {taxonomy}: {value} (ID: {term_id}) を設定完了")
                                    else:
                                        print(f"❌ {taxonomy}: {value} の設定に失敗")
                        
                        return result
                    else:
                        error_text = await response.text()
                        print(f"❌ WordPress投稿作成失敗 - Status: {response.status}")
                        print(f"Error: Response: {error_text}")
                        return None
                        
        except Exception as e:
            print(f"Error in create_post: {str(e)}")
            return None

    async def _get_or_create_taxonomy_terms(self, taxonomy: str, terms: List[str]) -> List[int]:
        """
        タクソノミーの用語を取得または作成する
        
        Args:
            taxonomy (str): タクソノミー名
            terms (List[str]): 用語のリスト
            
        Returns:
            List[int]: 用語IDのリスト
        """
        term_ids = []
        try:
            async with aiohttp.ClientSession() as session:
                for term in terms:
                    if not term:
                        continue
                        
                    # 既存の用語を検索
                    search_url = f"{self.wp_url}/wp-json/wp/v2/{taxonomy}"
                    params = {'search': term}
                    headers = {"Authorization": f"Basic {self.auth_token}"}
                    
                    async with session.get(search_url, params=params, headers=headers) as response:
                        if response.status == 200:
                            existing_terms = await response.json()
                            if existing_terms:
                                term_ids.append(existing_terms[0]['id'])
                                continue
                    
                    # 用語が存在しない場合は新規作成
                    create_url = f"{self.wp_url}/wp-json/wp/v2/{taxonomy}"
                    data = {'name': term, 'slug': term.lower().replace(' ', '-')}
                    
                    async with session.post(create_url, json=data, headers=headers) as response:
                        if response.status in (200, 201):
                            new_term = await response.json()
                            term_ids.append(new_term['id'])
                        else:
                            print(f"Warning: Failed to create term '{term}' for taxonomy '{taxonomy}'")
                            
        except Exception as e:
            print(f"Error in _get_or_create_taxonomy_terms: {e}")
            
        return term_ids

    async def _set_taxonomy_terms(self, post_id: int, taxonomy: str, term_ids: List[int]):
        """
        投稿にタクソノミーの用語を設定する
        
        Args:
            post_id (int): 投稿ID
            taxonomy (str): タクソノミー名
            term_ids (List[int]): 用語IDのリスト
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    auth=aiohttp.BasicAuth(self.wp_username, self.wp_password)
                )
            
            # タクソノミーのエンドポイント
            endpoint = f"{self.wp_url}/wp-json/wp/v2/posts/{post_id}"
            
            # タクソノミーのデータを準備
            data = {taxonomy: term_ids}
            
            async with self.session.post(endpoint, json=data) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    print(f"Warning: タクソノミー設定に失敗 ({taxonomy}): {error_text}")
                else:
                    print(f"Debug: タクソノミー設定成功 ({taxonomy}): {term_ids}")
                    
        except Exception as e:
            print(f"Error: タクソノミー設定中にエラー ({taxonomy}): {str(e)}")

    async def get_last_scheduled_post_time(self) -> Optional[datetime]:
        """
        WordPressの最終予約投稿時間を取得
        
        Returns:
            最後の予約投稿時間。データがない場合はNone
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    auth=aiohttp.BasicAuth(self.wp_username, self.wp_password)
                )
            
            # 予約投稿（status=future）の記事を取得
            params = {
                'status': 'future',
                'per_page': 100,  # 最大100件
                'orderby': 'date',
                'order': 'desc'  # 降順（新しい順）
            }
            
            async with self.session.get(self.posts_endpoint, params=params) as response:
                if response.status == 200:
                    posts = await response.json()
                    
                    if not posts:
                        print("Debug: WordPressに予約投稿がありません")
                        return None
                    
                    # 最初の記事（最新）の投稿予定時間を取得
                    latest_post = posts[0]
                    date_str = latest_post.get('date')
                    
                    if date_str:
                        # ISO 8601形式の日時をパース
                        # WordPressは通常 "2024-05-27T15:30:00" 形式で返す
                        try:
                            scheduled_time = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            print(f"Debug: WordPress最終予約投稿時間: {scheduled_time}")
                            return scheduled_time
                        except ValueError as e:
                            print(f"Debug: WordPress日時解析エラー: {date_str} - {str(e)}")
                            return None
                    else:
                        print("Debug: WordPress予約投稿に日時情報がありません")
                        return None
                else:
                    error_text = await response.text()
                    print(f"Warning: WordPress予約投稿取得に失敗: {error_text}")
                    return None
                    
        except Exception as e:
            print(f"Error: WordPress最終予約投稿時間の取得中にエラー: {str(e)}")
            return None

    async def check_existing_post_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """
        スラッグで既存投稿をチェック
        
        Args:
            slug (str): 投稿のスラッグ（通常は商品ID）
            
        Returns:
            Optional[Dict[str, Any]]: 既存投稿の情報。存在しない場合はNone
        """
        try:
            headers = {
                "Authorization": f"Basic {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                # スラッグで投稿を検索
                search_params = {
                    "slug": slug,
                    "per_page": 1,
                    "status": "any"  # 全ステータスを対象
                }
                
                async with session.get(self.posts_endpoint, params=search_params, headers=headers) as response:
                    if response.status == 200:
                        posts = await response.json()
                        if posts:
                            existing_post = posts[0]
                            print(f"🔍 既存投稿発見 - ID: {existing_post['id']}, スラッグ: {slug}, ステータス: {existing_post['status']}")
                            return {
                                'id': existing_post['id'],
                                'title': existing_post['title']['rendered'],
                                'slug': existing_post['slug'],
                                'status': existing_post['status'],
                                'link': existing_post['link'],
                                'date': existing_post['date']
                            }
                        else:
                            print(f"📋 既存投稿なし - スラッグ: {slug}")
                            return None
                    else:
                        error_text = await response.text()
                        print(f"❌ 既存投稿チェック失敗 - Status: {response.status}, Error: {error_text}")
                        return None
                        
        except Exception as e:
            print(f"❌ 既存投稿チェック中にエラー: {str(e)}")
            return None

    async def check_existing_post_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """
        タイトルで既存投稿をチェック
        
        Args:
            title (str): 投稿のタイトル
            
        Returns:
            Optional[Dict[str, Any]]: 既存投稿の情報。存在しない場合はNone
        """
        try:
            headers = {
                "Authorization": f"Basic {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                # タイトルで投稿を検索
                search_params = {
                    "search": title,
                    "per_page": 10,
                    "status": "any"  # 全ステータスを対象
                }
                
                async with session.get(self.posts_endpoint, params=search_params, headers=headers) as response:
                    if response.status == 200:
                        posts = await response.json()
                        # 完全一致するタイトルを探す
                        for post in posts:
                            if post['title']['rendered'] == title:
                                print(f"🔍 既存投稿発見（タイトル一致） - ID: {post['id']}, タイトル: {title}")
                                return {
                                    'id': post['id'],
                                    'title': post['title']['rendered'],
                                    'slug': post['slug'],
                                    'status': post['status'],
                                    'link': post['link'],
                                    'date': post['date']
                                }
                        
                        print(f"📋 既存投稿なし（タイトル一致） - タイトル: {title}")
                        return None
                    else:
                        error_text = await response.text()
                        print(f"❌ 既存投稿チェック失敗 - Status: {response.status}, Error: {error_text}")
                        return None
                        
        except Exception as e:
            print(f"❌ 既存投稿チェック中にエラー: {str(e)}")
            return None

    async def delete_post(self, post_id: int) -> bool:
        """
        投稿を削除
        
        Args:
            post_id (int): 削除する投稿のID
            
        Returns:
            bool: 削除が成功したかどうか
        """
        try:
            headers = {
                "Authorization": f"Basic {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                # 投稿を削除（ゴミ箱に移動）
                async with session.delete(f"{self.posts_endpoint}/{post_id}", headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        print(f"✅ 投稿削除成功 - ID: {post_id}")
                        return True
                    else:
                        error_text = await response.text()
                        print(f"❌ 投稿削除失敗 - ID: {post_id}, Status: {response.status}, Error: {error_text}")
                        return False
                        
        except Exception as e:
            print(f"❌ 投稿削除中にエラー: {str(e)}")
            return False

    async def force_delete_post(self, post_id: int) -> bool:
        """
        投稿を完全削除
        
        Args:
            post_id (int): 削除する投稿のID
            
        Returns:
            bool: 削除が成功したかどうか
        """
        try:
            headers = {
                "Authorization": f"Basic {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                # 投稿を完全削除
                delete_params = {"force": "true"}
                async with session.delete(f"{self.posts_endpoint}/{post_id}", params=delete_params, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        print(f"✅ 投稿完全削除成功 - ID: {post_id}")
                        return True
                    else:
                        error_text = await response.text()
                        print(f"❌ 投稿完全削除失敗 - ID: {post_id}, Status: {response.status}, Error: {error_text}")
                        return False
                        
        except Exception as e:
            print(f"❌ 投稿完全削除中にエラー: {str(e)}")
            return False 