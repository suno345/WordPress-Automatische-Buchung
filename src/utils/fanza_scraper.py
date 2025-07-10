import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from typing import List, Dict, Optional, Any
import re
import aiohttp
import os
import asyncio
import time
from functools import lru_cache
# from dotenv import load_dotenv # load_dotenvはauto_wp_post.pyで行う

# .envファイルを読み込む -> auto_wp_post.pyで行うため削除
# load_dotenv('../API.env')

# デバッグ用にDMM API関連の環境変数の値を出力 -> auto_wp_post.py側で確認
# print(f"Debug fanza_scraper: DMM_API_ID = {os.getenv('DMM_API_ID')}")
# print(f"Debug fanza_scraper: DMM_AFFILIATE_ID = {os.getenv('DMM_AFFILIATE_ID')}")

# FANZA API認証情報
DMM_API_ID = os.getenv('DMM_API_ID') or os.getenv('FANZA_API_ID')
DMM_AFFILIATE_ID = os.getenv('DMM_AFFILIATE_ID') or os.getenv('FANZA_AFFILIATE_ID')

# デバッグ用に認証情報の状態を確認
if DMM_API_ID and DMM_AFFILIATE_ID:
    print(f"Debug: DMM_API_ID = {DMM_API_ID[:10]}...")
    print(f"Debug: DMM_AFFILIATE_ID = {DMM_AFFILIATE_ID}")
else:
    print("Debug: DMM API認証情報が設定されていません")

def generate_search_variations(keyword: str) -> List[str]:
    """
    検索キーワードのバリエーションを生成
    
    Args:
        keyword: 元の検索キーワード
        
    Returns:
        キーワードのバリエーションリスト
    """
    variations = [keyword]
    
    # ひらがな・カタカナ・漢字の変換
    if re.search(r'[\u4e00-\u9fff]', keyword):  # 漢字を含む場合
        hiragana = 'あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん'
        katakana = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン'
        variations.append(keyword.translate(str.maketrans(hiragana, katakana)))
    
    # スペースの有無
    if ' ' in keyword:
        variations.append(keyword.replace(' ', ''))
    else:
        variations.append(keyword + ' ')
    
    # アルファベットの大文字小文字
    if keyword.isalpha():
        variations.append(keyword.upper())
        variations.append(keyword.lower())
    
    # 重複を除去
    return list(dict.fromkeys(variations))

def clean_title(title: str) -> str:
    """
    タイトルから割引表示や余分なスペースを除去する
    
    Args:
        title (str): 元のタイトル
        
    Returns:
        str: クリーンアップされたタイトル
    """
    if not title:
        return title
    
    # 割引表示を除去（【XX%OFF】、【割引】など）
    title = re.sub(r'【[^】]*(?:OFF|割引|セール)[^】]*】', '', title)
    
    # その他の不要な記号を除去
    title = re.sub(r'【[^】]*円[^】]*】', '', title)  # 価格表示
    title = re.sub(r'【[^】]*%[^】]*】', '', title)   # パーセント表示
    
    # 連続する空白を単一のスペースに変換
    title = re.sub(r'\s+', ' ', title)
    
    # 前後の空白を除去
    title = title.strip()
    
    return title

# キャッシュ用のグローバル変数
_image_validation_cache = {}
_cache_ttl = 3600  # 1時間

@lru_cache(maxsize=1000)
def _cached_clean_title(title: str) -> str:
    """タイトルクリーニングのキャッシュ版"""
    return clean_title(title)

