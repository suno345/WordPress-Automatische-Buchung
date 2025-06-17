import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from typing import List, Dict, Optional, Any
import re
import aiohttp
import os
import asyncio
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
            
            # 商品説明が取得できない場合はスクレイピングで補完
            if not description:
                description = await scrape_product_description(url)
            
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
    商品ページから商品説明をスクレイピングで取得
    
    Args:
        url: 商品ページのURL
        
    Returns:
        商品説明（取得できない場合は空文字列）
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
            "Cookie": "age_check_done=1"
        }
        
        timeout = aiohttp.ClientTimeout(total=10)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 商品説明の取得（複数のセレクタを試行）
                    description_selectors = [
                        '.mg-b20.lh4',  # 一般的な商品説明
                        '.productDetail__txt',  # 新しいレイアウト
                        '.product-detail-description',  # 別のレイアウト
                        '.item-description',  # 汎用的なセレクタ
                        'div[class*="description"]',  # クラス名に"description"を含む要素
                        'p[class*="detail"]'  # クラス名に"detail"を含むp要素
                    ]
                    
                    for selector in description_selectors:
                        description_elem = soup.select_one(selector)
                        if description_elem:
                            description = description_elem.get_text(strip=True)
                            if description and len(description) > 20:  # 最低20文字以上
                                print(f"Debug: 商品説明をスクレイピングで取得: {description[:50]}...")
                                return description
                    
                    print(f"Warning: 商品説明をスクレイピングで取得できませんでした: {url}")
                    return ""
                else:
                    print(f"Warning: 商品ページの取得に失敗: {response.status}")
                    return ""
                    
    except Exception as e:
        print(f"Error: 商品説明のスクレイピング中にエラー: {str(e)}")
        return "" 