async def verify_image_urls_optimized(image_urls: List[str]) -> List[str]:
    """キャッシュ付き画像ユール検証（最適化版）"""
    if not image_urls:
        return []
    
    current_time = time.time()
    valid_urls = []
    urls_to_check = []
    
    # キャッシュをチェック
    for url in image_urls:
        cache_entry = _image_validation_cache.get(url)
        if cache_entry and (current_time - cache_entry['timestamp']) < _cache_ttl:
            if cache_entry['valid']:
                valid_urls.append(url)
        else:
            urls_to_check.append(url)
    
    # 新しいURLのみ検証を並列実行
    if urls_to_check:
        print(f"Debug: {len(urls_to_check)}件の画像を並列検証中...")
        
        async def check_single_url(url):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.head(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        valid = response.status == 200 and response.headers.get('content-type', '').startswith('image/')
                        # キャッシュに保存
                        _image_validation_cache[url] = {
                            'valid': valid,
                            'timestamp': current_time
                        }
                        return url if valid else None
            except:
                # エラー時もキャッシュに保存（無効として）
                _image_validation_cache[url] = {
                    'valid': False,
                    'timestamp': current_time
                }
                return None
        
        # 並列検証実行
        results = await asyncio.gather(*[check_single_url(url) for url in urls_to_check], return_exceptions=True)
        valid_urls.extend([url for url in results if url and not isinstance(url, Exception)])
    
    print(f"Debug: 画像検証結果 - 入力: {len(image_urls)}件, 有効: {len(valid_urls)}件")
    return valid_urls

async def scrape_fanza_product_details(url, sheet_original_work=None, sheet_character=None):
    """
    FANZAの商品ページから詳細情報を取得する関数（API + スクレイピング補完）
    
    Args:
        url (str): 商品ページのURL
        sheet_original_work (str, optional): スプレッドシートから取得した原作名
        sheet_character (str, optional): スプレッドシートから取得したキャラクター名
    
    Returns:
        dict: 商品の詳細情報
    """
    try:
        # APIから商品情報を取得
        item = await get_fanza_item_info(url)
        
        if item:
            # APIから取得成功
            print(f"Debug: API取得成功 - 商品情報: {item.get('title', 'タイトル不明')}")
            
            # 基本情報の取得
            title = clean_title(item.get('title', ''))
            description = item.get('comment', '') or ''  # APIのcommentフィールドから商品説明を取得
            
            # 商品説明が取得できない場合はハイブリッドスクレイピングで補完
            if not description:
                description = await scrape_product_description_hybrid(url)
            
            # スクレイピングでも取得できない場合はAIで生成
            if not description:
                description = generate_description_from_metadata({
                    'title': title,
                    'genres': [genre.get('name', '') for genre in iteminfo.get('genre', []) if isinstance(genre, dict)],
                    'circle_name': get_first_item_name(iteminfo.get('maker', [])),
                    'author_name': get_first_item_name(iteminfo.get('author', [])),
                    'product_format': get_first_item_name(iteminfo.get('type', [])),
                    'page_count': item.get('volume', '')
                })
            
            # 商品詳細情報の取得
            iteminfo = item.get('iteminfo', {})

            # サークル名（メーカー）の取得 - DMM_API.txtの構造に基づく
            circle_name = get_first_item_name(iteminfo.get('maker', []))
            
            # 作者名の取得 - APIで取得できない場合はスクレイピング
            author_name = get_first_item_name(iteminfo.get('author', []))
            if not author_name:
                author_name = await scrape_author_name(url)
            
            # スプレッドシートからの情報を優先、なければAPIから取得
            original_work = sheet_original_work or get_first_item_name(iteminfo.get('series', []))
            character_name = sheet_character
            
            # 商品形式の取得 - APIで取得できない場合はスクレイピング
            product_format = get_first_item_name(iteminfo.get('type', []))
            if not product_format:
                product_format = await scrape_product_format(url)
            
            # ページ数の取得 - DMM_API.txtのvolume構造に基づく
            page_count = item.get('volume', '')
            
            # ジャンル情報の取得
            genres = [genre.get('name', '') for genre in iteminfo.get('genre', []) if isinstance(genre, dict)]
            
            # 画像情報の取得（APIから）
            main_image = ''
            sample_images = []

            # メイン画像 - DMM_API.txtのimageURL構造に基づく
            image_url_info = item.get('imageURL', {})
            if image_url_info:
                main_image = image_url_info.get('large', '') or image_url_info.get('small', '') or image_url_info.get('list', '')
                
            # サンプル画像 - DMM_API.txtのsampleImageURL構造に基づく
            sample_image_info = item.get('sampleImageURL', {})
            if sample_image_info:
                # sample_lを優先して取得
                sample_l_data = sample_image_info.get('sample_l', [])
                sample_s_data = sample_image_info.get('sample_s', [])
                
                # sample_lの処理 - DMM_API.txtの構造に基づく
                if isinstance(sample_l_data, list):
                    for img_obj in sample_l_data:
                        if isinstance(img_obj, dict) and 'image' in img_obj:
                            sample_images.append(img_obj['image'])
                elif isinstance(sample_l_data, dict) and 'image' in sample_l_data:
                    # 新しい構造の場合
                    if isinstance(sample_l_data['image'], list):
                        sample_images.extend(sample_l_data['image'])
                    else:
                        sample_images.append(sample_l_data['image'])
                
                # sample_lが少ない場合はsample_sも追加
                if len(sample_images) < 5 and isinstance(sample_s_data, list):
                    for img_obj in sample_s_data:
                        if isinstance(img_obj, dict) and 'image' in img_obj:
                            sample_images.append(img_obj['image'])
                        if len(sample_images) >= 15:  # 最大15枚まで
                            break
            
            # 画像URLのフィルタリング（バナーや広告を除外）
            sample_images = filter_sample_images(sample_images)
            
            # 最大サンプル画像数の制限
            max_samples = int(os.getenv('MAX_SAMPLE_IMAGES', 15))
            sample_images = sample_images[:max_samples]
            
            print(f"Debug: API取得完了 - サンプル画像数: {len(sample_images)}")
            print(f"Debug: 補完情報 - 作者名: {author_name}, 商品形式: {product_format}")

            return {
                'title': title,
                'description': description,
                'circle_name': circle_name,
                'author_name': author_name,
                'original_work': original_work,
                'character_name': character_name,
                'product_format': product_format,
                'page_count': page_count,
                'genres': genres,
                'main_image': main_image,
                'sample_images': sample_images,
                'url': url
            }
        else:
            print(f"Warning: API取得失敗、フォールバック処理を実行")
            # APIで取得できない場合のフォールバック処理
            return await scrape_fanza_product_details_fallback(url, sheet_original_work, sheet_character)

    except Exception as e:
        print(f"Error in scrape_fanza_product_details: {str(e)}")
        # エラー時のフォールバック処理
        return await scrape_fanza_product_details_fallback(url, sheet_original_work, sheet_character)

async def verify_image_urls(image_urls: List[str]) -> List[str]:
    """画像URLの有効性を確認し、有効なURLのみを返す"""
    valid_urls = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
        "Cookie": "age_check_done=1"
    }
    
    # タイムアウトを短縮して処理速度を向上
    timeout = aiohttp.ClientTimeout(total=5, connect=3)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for url in image_urls:
            try:
                # HEADリクエストで画像の存在確認
                async with session.head(url, headers=headers) as resp:
                    # 200, 301, 302, 304 を有効とする
                    if resp.status in [200, 301, 302, 304]:
                        valid_urls.append(url)
                        print(f"Debug: Valid image URL: {url} (Status: {resp.status})")
                    else:
                        print(f"Warning: Invalid image URL {url} (Status: {resp.status})")
            except asyncio.TimeoutError:
                # タイムアウトした場合も有効とみなす（サーバーが重い可能性）
                valid_urls.append(url)
                print(f"Debug: Timeout for image URL, but adding as valid: {url}")
            except Exception as e:
                # その他のエラーでも有効とみなす（ネットワークエラーなど）
                valid_urls.append(url)
                print(f"Debug: Error verifying image URL, but adding as valid: {url} - {str(e)}")
    
    print(f"Debug: Image verification result: {len(valid_urls)}/{len(image_urls)} images valid")
    return valid_urls

def extract_product_id_from_url(url: str) -> Optional[str]:
    """
    FANZAの商品URLから商品IDを抽出
    
    Args:
        url: 商品URL
        
    Returns:
        商品ID（抽出できない場合はNone）
    """
    # Debug: extract_product_id_from_url に渡されたURL
    print(f"Debug in extract_product_id_from_url: Input URL: {url}")

    match = re.search(r'cid=([^/]+)', url)
    # Debug: 正規表現マッチの結果
    print(f"Debug in extract_product_id_from_url: Regex match object: {match}")

    return match.group(1) if match else None

# DMM APIを使ってキーワードで商品を検索する関数
async def search_fanza_products_by_keyword(keyword: str) -> List[str]:
    """FANZA APIを使ってキーワード検索し、商品CIDのリストを返す"""
    # API認証情報が存在するか確認
    current_api_id = os.getenv("DMM_API_ID")
    current_affiliate_id = os.getenv("DMM_AFFILIATE_ID")

    if not current_api_id or not current_affiliate_id:
        print("Error: DMM API ID or Affiliate ID is not set in environment variables.")
        return []

    product_cids = [] # product_ids から product_cids に変更
    try:
        # FANZA API ItemList エンドポイント
        api_url = "https://api.dmm.com/affiliate/v3/ItemList"
        params = {
            'api_id': current_api_id,
            'affiliate_id': current_affiliate_id,
            'site': 'FANZA',      # FANZAサイトを指定
            'service': 'doujin', # ☆サービスをdoujinに変更☆
            'keyword': keyword,    # キーワードで検索
            'hits': 30,          # 取得件数 (100から30に変更)
            'sort': 'rank', # ソート順（必要に応じて調整）
            'output': 'json'
        }

        # デバッグ用に送信するパラメータを出力
        print(f"Debug fanza_scraper: Sending API request with params: {params}")

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params) as response:
                # ステータスコードをチェック
                if response.status != 200:
                    print(f"Error: FANZA API request failed with status {response.status}")
                    # レスポンスボディも出力してみる
                    error_text = await response.text()
                    print(f"Error body: {error_text[:500]}...") # 長すぎる場合は一部のみ表示
                    return [] # エラー時は空のリストを返す

                data = await response.json()
                
                # デバッグ用にAPIレスポンス全体を出力
                # print(f"Debug fanza_scraper: Full API response for keyword '{keyword}': {data}")
                
                # APIレスポンスから商品情報を抽出
                if data.get('result') and data['result'].get('items'):
                    for item in data['result']['items']:
                        # product_ids.append(item.get('product_id')) # product_id は存在しない可能性
                        # content_id を使う
                        cid = item.get('content_id')
                        if cid:
                            product_cids.append(cid) # product_ids から product_cids に変更
                    # デバッグ用に抽出した商品IDリストを出力
                    print(f"Debug fanza_scraper: Found product CIDs for keyword '{keyword}': {product_cids}")
                else:
                    print(f"Warning: No items found in API response for keyword '{keyword}'. Response: {data}")

    except Exception as e:
        print(f"Error during FANZA API request for keyword '{keyword}': {str(e)}")
    
    return product_cids # product_ids から product_cids に変更 

def get_first_item_name(field_list):
    """
    DMM_API.txtの構造に基づいてリストから最初の要素のnameを取得する関数
    
    Args:
        field_list: APIレスポンスのフィールドリスト
        
    Returns:
        str: 最初の要素のname、または空文字列
    """
    if not field_list or not isinstance(field_list, list):
        return ''
    
    if len(field_list) == 0:
        return ''
    
    first_item = field_list[0]
    
    # DMM_API.txtの構造: {'name': '名前', 'id': 'ID'}
    if isinstance(first_item, dict):
        return first_item.get('name', '')
    
    # 文字列の場合はそのまま返す
    return str(first_item)

def filter_sample_images(image_urls: List[str]) -> List[str]:
    """
    サンプル画像URLをフィルタリングして、バナーや広告を除外する
    
    Args:
        image_urls: 画像URLのリスト
        
    Returns:
        フィルタリングされた画像URLのリスト
    """
    if not image_urls:
        return []
    
    filtered_urls = []
    exclude_patterns = [
        'banner',
        'ad_',
        'advertisement',
        'promo',
        'campaign',
        'affiliate',
        'logo',
        'btn_',
        'button',
        'nav_',
        'header',
        'footer',
        'sidebar'
    ]
    
    for url in image_urls:
        # 除外パターンをチェック
        should_exclude = False
        for pattern in exclude_patterns:
            if pattern in url.lower():
                should_exclude = True
                break
        
        if not should_exclude:
            filtered_urls.append(url)
    
    print(f"Debug: 画像フィルタリング結果: {len(filtered_urls)}/{len(image_urls)} 枚が有効")
    return filtered_urls

async def scrape_fanza_product_details_fallback(url, sheet_original_work=None, sheet_character=None):
    """
    APIで取得できない場合のフォールバック処理（スクレイピング）
    
    Args:
        url (str): 商品ページのURL
        sheet_original_work (str, optional): スプレッドシートから取得した原作名
        sheet_character (str, optional): スプレッドシートから取得したキャラクター名
    
    Returns:
        dict: 商品の詳細情報
    """
    print(f"Debug: フォールバック処理開始 - URL: {url}")
    
    # 基本的な情報のみ返す（スクレイピングは最小限に）
    return {
        'title': 'タイトル取得失敗',
        'description': '商品説明を取得できませんでした。',
        'circle_name': '',
        'author_name': '',
        'original_work': sheet_original_work or '',
        'character_name': sheet_character or '',
        'product_format': '',
        'page_count': '',
        'genres': [],
        'main_image': '',
        'sample_images': [],  # フォールバック時はサンプル画像を取得しない
        'url': url
    }

async def get_fanza_item_info(url: str) -> Optional[Dict]:
    """
    FANZA APIを使用して商品情報を取得する（DMM_API.txt仕様準拠）
    
    Args:
        url (str): 商品ページのURL
        
    Returns:
        Optional[Dict]: 商品情報の辞書。エラー時はNone
    """
    try:
        # 環境変数から認証情報を取得
        DMM_API_ID = os.getenv("DMM_API_ID")
        DMM_AFFILIATE_ID = os.getenv("DMM_AFFILIATE_ID")
        
        if not DMM_API_ID or not DMM_AFFILIATE_ID:
            print("Error: DMM API credentials not found in environment variables")
            return None
        
        # URLから商品IDを抽出
        product_id = extract_product_id_from_url(url)
        if not product_id:
            print(f"Warning: Could not extract product ID from URL: {url}")
            return None

        print(f"Debug: API呼び出し開始 - Product ID: {product_id}")

        # DMM_API.txtの仕様に基づくAPIパラメータ
        params = {
            'api_id': DMM_API_ID,
            'affiliate_id': DMM_AFFILIATE_ID,
            'site': 'FANZA',
            'service': 'doujin',
            'cid': product_id,
            'output': 'json'
        }

        # APIリクエスト
        api_url = "https://api.dmm.com/affiliate/v3/ItemList"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params) as response:
                if response.status != 200:
                    print(f"Error: API request failed with status {response.status}")
                    error_text = await response.text()
                    print(f"Error response: {error_text[:500]}")
                    return None
                
                data = await response.json()
                
                # DMM_API.txtの構造に基づくレスポンス解析
                result = data.get('result', {})
                if result.get('status') != 200:
                    print(f"Error: API returned error status: {result.get('status')}")
                    return None
                
                items = result.get('items', [])
                if not items:
                    print(f"Error: No items found for product ID: {product_id}")
                    print(f"API Response: {data}")
                    return None
                
                # 最初のアイテムを返す
                item = items[0]
                print(f"Debug: API取得成功 - Product ID: {product_id}, Title: {item.get('title', 'タイトル不明')}")
                
                # デバッグ用にiteminfo構造を確認
                iteminfo = item.get('iteminfo', {})
                print(f"Debug: iteminfo keys: {list(iteminfo.keys())}")
                if 'author' in iteminfo:
                    print(f"Debug: author data: {iteminfo['author']}")
                if 'maker' in iteminfo:
                    print(f"Debug: maker data: {iteminfo['maker']}")
                
                return item

    except Exception as e:
        print(f"Error in get_fanza_item_info: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None 

async def scrape_author_name(url: str) -> str:
    """
    商品ページから作者名をスクレイピングで取得
    
    Args:
        url: 商品ページのURL
        
    Returns:
        作者名（取得できない場合は空文字列）
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
            'Cookie': 'age_check_done=1'
        }
        
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    print(f"Warning: 作者名スクレイピング失敗 - HTTP {response.status}")
                    return ''
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 指定されたCSSセレクターで作者名を取得
                author_selector = '#w > div.l-areaProductTitle > div.m-circleInfo.u-common__clearfix > div > div:nth-child(1) > div > div > div > a'
                author_elem = soup.select_one(author_selector)
                
                if author_elem:
                    author_name = author_elem.get_text(strip=True)
                    print(f"Debug: 作者名スクレイピング成功 - {author_name}")
                    return author_name
                else:
                    print(f"Debug: 作者名要素が見つかりません - セレクター: {author_selector}")
                    return ''
                    
    except Exception as e:
        print(f"Error in scrape_author_name: {str(e)}")
        return ''

async def scrape_product_format(url: str) -> str:
    """
    商品ページから商品形式をスクレイピングで取得
    
    Args:
        url: 商品ページのURL
        
    Returns:
        商品形式（取得できない場合は空文字列）
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
            'Cookie': 'age_check_done=1'
        }
        
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    print(f"Warning: 商品形式スクレイピング失敗 - HTTP {response.status}")
                    return ''
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 指定されたCSSセレクターで商品形式を取得
                format_selector = '#l-areaVariableBoxWrap > div > div.l-areaVariableBoxGroup > div.l-areaProductInfo > div.m-productInformation > div > div:nth-child(1) > dl > dd'
                format_elem = soup.select_one(format_selector)
                
                if format_elem:
                    product_format = format_elem.get_text(strip=True)
                    print(f"Debug: 商品形式スクレイピング成功 - {product_format}")
                    return product_format
                else:
                    print(f"Debug: 商品形式要素が見つかりません - セレクター: {format_selector}")
                    return ''
                    
    except Exception as e:
        print(f"Error in scrape_product_format: {str(e)}")
        return '' 

async def scrape_product_description(url: str) -> str:
    """
    商品ページから商品説明をスクレイピングで取得（改善版）
    
    Args:
        url: 商品ページのURL
        
    Returns:
        商品説明（取得できない場合は空文字列）
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Cookie": "age_check_done=1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        timeout = aiohttp.ClientTimeout(total=15)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 商品説明の取得（拡張されたセレクタを試行）
                    description_selectors = [
                        # 現在のセレクタ（優先度高）
                        '.mg-b20.lh4',
                        '.productDetail__txt',
                        '.product-detail-description',
                        '.item-description',
                        
                        # 汎用的セレクタ（中優先度）
                        'div[class*="mg-b20"]',
                        'div[class*="productDetail"]',
                        'div[class*="description"]',
                        'div[class*="detail"]',
                        'div[class*="comment"]',
                        'div[class*="intro"]',
                        'div[class*="summary"]',
                        
                        # 要素タイプ別セレクタ
                        'p[class*="description"]',
                        'p[class*="detail"]',
                        'p[class*="intro"]',
                        'p[class*="comment"]',
                        
                        # 構造的セレクタ
                        '.product-info p',
                        '.product-content p',
                        '.item-info p',
                        '.work-info p',
                        '.content-area p',
                        '.main-content p',
                        
                        # 属性ベースセレクタ
                        '[data-description]',
                        '[data-detail]',
                        '[data-comment]',
                        '[data-content]',
                        
                        # 緊急時フォールバック
                        'div p',
                        'section p',
                        'article p'
                    ]
                    
                    # 各セレクタを試行
                    for selector in description_selectors:
                        try:
                            description_elem = soup.select_one(selector)
                            if description_elem:
                                description = description_elem.get_text(strip=True)
                                if validate_description_quality(description):
                                    cleaned_description = clean_description(description)
                                    print(f"Debug: 商品説明取得成功 (セレクタ: {selector}) - {cleaned_description[:50]}...")
                                    return cleaned_description
                        except Exception as e:
                            print(f"Debug: セレクタ {selector} でエラー: {str(e)}")
                            continue
                    
                    # テキストパターンベースのフォールバック
                    print(f"Debug: CSS選択できない場合のキーワード検索を開始")
                    keywords = ['作品内容', 'あらすじ', '内容紹介', '商品説明', 'ストーリー', '概要']
                    for keyword in keywords:
                        try:
                            elements = soup.find_all(text=re.compile(keyword))
                            for elem in elements:
                                if elem.parent:
                                    description = elem.parent.get_text(strip=True)
                                    if validate_description_quality(description):
                                        cleaned_description = clean_description(description)
                                        print(f"Debug: キーワード検索で説明文取得成功 ({keyword}) - {cleaned_description[:50]}...")
                                        return cleaned_description
                        except Exception as e:
                            print(f"Debug: キーワード '{keyword}' でエラー: {str(e)}")
                            continue
                    
                    print(f"Warning: 商品説明をスクレイピングで取得できませんでした: {url}")
                    return ""
                else:
                    print(f"Warning: 商品ページの取得に失敗: {response.status}")
                    return ""
                    
    except Exception as e:
        print(f"Error: 商品説明のスクレイピング中にエラー: {str(e)}")
        return ""

def validate_description_quality(description: str) -> bool:
    """商品説明の品質チェック（改善版）"""
    if not description:
        return False
    
    # 最低文字数を緩和（20文字→10文字）
    if len(description) < 10:
        return False
    
    # 意味のないテキストを除外
    meaningless_patterns = [
        r'^[0-9\s\-\.\,]+$',  # 数字と記号のみ
        r'^[★☆\s]+$',        # 星記号のみ
        r'^[\.]{3,}$',        # 省略記号のみ
        r'^[・\s]+$',         # 中点のみ
        r'^[×\s]+$',         # ×記号のみ
    ]
    
    for pattern in meaningless_patterns:
        if re.match(pattern, description):
            return False
    
    # 除外すべきテキスト
    exclude_phrases = [
        'JavaScript', 'Cookie', 'お問い合わせ', 'FAQ', 
        'プライバシーポリシー', '利用規約', '著作権',
        'Copyright', 'All Rights Reserved'
    ]
    
    for phrase in exclude_phrases:
        if phrase in description:
            return False
    
    # 有効な説明文の特徴をチェック
    positive_indicators = [
        '作品', '内容', 'ストーリー', 'キャラクター', 
        'シナリオ', 'イラスト', 'CG', 'ゲーム', 'マンガ',
        '物語', '設定', '世界観', '登場人物', '主人公'
    ]
    
    if any(indicator in description for indicator in positive_indicators):
        return True
    
    # 長さによる判定（30文字以上なら有効とみなす）
    if len(description) >= 30:
        return True
    
    return False

def clean_description(description: str) -> str:
    """商品説明のクリーンアップ"""
    if not description:
        return description
    
    # 不要な文字列を除去
    description = re.sub(r'※.*?(?=\n|$)', '', description)  # 注意書き
    description = re.sub(r'【.*?】', '', description)        # 角括弧内の文字
    description = re.sub(r'■.*?(?=\n|$)', '', description)  # 見出し記号
    description = re.sub(r'★.*?(?=\n|$)', '', description)  # 星記号
    description = re.sub(r'◆.*?(?=\n|$)', '', description)  # ダイヤ記号
    description = re.sub(r'\s+', ' ', description)          # 連続する空白を単一化
    
    # 先頭・末尾の空白を除去
    description = description.strip()
    
    # 最大文字数制限（必要に応じて）
    max_length = 500
    if len(description) > max_length:
        description = description[:max_length] + "..."
    
    return description

def generate_description_from_metadata(product_data: dict) -> str:
    """
    商品メタデータからAIが説明文を生成
    
    Args:
        product_data: 商品データの辞書
        
    Returns:
        生成された説明文
    """
    try:
        # 基本情報の取得
        title = product_data.get('title', '')
        genres = product_data.get('genres', [])
        circle_name = product_data.get('circle_name', '')
        author_name = product_data.get('author_name', '')
        product_format = product_data.get('product_format', '')
        page_count = product_data.get('page_count', '')
        
        # 説明文の構築
        description_parts = []
        
        # 基本紹介
        if title:
            description_parts.append(f"「{title}」")
        
        # ジャンル情報
        if genres:
            # 有効なジャンルのみフィルタリング
            valid_genres = [g for g in genres if g and g.strip()]
            if valid_genres:
                genre_text = "、".join(valid_genres[:3])  # 最初の3つのジャンル
                description_parts.append(f"は{genre_text}ジャンルの同人作品です。")
            else:
                description_parts.append("は同人作品です。")
        else:
            description_parts.append("は同人作品です。")
        
        # サークル・作者情報
        if circle_name:
            description_parts.append(f"サークル「{circle_name}」")
            if author_name and author_name != circle_name:
                description_parts.append(f"（作者：{author_name}）")
            description_parts.append("により制作されました。")
        elif author_name:
            description_parts.append(f"作者「{author_name}」による作品です。")
        
        # 作品形式・ページ数
        format_info = []
        if product_format:
            format_info.append(f"作品形式：{product_format}")
        if page_count:
            format_info.append(f"ページ数：{page_count}")
        
        if format_info:
            description_parts.append(" ".join(format_info) + "。")
        
        # 魅力的な結び
        if genres:
            description_parts.append("魅力的な内容で多くの読者に愛されている作品です。")
        else:
            description_parts.append("詳細な内容については商品ページをご確認ください。")
        
        # 説明文の組み立て
        description = "".join(description_parts)
        
        print(f"Debug: AI生成説明文: {description[:50]}...")
        return description
        
    except Exception as e:
        print(f"Error: AI説明文生成中にエラー: {str(e)}")
        # エラー時のフォールバック
        title = product_data.get('title', '商品名不明')
        return f"「{title}」の同人作品です。詳細は商品ページをご確認ください。"

# リソース管理クラス
class PlaywrightResourceManager:
    """
    Playwrightのリソース管理を行うクラス
    VPS環境での効率的なブラウザ管理を実現
    """
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.session_count = 0
        self.max_sessions = 10  # 10回使用後にリセット
    
    async def initialize(self):
        """ブラウザセッションの初期化"""
        try:
            if not self.playwright:
                from playwright.async_api import async_playwright
                self.playwright = await async_playwright().start()
            
            if not self.browser:
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=[
                        # VPS最適化設定
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--memory-pressure-off',
                        '--max_old_space_size=512',  # メモリ制限をより厳しく
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding',
                        '--disable-features=TranslateUI,BlinkGenPropertyTrees,VizDisplayCompositor',
                        '--disable-extensions',
                        '--disable-plugins',
                        '--disable-default-apps',
                        '--disable-sync',
                        '--disable-background-networking',
                        '--disable-component-update',
                        '--single-process',
                        '--no-zygote',
                        '--disable-breakpad'
                    ]
                )
            
            if not self.context:
                self.context = await self.browser.new_context(
                    user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                )
            
            print(f"Debug: PlaywrightResourceManager初期化完了")
            
        except Exception as e:
            print(f"Debug: PlaywrightResourceManager初期化エラー: {str(e)}")
            raise
    
    async def get_page(self):
        """新しいページを取得"""
        await self.initialize()
        page = await self.context.new_page()
        
        # 基本設定
        page.set_default_timeout(15000)  # 15秒に短縮
        await page.add_init_script("window.localStorage.setItem('age_check_done', '1')")
        
        self.session_count += 1
        
        # セッション数が上限に達したらリセット
        if self.session_count >= self.max_sessions:
            print(f"Debug: セッション上限到達、リソースをリセット中...")
            await self.reset()
        
        return page
    
    async def reset(self):
        """リソースのリセット"""
        try:
            if self.context:
                await self.context.close()
                self.context = None
            
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            self.session_count = 0
            print(f"Debug: PlaywrightResourceManagerリセット完了")
            
        except Exception as e:
            print(f"Debug: PlaywrightResourceManagerリセットエラー: {str(e)}")
    
    async def cleanup(self):
        """完全なクリーンアップ"""
        try:
            await self.reset()
            
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            
            print(f"Debug: PlaywrightResourceManager完全クリーンアップ完了")
            
        except Exception as e:
            print(f"Debug: PlaywrightResourceManagerクリーンアップエラー: {str(e)}")

# グローバルリソースマネージャー
_resource_manager = None

async def get_resource_manager():
    """グローバルリソースマネージャーを取得"""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = PlaywrightResourceManager()
    return _resource_manager

# Playwright統合機能
async def scrape_product_description_with_playwright(url: str) -> str:
    """
    Playwrightを使用した商品説明取得（VPS最適化版）
    
    Args:
        url: 商品ページのURL
        
    Returns:
        商品説明（取得できない場合は空文字列）
    """
    try:
        print(f"Debug: Playwright最適化版実行開始 - URL: {url}")
        
        # リソースマネージャーを取得
        manager = await get_resource_manager()
        page = await manager.get_page()
        
        try:
            # ページにアクセス
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=15000)
                print(f"Debug: Playwrightページアクセス成功")
                # 追加で少し待機（JavaScript実行のため）
                await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"Debug: Playwrightページアクセス失敗: {str(e)}")
                await page.close()
                return ""
            
            # 商品説明を複数の方法で取得
            description = ""
            
            # 方法1: 基本セレクタ（高速）
            basic_selectors = [
                '.mg-b20.lh4',
                '.productDetail__txt'
            ]
            
            for selector in basic_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=2000)
                    if element:
                        description = await element.inner_text()
                        if validate_description_quality(description):
                            print(f"Debug: Playwright基本取得成功 (セレクタ: {selector})")
                            break
                except:
                    continue
            
            # 方法2: 拡張セレクタ（中速）
            if not description:
                extended_selectors = [
                    'div[class*="mg-b20"]',
                    'div[class*="productDetail"]',
                    'div[class*="description"]',
                    'p[class*="description"]'
                ]
                
                for selector in extended_selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=1500)
                        if element:
                            description = await element.inner_text()
                            if validate_description_quality(description):
                                print(f"Debug: Playwright拡張取得成功 (セレクタ: {selector})")
                                break
                    except:
                        continue
            
            # 方法3: JavaScript実行（低速だが確実）
            if not description:
                try:
                    description = await page.evaluate("""
                        () => {
                            const elements = document.querySelectorAll('p, div');
                            for (let elem of elements) {
                                const text = elem.textContent.trim();
                                if (text.length > 20 && 
                                    (text.includes('作品') || text.includes('内容') || 
                                     text.includes('ストーリー') || text.includes('物語'))) {
                                    return text;
                                }
                            }
                            return '';
                        }
                    """)
                    
                    if validate_description_quality(description):
                        print("Debug: PlaywrightJS実行取得成功")
                except Exception as e:
                    print(f"Debug: PlaywrightJS実行失敗: {str(e)}")
            
            # ページを閉じる
            await page.close()
            
            if description:
                cleaned_description = clean_description(description)
                print(f"Debug: Playwright最適化版取得成功 - {cleaned_description[:50]}...")
                return cleaned_description
            else:
                print("Debug: Playwright最適化版全方法で取得失敗")
                return ""
                
        except Exception as e:
            await page.close()
            print(f"Debug: Playwrightページ処理エラー: {str(e)}")
            return ""
            
    except ImportError:
        print("Debug: Playwrightがインストールされていません")
        return ""
    except Exception as e:
        print(f"Debug: Playwright最適化版実行エラー: {str(e)}")
        return ""

async def scrape_product_description_hybrid(url: str) -> str:
    """
    ハイブリッドモード: 従来のスクレイピング → Playwright の順で試行
    
    Args:
        url: 商品ページのURL
        
    Returns:
        商品説明（取得できない場合は空文字列）
    """
    # まず従来のスクレイピングを試行
    print(f"Debug: ハイブリッドモード開始 - 従来のスクレイピングを試行")
    description = await scrape_product_description(url)
    
    # 従来の方法で成功した場合
    if description and validate_description_quality(description):
        print(f"Debug: 従来のスクレイピングで成功 - {description[:50]}...")
        return description
    
    # 従来の方法で失敗した場合はPlaywrightを試行
    print(f"Debug: 従来のスクレイピング失敗、Playwrightフォールバックを実行")
    playwright_description = await scrape_product_description_with_playwright(url)
    
    if playwright_description and validate_description_quality(playwright_description):
        print(f"Debug: Playwrightフォールバックで成功 - {playwright_description[:50]}...")
        return playwright_description
    
    # 両方失敗した場合
    print(f"Debug: 両方の方法で失敗、空文字列を返却")
    return "" 