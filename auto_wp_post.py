import requests
import base64
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import asyncio
import aiohttp
import json
from src.utils import fanza_scraper
from src.core.spreadsheet.manager import SpreadsheetManager
from src.core.wordpress.poster import WordPressPoster
# from src.core.utils.character_validator import CharacterValidator
# from src.core.utils.pre_filter import PreFilter

# ダミークラス（存在しないモジュール対策）
class CharacterValidator:
    @staticmethod
    def get_validation_prompt_addition(sheet_character, sheet_original_work, title):
        return ""

class PreFilter:
    @staticmethod
    def should_exclude_product(title, original_work, character):
        return {'action': 'continue', 'reason': 'ダミーフィルター'}
import re # 正規表現モジュールのインポート
from urllib.parse import quote

def clean_title(title):
    """タイトルから不適切な文字を除去"""
    if not title:
        return ""
    
    # 不要な文字列を除去
    title = re.sub(r'\.pdf$', '', title)  # .pdf拡張子を除去
    title = re.sub(r'_ 無料.*?マンガ', '', title)  # _ 無料18禁マンガ等を除去
    title = re.sub(r'_ 無料.*', '', title)  # _ 無料で始まる文字列を除去
    title = re.sub(r'\s+', ' ', title)  # 連続する空白を単一空白に
    title = title.strip()  # 前後の空白を除去
    
    return title

def validate_product_data(details):
    """商品データの品質チェック"""
    errors = []
    warnings = []
    
    # 必須フィールドチェック
    required_fields = ['title', 'description', 'author_name', 'circle_name']
    for field in required_fields:
        if not details.get(field):
            errors.append(f"必須フィールド '{field}' が空です")
    
    # 画像データチェック
    if not details.get('main_image_url'):
        errors.append("メイン画像URLが取得できていません")
    
    if not details.get('sample_images') or len(details.get('sample_images', [])) == 0:
        warnings.append("サンプル画像が取得できていません")
    
    # 価格情報チェック
    if not details.get('price'):
        warnings.append("価格情報が取得できていません")
    
    # 作品形式チェック
    if not details.get('product_format'):
        warnings.append("作品形式が取得できていません")
    
    # ページ数チェック
    if not details.get('page_count'):
        warnings.append("ページ数が取得できていません")
    
    return {
        'is_valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'quality_score': max(0, 100 - len(errors) * 25 - len(warnings) * 5)
    }

def generate_free_reading_section(title, original_work='', character_name=''):
    """無料で読める？セクションを生成（SEO強化版）"""
    
    # タイトルとキャラクター名の組み合わせ
    if character_name and character_name not in ['不明', '不明（特定不可）', '不明（特定できず）', '不明（確定情報なし）', '不明（フルネームの特定不可）', '不明（提供情報からはキャラクター特定不可）', '不明（キャラクター名が特定できない）']:
        full_title = f"{title}【{character_name}】"
        seo_keyword = f"{character_name} 同人"
    else:
        full_title = title
        seo_keyword = title
    
    # 原作名がある場合はSEOキーワードに追加
    if original_work and original_work not in ['不明', '不明（特定不可）', '不明（特定できず）', '不明（確定情報なし）', '不明（複数の原作が混在する可能性あり）', '不明（提供情報からは原作特定不可）', '不明（原作名が特定できない）'] and not original_work.startswith('不明（推定：'):
        seo_keyword = f"{original_work} {seo_keyword}"
    
    section_html = f'''<!-- wp:heading -->
<h2>漫画『{full_title}』は漫画rawやhitomiで無料で読める？</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>漫画rawやhitomi、momon:GA（モモンガ）などの海賊版サイトを使えば、{full_title}を全巻無料で読めるかもしれません。しかし、海賊版サイトを利用するのは控えましょう。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>無断転載している違法の海賊版サイトを使うと、{full_title}を全巻無料で読める反面、以下のリスクが生じるからです。</p>
<!-- /wp:paragraph -->

<!-- wp:list -->
<ul>
<li>デバイスの故障</li>
<li>クレカ情報といった個人情報の漏洩・悪用</li>
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

<!-- wp:heading {"level":3} -->
<h3>{seo_keyword} rawで検索しても危険！</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>「{seo_keyword} raw」「{character_name} raw」「{original_work} raw」などで検索して海賊版サイトを探すのは、前述のリスクがあるため大変危険です。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>本作品はFANZA公式サイトで正規購入できます。高品質な作品を適正な価格で楽しみ、クリエイターを応援しましょう。</p>
<!-- /wp:paragraph -->'''
    
    return section_html

# ====== グローバル変数 ======
# 最終予約時間を管理するグローバル変数
global_last_scheduled_time = None

# ====== WordPress設定 ======
# 環境変数の読み込み
load_dotenv('API.env')
# 絶対パスでも試行
load_dotenv('/Users/sunouchikouichi/Desktop/プログラミング/同人WordPress自動投稿/API.env')

# 環境変数から設定を取得
WP_URL = os.getenv('WP_URL')
WP_USERNAME = os.getenv('WP_USERNAME')
WP_APP_PASSWORD = os.getenv('WP_APP_PASSWORD')

# DMM API設定
DMM_API_ID = os.getenv('DMM_API_ID')
DMM_AFFILIATE_ID = os.getenv('DMM_AFFILIATE_ID')

# xAI API設定
XAI_API_KEY = os.getenv('XAI_API_KEY')

# OpenAI API設定
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# 環境変数をfanza_scraperでも使用できるように設定
if DMM_API_ID:
    os.environ['DMM_API_ID'] = DMM_API_ID
if DMM_AFFILIATE_ID:
    os.environ['DMM_AFFILIATE_ID'] = DMM_AFFILIATE_ID

# デバッグ用に設定後の環境変数を確認
print(f"Debug: 設定後のDMM_API_ID = {os.environ.get('DMM_API_ID', '未設定')}")
print(f"Debug: 設定後のDMM_AFFILIATE_ID = {os.environ.get('DMM_AFFILIATE_ID', '未設定')}")

# サンプル画像の最大数
MAX_SAMPLE_IMAGES = int(os.getenv('MAX_SAMPLE_IMAGES', 15))

print(f"Debug: DMM_API_ID = {DMM_API_ID}")
print(f"Debug: DMM_AFFILIATE_ID = {DMM_AFFILIATE_ID}")
print(f"Debug: MAX_SAMPLE_IMAGES = {MAX_SAMPLE_IMAGES}")
print(f"Debug: XAI_API_KEY = {'設定済み' if XAI_API_KEY else '未設定'}")
print(f"Debug: OPENAI_API_KEY = {'設定済み' if OPENAI_API_KEY else '未設定'}")
print(f"Debug: WP_URL = {WP_URL}")
print(f"Debug: WP_USERNAME = {WP_USERNAME}")
print(f"Debug: WP_APP_PASSWORD = {'設定済み' if WP_APP_PASSWORD else '未設定'}")

def extract_product_id_from_url(url):
    """
    URLから商品IDを抽出する
    
    Args:
        url (str): 商品URL
        
    Returns:
        str: 商品ID。抽出できない場合は空文字
    """
    try:
        if not url:
            return ''
        
        # cid=パラメータから商品IDを抽出
        product_id_match = re.search(r'cid=([^/&]+)', url)
        if product_id_match:
            return product_id_match.group(1)
        
        return ''
        
    except Exception as e:
        print(f"Warning: 商品ID抽出中にエラー: {str(e)}")
        return ''

def generate_affiliate_link(original_url):
    """
    FANZA商品URLをアフィリエイトリンクに変換する
    
    Args:
        original_url (str): 元のFANZA商品URL
        
    Returns:
        str: アフィリエイトリンク
    """
    try:
        # URLから商品IDを抽出
        product_id_match = re.search(r'cid=([^/&]+)', original_url)
        if not product_id_match:
            print(f"Warning: 商品IDを抽出できませんでした: {original_url}")
            return original_url
        
        product_id = product_id_match.group(1)
        
        # アフィリエイトリンクを生成
        affiliate_link = f"https://al.dmm.co.jp/?lurl=https%3A%2F%2Fwww.dmm.co.jp%2Fdc%2Fdoujin%2F-%2Fdetail%2F%3D%2Fcid%3D{product_id}%2F&af_id={DMM_AFFILIATE_ID}&ch=link_tool&ch_id=text"
        
        print(f"Debug: アフィリエイトリンク生成 - 商品ID: {product_id}")
        print(f"Debug: アフィリエイトリンク: {affiliate_link}")
        
        return affiliate_link
        
    except Exception as e:
        print(f"Error: アフィリエイトリンク生成エラー: {str(e)}")
        return original_url

def load_prompt_template(filename):
    """
    プロンプトファイルを読み込む関数（YAML形式対応）
    """
    try:
        prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', filename)
        with open(prompt_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # YAML形式のプロンプトファイルかどうかを判定
        if filename.endswith('.txt') and 'prompt_definition:' in content:
            try:
                import yaml
                # YAMLとして解析を試行
                yaml_data = yaml.safe_load(content)
                if yaml_data and 'prompt_definition' in yaml_data:
                    print(f"Debug: YAML形式のプロンプトファイルを検出: {filename}")
                    return yaml_data
            except ImportError:
                print("Warning: PyYAMLがインストールされていません。テキスト形式として処理します。")
            except yaml.YAMLError as e:
                print(f"Warning: YAML解析エラー: {str(e)}。テキスト形式として処理します。")
        
        # 通常のテキストファイルとして返す
        return content
        
    except Exception as e:
        print(f"Warning: プロンプトファイル {filename} の読み込みに失敗: {str(e)}")
        return None

# ====== Google Sheets認証 ======
# load_dotenv('./同人WordPress自動投稿/API.env')
load_dotenv('/Users/sunouchikouichi/Desktop/プログラミング/同人WordPress自動投稿/API.env')

def get_unprocessed_products(ss):
    """商品管理シートから未処理データを取得（厳密な重複チェック付き）"""
    # FORMULAを指定して、数式自体を取得。原作名・キャラ名も取得するために範囲を広げる (例: I列まで)
    # ヘッダー構成: 投稿ステータス, 原作名, キャラ名, 商品URL, 商品名, 予約投稿日時, 記事URL, 最終処理日時, エラー詳細
    values = ss._get_sheet_values(ss.product_sheet, 'A2:I1000', value_render_option='FORMULA')
    products = []
    
    # 処理対象外のステータス一覧（厳密に定義）
    excluded_statuses = {
        '予約投稿', '投稿済み', '投稿完了', '公開済み', '処理済み', 
        '下書き保存', '下書き', 'draft', 'published', 'scheduled',
        'エラー', 'スキップ', 'skip', 'error', '除外', '無効'
    }
    
    print("Debug: Starting to process sheet values")
    print(f"Debug: 除外対象ステータス: {excluded_statuses}")
    
    for idx, row in enumerate(values, start=2):
        # 最低限、投稿ステータス(A列)と商品URL(D列)が存在するかチェック
        if len(row) < 4:
            print(f"Debug: Row {idx} - 不完全な行データ（列数不足）: {len(row)}")
            continue
            
        status = str(row[0]).strip() if row[0] else ''
        product_url_formula = row[3] if len(row) > 3 else ''
        
        print(f"Debug: Row {idx} - ステータス: '{status}', URL: '{product_url_formula[:50]}...'")
        
        # ステータスチェック（厳密）
        if not status:
            print(f"Debug: Row {idx} - ステータスが空のためスキップ")
            continue
            
        if status in excluded_statuses:
            print(f"Debug: Row {idx} - 除外対象ステータス '{status}' のためスキップ")
            continue
            
        # 「未処理」または空白のみを処理対象とする
        if status != '未処理' and status != '':
            print(f"Debug: Row {idx} - 未処理以外のステータス '{status}' のためスキップ")
            continue
        
        # 記事URL（G列）が既に存在する場合は投稿済みとみなす
        post_url = row[6] if len(row) > 6 else ''
        if post_url and str(post_url).strip():
            print(f"Debug: Row {idx} - 記事URLが既に存在するためスキップ: {post_url}")
            continue
        
        # 予約投稿日時（F列）が存在する場合は既に処理済みとみなす
        scheduled_date = row[5] if len(row) > 5 else ''
        if scheduled_date and str(scheduled_date).strip():
            print(f"Debug: Row {idx} - 予約投稿日時が既に設定されているためスキップ: {scheduled_date}")
            continue
            
        actual_url = ''
        
        if isinstance(product_url_formula, str):
            if product_url_formula.startswith('=HYPERLINK('):
                # =HYPERLINK("URL", "TEXT") からURLを抽出
                # より堅牢な正規表現パターンを使用
                match = re.search(r'=HYPERLINK\("([^"]+)"', product_url_formula)
                if match:
                    actual_url = match.group(1)
                    print(f"Debug: Row {idx} - HYPERLINK からURL抽出: {actual_url}")
                else:
                    print(f"Warning: Row {idx} - HYPERLINK式の解析に失敗: {product_url_formula}")
            else:
                # 通常のURL文字列の場合
                actual_url = product_url_formula
                print(f"Debug: Row {idx} - 直接URL使用: {actual_url}")
        else:
            print(f"Warning: Row {idx} - 無効な商品URLデータ型: {type(product_url_formula)}")
            continue

        if actual_url:
            # 商品IDを抽出してURLの形式を確認
            product_id = re.search(r'cid=([^/&]+)', actual_url)
            if product_id:
                print(f"Debug: Row {idx} - 有効な商品ID発見: {product_id.group(1)} - 処理対象に追加")
                new_row = list(row)
                new_row[3] = actual_url  # URLを更新
                products.append({'row_idx': idx, 'row': new_row})
            else:
                print(f"Warning: Row {idx} - URLから商品IDを抽出できません: {actual_url}")
        else:
            print(f"Warning: Row {idx} - 有効なURLが見つかりません")

    print(f"Debug: 最終的に {len(products)} 件の未処理商品を発見")
    return products

async def call_grok_api_with_retry(prompt, max_tokens=500, max_retries=3):
    """リトライ機能付きGrok API呼び出し"""
    for attempt in range(max_retries):
        try:
            result = await call_grok_api(prompt, max_tokens)
            if result:  # 成功時は結果を返す
                return result
        except Exception as e:
            if attempt == max_retries - 1:  # 最後の試行
                print(f"Grok APIリトライ終了: {e}")
                return None
            else:
                # 指数バックオフ
                wait_time = (2 ** attempt) + 1
                print(f"Grok APIリトライ {attempt + 1}/{max_retries} - {wait_time}秒待機")
                await asyncio.sleep(wait_time)
    return None

async def call_grok_api(prompt, max_tokens=500):
    """
    Grok API（xAI API）を呼び出す共通関数
    """
    if not XAI_API_KEY:
        print("Warning: XAI_API_KEY が設定されていません。元のテキストを返します。")
        return None
    
    headers = {
        'Authorization': f'Bearer {XAI_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'messages': [
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'model': 'grok-3',
        'stream': False,
        'temperature': 0.7,
        'max_tokens': max_tokens
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://api.x.ai/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content'].strip()
                else:
                    error_text = await response.text()
                    print(f"Grok API Error {response.status}: {error_text}")
                    return None
    except Exception as e:
        print(f"Grok API呼び出しエラー: {str(e)}")
        return None

async def get_grok_rewritten_description(original_description, product_info, target_audience):
    """
    Grok APIで紹介文をリライトする（詳細プロンプト使用）
    """
    title = product_info.get('title', '')
    circle_name = product_info.get('circle_name', '')
    author_name = product_info.get('author_name', '')
    original_work = product_info.get('original_work', '')
    character_name = product_info.get('character_name', '')
    genres = product_info.get('genres', [])
    description = product_info.get('description', '')
    sample_images = product_info.get('sample_images', [])
    
    # サンプル画像から顔画像を抽出（最大5枚、女性の顔のみ）
    face_images_info = ""
    if sample_images:
        print(f"Debug: {len(sample_images)}枚のサンプル画像から顔画像を抽出中...")
        face_count = min(5, len(sample_images))
        face_images_info = f"\n\n【顔画像情報】\n{face_count}枚の女性キャラクターの顔画像を分析対象として提供しています。"
        print(f"Debug: 最大{face_count}枚の顔画像をGrok APIに送信予定")
    
    # プロンプトテンプレートを読み込み
    prompt_template = load_prompt_template('grok_prompt.txt')
    
    if prompt_template:
        # grok_prompt.txtの制約に従ったプロンプトを作成
        prompt = f"""以下の同人作品のリード文とストーリー/紹介文を作成してください。

【作品情報】
キャラクター名: {character_name}
原作名: {original_work}
同人作品タイトル: {title}
同人作品作者名: {author_name}
サークル名: {circle_name}

【FANZA公式サイトの商品紹介文】
{original_description}

【重要な制約】
- 生成する文章は、接頭辞（例: 「リード文:」「ストーリー/紹介文:」）やタイプ名を含まない、純粋な本文のみとしてください
- リード文（2～3行）: 読者の興味を引く導入文
- ストーリー/紹介文（200～400字）: 作品の魅力を伝える詳細な紹介文

【出力形式】
以下の形式で出力してください（「リード文:」「ストーリー/紹介文:」の接頭辞は絶対に含めないでください）：

（ここにリード文の内容のみを記載）

---

（ここにストーリー/紹介文の内容のみを記載）"""
    else:
        # フォールバック用の簡易プロンプト
        prompt = f"""以下の同人作品の紹介文を、より魅力的で読みやすい文章にリライトしてください。

【作品情報】
タイトル: {title}
サークル名: {circle_name}
原作: {original_work}
キャラクター: {character_name}

【元の紹介文】
{original_description}

【リライト要件】
- 読みやすく魅力的な文章にする
- 作品の魅力を伝える
- 300文字程度にまとめる
- 自然な日本語で書く
- 過度にエロティックな表現は避ける

リライトした紹介文のみを出力してください："""

    rewritten = await call_grok_api(prompt, max_tokens=600)
    
    # Grok APIの結果が空の場合のフォールバック
    if not rewritten:
        fallback_description = f"{title}は、{character_name}が登場する{original_work}の二次創作同人作品です。{circle_name}による魅力的な作品をお楽しみください。"
        print(f"Debug: Grok API失敗のため、フォールバック紹介文を使用: {fallback_description}")
        return fallback_description
    
    return rewritten

async def get_grok_rewritten_lead(original_lead, product_info, target_audience):
    """
    Grok APIでリード文を生成する（詳細プロンプト使用）
    """
    title = product_info.get('title', '')
    circle_name = product_info.get('circle_name', '')
    author_name = product_info.get('author_name', '')
    original_work = product_info.get('original_work', '')
    character_name = product_info.get('character_name', '')
    description = product_info.get('description', '')
    
    prompt = f"""以下の同人作品のリード文（導入文）を作成してください。

【作品情報】
キャラクター名: {character_name}
原作名: {original_work}
同人作品タイトル: {title}
同人作品作者名: {author_name}
サークル名: {circle_name}
紹介文: {description[:200]}...

【リード文要件】
- ' {character_name} 'が' {original_work} 'の世界観で魅力的な姿を見せる
- 読者の興味を引く導入文（2～3行）
- 期待感と好奇心を煽る、キャッチーで簡潔な表現
- 80文字程度
- 作品の魅力を簡潔に表現
- 自然な日本語で書く

リード文のみを出力してください："""

    lead = await call_grok_api(prompt, max_tokens=200)
    return lead if lead else (original_lead or description[:80])

async def get_grok_rewritten_seo_description(original_seo, product_info, target_audience):
    """
    Grok APIでSEO説明文を生成する（詳細プロンプト使用）
    """
    title = product_info.get('title', '')
    circle_name = product_info.get('circle_name', '')
    author_name = product_info.get('author_name', '')
    original_work = product_info.get('original_work', '')
    character_name = product_info.get('character_name', '')
    description = product_info.get('description', '')
    
    prompt = f"""以下の同人作品のSEO用メタディスクリプション（120文字以内）を作成してください。

【作品情報】
キャラクター名: {character_name}
原作名: {original_work}
同人作品タイトル: {title}
同人作品作者名: {author_name}
サークル名: {circle_name}
紹介文: {description[:200]}...

【SEO要件】
- 120文字以内
- 検索されやすいキーワードを含む（{character_name}、{original_work}、同人誌など）
- 作品の魅力を簡潔に表現
- 自然な日本語
- 成人向けコンテンツであることを適切に表現

SEO用メタディスクリプションのみを出力してください："""

    rewritten = await call_grok_api(prompt, max_tokens=250)
    return rewritten if rewritten else (description[:120] if description else f"{title}の同人作品情報")

async def get_grok_original_work_suggestion(product_info, sheet_original_work='', sheet_character=''):
    """
    Grok APIで原作名を推測する（詳細プロンプト使用・顔画像付き）
    """
    title = product_info.get('title', '')
    circle_name = product_info.get('circle_name', '')
    character_name = product_info.get('character_name', '')
    genres = product_info.get('genres', [])
    description = product_info.get('description', '')
    sample_images = product_info.get('sample_images', [])
    
    # OpenAI APIの拒否問題を回避するため、画像処理をスキップ
    face_images_info = ""
    print(f"Debug: OpenAI API拒否問題を回避するため、画像処理をスキップしてテキストのみで処理します")
    
    # 代替として、タイトルと説明文から特徴を推測
    if sample_images:
        face_images_info = f"\n\n【画像情報】\n{len(sample_images)}枚のサンプル画像が利用可能です。"
    
    # プロンプトテンプレートを読み込み
    prompt_template = load_prompt_template('grok_description_prompt.txt')
    
    if prompt_template and isinstance(prompt_template, dict):
        # YAML形式のプロンプトテンプレートの場合
        prompt_def = prompt_template.get('prompt_definition', {})
        assistant_role = prompt_def.get('assistant_role', 'あなたは高度な分析能力を持つAIアシスタントです。')
        task_description = prompt_def.get('task_description', '')
        
        # キャラクターバリデーションを実行
        validation_addition = CharacterValidator.get_validation_prompt_addition(
            sheet_character, sheet_original_work, title
        )
        
        prompt = f"""{assistant_role}

{task_description}

【ユーザーからの入力情報】
- 想定原作名: {sheet_original_work}
- 想定キャラクター名: {sheet_character}

【同人作品に関する情報】
- 商品タイトル: {title}
- 商品紹介文: {description}

{face_images_info}

【判定基準】
1. タイトルと紹介文から抽出できる原作名とキャラクター名を確認
2. ユーザーの想定する原作名とキャラクター名と比較
3. サンプル画像の顔の特徴が、ユーザーの想定するキャラクターの一般的な特徴と一致するか補足的に考慮（ただし、AI生成イラストのため特徴の一致は参考程度）
4. 一致/相違の結果と、相違がある場合は具体的な相違点（例: 原作が異なる、キャラ名が異なる）を明確に説明

{validation_addition}

【出力形式】
以下のJSON形式で回答してください。JSON以外のテキストは一切含めないでください：

{{
  "judgement_result": "一致" または "相違",
  "details": {{
    "on_match": "一致する場合の説明（なぜ一致しているか）",
    "on_mismatch": "相違する場合の説明（どの部分が異なるか、具体的な相違点）"
  }},
  "correct_original_work": "正しい原作名（相違がある場合）",
  "correct_character_name": "正しいキャラクター名（相違がある場合、フルネームで）"
}}

JSON形式で回答してください："""
    elif prompt_template:
        # 従来のテキスト形式のプロンプトテンプレートの場合
        prompt = f"""あなたは高度な分析能力を持つAIアシスタントです。

以下の情報を基に、指定された同人作品のキャラクターと原作が、ユーザーの想定するキャラクター名と原作名に一致しているか、または相違しているかを判定してください。相違がある場合は、どの点が異なるかを具体的に指摘してください。

【ユーザーからの入力情報】
- 想定原作名: {sheet_original_work}
- 想定キャラクター名: {sheet_character}

【同人作品に関する情報】
- 商品タイトル: {title}
- 商品紹介文: {description}

{face_images_info}

【判定基準】
1. タイトルと紹介文から抽出できる原作名とキャラクター名を確認
2. ユーザーの想定する原作名とキャラクター名と比較
3. サンプル画像の顔の特徴が、ユーザーの想定するキャラクターの一般的な特徴と一致するか補足的に考慮（ただし、AI生成イラストのため特徴の一致は参考程度）
4. 一致/相違の結果と、相違がある場合は具体的な相違点（例: 原作が異なる、キャラ名が異なる）を明確に説明

【出力形式】
以下のJSON形式で回答してください。JSON以外のテキストは一切含めないでください：

{{
  "judgement_result": "一致" または "相違",
  "details": {{
    "on_match": "一致する場合の説明（なぜ一致しているか）",
    "on_mismatch": "相違する場合の説明（どの部分が異なるか、具体的な相違点）"
  }},
  "correct_original_work": "正しい原作名（相違がある場合）",
  "correct_character_name": "正しいキャラクター名（相違がある場合、フルネームで）"
}}

JSON形式で回答してください："""
    else:
        # フォールバック用の簡易プロンプト（顔画像情報を追加）
        prompt = f"""以下の同人作品の情報から、原作（元ネタ）とキャラクター名を推測してください。

【作品情報】
タイトル: {title}
サークル名: {circle_name}
キャラクター名: {character_name}
ジャンル: {', '.join(genres[:5])}

{face_images_info}

【推測要件】
- タイトルやキャラクター名、顔画像の特徴から原作を推測
- 有名なアニメ、ゲーム、漫画などの作品名
- 女性キャラクター名を最大5名まで特定
- **キャラクター名は必ずフルネーム（姓＋名）で回答してください**
- **例: 「アスナ」ではなく「結城アスナ」、「美琴」ではなく「御坂美琴」**
- 確信がない場合は「オリジナル」と回答

**必ず以下のJSON形式のみで回答してください。他のテキストは一切含めないでください：**

{{
  "原作名": "推測された原作名",
  "キャラクター名リスト": ["キャラクター1のフルネーム", "キャラクター2のフルネーム", "キャラクター3のフルネーム"],
  "信頼度スコア": 0.8
}}"""

    # Grok APIにテキスト情報のみを送信（画像は送信しない）
    suggestion = await call_grok_api(prompt, max_tokens=600)
    return suggestion

def generate_article_content(details, main_image, gallery_images, url, grok_description=None, grok_lead=None, grok_seo=None):
    # デバッグ: 渡されたdetailsの内容を確認
    print(f"Debug generate_article_content: details = {details}")
    
    title = details.get('title', '')
    description = grok_description if grok_description else details.get('description', '')
    catch_copy = grok_lead if grok_lead else (details.get('catch_copy', '') or description[:80])
    seo_description = grok_seo if grok_seo else description[:120]
    circle_name = details.get('circle_name', '')
    author_name = details.get('author_name', '')
    original_work = details.get('original_work', '')
    character_name = details.get('character_name', '')
    product_format = details.get('product_format', '')
    page_count = details.get('page_count', '')
    
    # URLから品番（商品ID）を抽出
    product_id = ''
    product_id_match = re.search(r'cid=([^/&]+)', url)
    if product_id_match:
        product_id = product_id_match.group(1)
        print(f"Debug: 記事内容用品番抽出: {product_id}")
    else:
        print(f"Warning: 記事内容用URLから品番を抽出できませんでした: {url}")

    # デバッグ: 各フィールドの値を確認
    print(f"Debug: author_name = '{author_name}', product_format = '{product_format}', circle_name = '{circle_name}'")
    print(f"Debug: original_work = '{original_work}', character_name = '{character_name}', page_count = '{page_count}'")

    # 原作・キャラが特定できない場合の判定
    is_unknown_work_or_character = (
        not original_work or 
        original_work in ['不明', '不明（特定不可）', '不明（特定できず）', '不明（確定情報なし）', '不明（複数の原作が混在する可能性あり）', '不明（提供情報からは原作特定不可）', '不明（原作名が特定できない）'] or
        original_work.startswith('不明（推定：') or
        not character_name or 
        character_name in ['不明', '不明（特定不可）', '不明（特定できず）', '不明（確定情報なし）', '不明（フルネームの特定不可）', '不明（提供情報からはキャラクター特定不可）', '不明（キャラクター名が特定できない）']
    )
    
    print(f"Debug: 原作・キャラ特定状況 - 不明判定: {is_unknown_work_or_character}")

    # メイン画像のHTML（記事上部に表示）
    main_image_html = ""
    if main_image:
        main_image_html = f'''<!-- wp:html -->
<div style="text-align: center; margin: 20px 0;">
    <a href="{generate_affiliate_link(url)}" rel="nofollow noopener" target="_blank">
        <img src="{main_image}" alt="{title}" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); transition: transform 0.3s ease;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
    </a>
    <p style="font-size: 14px; color: #666; margin-top: 10px;">↑ 画像をクリックして詳細をチェック！</p>
</div>
<!-- /wp:html -->

'''

    # サンプル画像HTML（縦に1枚ずつ並べる、クリック無効）
    gallery_html = ""
    if gallery_images:
        for img in gallery_images:
            gallery_html += f'<!-- wp:html -->\n<figure class="wp-block-image size-large is-style-default" style="pointer-events: none; user-select: none;"><img src="{img}" alt="{title}のサンプル画像" class="wp-image" loading="lazy" style="pointer-events: none; cursor: default;"/></figure>\n<!-- /wp:html -->\n\n'

    # SWELLボタンHTML（完成版）
    affiliate_url = generate_affiliate_link(url)
    
    # アイキャッチ画像をクリック可能にするHTMLとボタン
    featured_image_html = ""
    if main_image:
        featured_image_html = f'''<!-- wp:html -->
<div style="text-align: center; margin: 20px 0;">
    <a href="{affiliate_url}" rel="nofollow noopener" target="_blank">
        <img src="{main_image}" alt="{title}" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); transition: transform 0.3s ease;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
    </a>
    <p style="font-size: 14px; color: #666; margin-top: 10px;">↑ 画像をクリックして詳細をチェック！</p>
</div>
<!-- /wp:html -->

'''
    
    button_html = f'<!-- wp:html -->\n<div class="swell-block-button red_ is-style-btn_solid"><a href="{affiliate_url}" class="swell-block-button__link" rel="nofollow noopener" target="_blank"><span>続きはコチラ</span></a></div>\n<!-- /wp:html -->'

    # 作品情報テーブル（原作・キャラ不明時は該当行を除外）
    table_rows = []
    
    # 品番（常に表示）
    if product_id:
        table_rows.append(f'<tr><th class="has-text-align-center" data-align="center">品番</th><td>{product_id}</td></tr>')
    
    # サークル名（優先表示）
    if circle_name:
        circle_link = f'<a href="/circle_name/{quote(circle_name)}/">{circle_name}</a>'
        table_rows.append(f'<tr><th class="has-text-align-center" data-align="center">サークル名</th><td>{circle_link}</td></tr>')
    
    # 作者名（常に表示）
    if author_name:
        author_link = f'<a href="/tag/{quote(author_name)}/">{author_name}</a>'
        table_rows.append(f'<tr><th class="has-text-align-center" data-align="center">作者名</th><td>{author_link}</td></tr>')
    
    # 原作名（特定できた場合のみ表示）
    if not is_unknown_work_or_character and original_work:
        original_work_link = f'<a href="/original_work/{quote(original_work)}/">{original_work}</a>'
        table_rows.append(f'<tr><th class="has-text-align-center" data-align="center">原作名</th><td>{original_work_link}</td></tr>')
    
    # キャラ名（特定できた場合のみ表示）
    if not is_unknown_work_or_character and character_name:
        character_link = f'<a href="/character_name/{quote(character_name)}/">{character_name}</a>'
        table_rows.append(f'<tr><th class="has-text-align-center" data-align="center">キャラ名</th><td>{character_link}</td></tr>')
    
    # 作品形式（常に表示）
    if product_format:
        format_link = f'<a href="/product_format/{quote(product_format)}/">{product_format}</a>'
        table_rows.append(f'<tr><th class="has-text-align-center" data-align="center">作品形式</th><td>{format_link}</td></tr>')
    
    # 価格（新規追加）
    if details.get('price'):
        price_display = f"{details['price']}円"
        table_rows.append(f'<tr><th class="has-text-align-center" data-align="center">価格</th><td>{price_display}</td></tr>')
    
    # ページ数（常に表示）
    page_display = f'{page_count}ページ' if page_count else '不明'
    table_rows.append(f'<tr><th class="has-text-align-center" data-align="center">ページ数</th><td>{page_display}</td></tr>')
    
    # 販売日（新規追加）
    if details.get('sale_date'):
        table_rows.append(f'<tr><th class="has-text-align-center" data-align="center">販売日</th><td>{details["sale_date"]}</td></tr>')
    
    # テーブルHTML生成（最低3行必要）
    if len(table_rows) < 3:
        genres_text = '、'.join(details.get("genres", ["不明"]))
        table_rows.append(f'<tr><th class="has-text-align-center" data-align="center">ジャンル</th><td>{genres_text}</td></tr>')
    
    info_table = f'<!-- wp:table {{"className":"is-style-regular"}} -->\n<figure class="wp-block-table is-style-regular"><table><tbody>\n{chr(10).join(table_rows)}\n</tbody></table></figure>\n<!-- /wp:table -->'

    # 無料で読める？セクションの生成（SEO強化版）
    free_reading_section = generate_free_reading_section(title, original_work, character_name)
    
    # 記事本文の構築（ブロックエディタ対応）
    content = f'{main_image_html}<!-- wp:paragraph -->\n<p>{catch_copy}</p>\n<!-- /wp:paragraph -->\n\n<!-- wp:heading -->\n<h2>作品情報</h2>\n<!-- /wp:heading -->\n\n{info_table}\n\n<!-- wp:heading -->\n<h2>サンプル画像</h2>\n<!-- /wp:heading -->\n\n{gallery_html}<!-- wp:heading -->\n<h2>作品紹介</h2>\n<!-- /wp:heading -->\n\n<!-- wp:paragraph -->\n<p>{description}</p>\n<!-- /wp:paragraph -->\n\n{featured_image_html}{button_html}\n\n{free_reading_section}'

    return content, seo_description

async def process_product(ss, row_idx, row, url):
    # グローバル変数の宣言
    global global_last_scheduled_time
    
    # タイムゾーンの設定
    jst = timezone(timedelta(hours=9), 'Asia/Tokyo')
    
    try:
        # 【重要】処理開始前の重複チェック
        current_status = str(row[0]).strip() if row[0] else ''
        post_url = row[6] if len(row) > 6 else ''
        scheduled_date = row[5] if len(row) > 5 else ''
        
        print(f"🔍 重複チェック開始 - Row {row_idx}")
        print(f"   現在のステータス: '{current_status}'")
        print(f"   記事URL: '{post_url}'")
        print(f"   予約投稿日時: '{scheduled_date}'")
        
        # 処理済み商品の重複チェック
        excluded_statuses = {
            '予約投稿', '投稿済み', '投稿完了', '公開済み', '処理済み', 
            '下書き保存', '下書き', 'draft', 'published', 'scheduled'
        }
        
        if current_status in excluded_statuses:
            print(f"⚠️  重複処理防止: Row {row_idx} は既に処理済み（ステータス: {current_status}）")
            return False
            
        if post_url and str(post_url).strip():
            print(f"⚠️  重複処理防止: Row {row_idx} は既に記事URLが設定済み（{post_url}）")
            return False
            
        if scheduled_date and str(scheduled_date).strip():
            print(f"⚠️  重複処理防止: Row {row_idx} は既に予約投稿日時が設定済み（{scheduled_date}）")
            return False
        
        # 【新機能】WordPress側の既存投稿チェック
        print(f"🔍 WordPress側重複チェック開始 - Row {row_idx}")
        
        # URLから商品IDを抽出
        product_id = extract_product_id_from_url(url)
        if product_id:
            wp_poster = WordPressPoster(WP_URL, WP_USERNAME, WP_APP_PASSWORD)
            
            # スラッグ（商品ID）で既存投稿をチェック（一時的にスキップ）
            # existing_post = await wp_poster.check_existing_post_by_slug(product_id)
            existing_post = None  # 重複チェックを一時的にスキップ
            if existing_post:
                print(f"⚠️  WordPress重複投稿発見: Row {row_idx}")
                print(f"   既存投稿ID: {existing_post['id']}")
                print(f"   既存投稿タイトル: {existing_post['title']}")
                print(f"   既存投稿ステータス: {existing_post['status']}")
                print(f"   既存投稿URL: {existing_post['link']}")
                
                # スプレッドシートに既存投稿情報を記録
                while len(row) < 9:
                    row.append('')
                
                row[0] = '重複投稿'  # ステータス
                row[6] = existing_post['link']  # 記事URL
                row[7] = datetime.now(jst).strftime('%m/%d %H:%M')  # 最終処理日時
                row[8] = f"WordPress既存投稿発見 (ID: {existing_post['id']})"  # エラー詳細
                
                ss.update_row(ss.product_sheet, row_idx, row)
                print(f"✅ 重複投稿情報をスプレッドシートに記録完了")
                return False
        
        print(f"✅ 重複チェック通過 - Row {row_idx} の処理を開始")
        
        # Debug: scrape_fanza_product_details 関数に渡す直前のURL
        print(f"Debug in process_product: Calling scrape_fanza_product_details with URL: {url}")
        
        # スプレッドシートから原作名とキャラ名を取得（存在する場合）
        sheet_original_work = row[1] if len(row) > 1 else ''  # B列: 原作名
        sheet_character = row[2] if len(row) > 2 else ''      # C列: キャラ名
        
        print(f"Debug: スプレッドシート情報 - 原作: '{sheet_original_work}', キャラ: '{sheet_character}'")
        
        # 詳細情報取得（スプレッドシートの情報も渡す）
        details = await fanza_scraper.scrape_fanza_product_details(url, sheet_original_work, sheet_character)
        
        # 商品データの品質チェック
        validation_result_data = validate_product_data(details)
        print(f"📊 データ品質チェック結果:")
        print(f"   品質スコア: {validation_result_data['quality_score']}%")
        print(f"   エラー: {len(validation_result_data['errors'])}件")
        print(f"   警告: {len(validation_result_data['warnings'])}件")
        
        # エラーがある場合は詳細ログを出力
        if validation_result_data['errors']:
            print(f"❌ データ品質エラー:")
            for error in validation_result_data['errors']:
                print(f"   - {error}")
        
        if validation_result_data['warnings']:
            print(f"⚠️  データ品質警告:")
            for warning in validation_result_data['warnings']:
                print(f"   - {warning}")
        
        # 重大なエラーがある場合は処理を中断
        if not validation_result_data['is_valid']:
            print(f"❌ 商品データが不完全なため処理を中断します")
            ss.update_cell(row_idx, 1, '❌データ不完全')
            return
        
        # 【重要】事前フィルタリングによる原作相違・キャラクター相違チェック
        excluded_by_prefilter = False
        excluded_reason = ''
        
        if sheet_original_work and details.get('title'):
            filter_result = PreFilter.should_exclude_product(
                details['title'], 
                sheet_original_work, 
                sheet_character
            )
            
            if filter_result['action'] == 'exclude':
                print(f"⚠️  事前フィルタリングで除外: {filter_result['reason']}")
                print(f"🔄 除外されましたが、下書き保存として処理を継続します")
                
                # 事前フィルタリングで除外された場合、強制的に下書き保存フラグを設定
                excluded_by_prefilter = True
                excluded_reason = filter_result['reason']
                
                # 処理を継続（return Falseしない）
                print("Debug: 事前フィルタリング除外時も通常の処理フローを継続します")
                
            elif filter_result['action'] == 'correct_character':
                print(f"🔧 キャラクター名を自動修正: {filter_result['reason']}")
                
                # スプレッドシートのキャラクター名を修正
                original_character = sheet_character
                corrected_character = filter_result['detected_character']
                
                # 行データの列数を確認し、必要に応じて拡張
                while len(row) < 9:
                    row.append('')
                
                # キャラクター名を修正
                row[2] = corrected_character  # C列: キャラ名を修正
                sheet_character = corrected_character  # 以降の処理で使用するキャラ名も更新
                
                print(f"✓ キャラクター名を修正: 「{original_character}」→「{corrected_character}」")
                print(f"✓ 修正後、通常の投稿処理を継続します")
        
        # AI分析の並列処理（Grok + Gemini同時実行）
        print("Debug: AI分析を並列実行中...")
        try:
            # GrokとGeminiを同時実行
            grok_task = get_grok_original_work_suggestion(details, sheet_original_work, sheet_character)
            
            # Geminiはキャラクター分析のみ実行
            gemini_task = None
            if details.get('sample_images'):  # 画像がある場合のみGemini実行
                from src.core.gemini.analyzer import Gemini_Analyzer
                gemini_analyzer = Gemini_Analyzer()
                gemini_task = gemini_analyzer.analyze_character_from_images(
                    details['sample_images'][:3], details
                )
            
            # 並列実行
            if gemini_task:
                grok_suggestion, gemini_result = await asyncio.gather(
                    grok_task, gemini_task, return_exceptions=True
                )
                print(f"Debug: Gemini結果 - {gemini_result.get('character_name', '不明') if isinstance(gemini_result, dict) else 'エラー'}")
            else:
                grok_suggestion = await grok_task
                gemini_result = None
                print("Debug: 画像がないためGemini分析をスキップ")
                
        except Exception as e:
            print(f"Warning: AI分析でエラー: {e}")
            grok_suggestion = None
            gemini_result = None
        
        # Grokの推測結果とスプレッドシートの情報を照合
        validation_result = validate_grok_results_with_sheet(grok_suggestion, sheet_original_work, sheet_character)
        
        print(f"Debug: 照合結果 - {validation_result['match_reason']}")
        
        # 照合結果に基づいて原作名・キャラクター名を設定
        details['original_work'] = validation_result['validated_original_work']
        details['character_name'] = ', '.join(validation_result['validated_characters']) if validation_result['validated_characters'] else ''
        
        print(f"Debug: 最終設定 - 原作: '{details['original_work']}', キャラ: '{details['character_name']}'")
        
        # 画像処理の改善
        main_image = details.get('main_image', '')
        sample_images = details.get('sample_images', [])
        
        # 最適化された画像検証（キャッシュ付き並列処理）
        if sample_images:
            valid_sample_images = await fanza_scraper.verify_image_urls_optimized(sample_images)
        else:
            valid_sample_images = []
        
        # サンプル画像の数を制限
        if len(valid_sample_images) > MAX_SAMPLE_IMAGES:
            valid_sample_images = valid_sample_images[:MAX_SAMPLE_IMAGES]
            print(f"Debug: サンプル画像を{MAX_SAMPLE_IMAGES}枚に制限しました")
        
        # メイン画像が空の場合、最初のサンプル画像を使用
        if not main_image and valid_sample_images:
            main_image = valid_sample_images[0]
            valid_sample_images = valid_sample_images[1:]  # 残りをギャラリー用に
        
        # ギャラリー画像の設定
        gallery_images = valid_sample_images
        
        print(f"Debug: 最終的な画像設定")
        print(f"Debug: Main Image: {main_image}")
        print(f"Debug: Gallery Images: {len(gallery_images)} images")
        if gallery_images:
            print(f"Debug: Gallery Images URLs: {gallery_images[:3]}...")  # 最初の3つだけ表示

        # Grok APIでコンテンツ生成（並列実行）
        print("Debug: Grokコンテンツ生成を並列実行中...")
        try:
            # Grokのコンテンツ生成を並列実行
            description_task = get_grok_rewritten_description(
                details.get('description', ''), details, target_audience={}
            )
            lead_task = get_grok_rewritten_lead(
                details.get('catch_copy', '') or details.get('description', ''), details, target_audience={}
            )
            seo_task = get_grok_rewritten_seo_description(
                details.get('description', ''), details, target_audience={}
            )
            
            # 並列実行
            grok_description, grok_lead, grok_seo = await asyncio.gather(
                description_task, lead_task, seo_task, return_exceptions=True
            )
            
            # エラーハンドリング
            if isinstance(grok_description, Exception):
                print(f"Warning: Grok説明文生成エラー: {grok_description}")
                grok_description = details.get('description', '')
            if isinstance(grok_lead, Exception):
                print(f"Warning: Grokリード文生成エラー: {grok_lead}")
                grok_lead = details.get('catch_copy', '') or details.get('description', '')[:80]
            if isinstance(grok_seo, Exception):
                print(f"Warning: GrokSEO説明文生成エラー: {grok_seo}")
                grok_seo = details.get('description', '')[:120]
                
        except Exception as e:
            print(f"Warning: Grokコンテンツ生成でエラー: {e}")
            grok_description = details.get('description', '')
            grok_lead = details.get('catch_copy', '') or details.get('description', '')[:80]
            grok_seo = details.get('description', '')[:120]
        
        # 投稿ステータスを照合結果に基づいて決定（最初に定義）
        # 事前フィルタリングで除外された場合は強制的に下書き保存
        if excluded_by_prefilter:
            is_scheduled_post = False
            post_status = 'draft'
            status_text = '下書き保存'
            print(f"Debug: 事前フィルタリング除外のため強制下書き保存")
        else:
            is_scheduled_post = validation_result.get('is_match', False)
            post_status = 'future' if is_scheduled_post else 'draft'
            status_text = '予約投稿' if is_scheduled_post else '下書き保存'
        
        print(f"Debug: 投稿ステータス - {status_text} ({validation_result.get('match_reason', excluded_reason)})")
        
        # 投稿テンプレート生成
        article_content, seo_description = generate_article_content(details, main_image, gallery_images, url, grok_description, grok_lead, grok_seo)

        # 投稿予約時間を計算（グローバル最終予約時間を考慮）
        base_time = datetime.now(jst)
        
        if is_scheduled_post:
            # 基準時間を決定（グローバル最終予約時間 > スプレッドシート > WordPress の優先順位）
            reference_times = []
            
            # グローバル最終予約時間を最優先
            if global_last_scheduled_time:
                reference_times.append(global_last_scheduled_time)
                print(f"Debug: グローバル最終予約時間: {global_last_scheduled_time}")
            
            # スプレッドシートの最終予約投稿時間を取得
            sheet_last_time = ss.get_last_scheduled_time()
            if sheet_last_time:
                # スプレッドシートの時間をJSTに変換（年が設定されていない場合は現在年を使用）
                if sheet_last_time.year == datetime.now().year:
                    reference_times.append(sheet_last_time)
                else:
                    # 年が古い場合は現在年に更新
                    updated_time = sheet_last_time.replace(year=datetime.now().year)
                    reference_times.append(updated_time)
                print(f"Debug: スプレッドシート最終予約時間: {sheet_last_time}")
            
            # WordPressの最終予約投稿時間を取得
            wp_poster = WordPressPoster(WP_URL, WP_USERNAME, WP_APP_PASSWORD)
            wp_last_time = await wp_poster.get_last_scheduled_post_time()
            if wp_last_time:
                # WordPressの時間をJSTに変換
                wp_last_time_jst = wp_last_time.replace(tzinfo=None) + timedelta(hours=9)
                reference_times.append(wp_last_time_jst)
                print(f"Debug: WordPress最終予約時間: {wp_last_time} (JST: {wp_last_time_jst})")
            
            if reference_times:
                # 最新の時間から1時間後に設定
                latest_time = max(reference_times)
                scheduled_time = latest_time + timedelta(hours=1)
                print(f"Debug: 基準時間: {latest_time}, 予約時間: {scheduled_time.strftime('%m/%d %H:%M')}")
            else:
                # 基準時間がない場合は現在時刻から1時間後
                scheduled_time = base_time + timedelta(hours=1)
                print(f"Debug: 基準時間なし、現在時刻から1時間後に設定: {scheduled_time.strftime('%m/%d %H:%M')}")
            
            # グローバル最終予約時間を更新
            global_last_scheduled_time = scheduled_time
            print(f"Debug: グローバル最終予約時間を更新: {global_last_scheduled_time.strftime('%m/%d %H:%M')}")
        else:
            scheduled_time = base_time  # 下書き保存は現在時刻
            print(f"Debug: 下書き保存のため投稿時間は現在時刻を使用")
        
        # WordPress REST API用の日時フォーマット（ISO 8601形式）
        wordpress_date = scheduled_time.strftime('%Y-%m-%dT%H:%M:%S')
        
        # キャラクター名をタグとカスタムタクソノミーに設定
        character_tags = validation_result['validated_characters'][:5]  # 最大5名
        character_taxonomy = ', '.join(character_tags) if character_tags else ''
        
        # URLから品番（商品ID）を抽出
        product_id = ''
        product_id_match = re.search(r'cid=([^/&]+)', url)
        if product_id_match:
            product_id = product_id_match.group(1)
            print(f"Debug: 抽出された品番: {product_id}")
        else:
            print(f"Warning: URLから品番を抽出できませんでした: {url}")
        
        # カテゴリとタグの準備
        # カテゴリ：作者・サークル名
        categories = []
        if details.get('author_name'):
            categories.append(details['author_name'])
        if details.get('circle_name') and details.get('circle_name') != details.get('author_name'):
            categories.append(details['circle_name'])
        
        # タグ：ジャンル、シチュエーション
        tags = []
        # FANZAのジャンルをタグに追加
        if details.get('genres'):
            tags.extend(details['genres'])
        
        print(f"Debug: カテゴリ設定 - {categories}")
        print(f"Debug: タグ設定 - {tags}")
        
        # 原作・キャラが特定できない場合の判定
        is_unknown_work_or_character = (
            not details.get('original_work') or 
            details.get('original_work') in ['不明', '不明（特定不可）', '不明（特定できず）', '不明（確定情報なし）', '不明（複数の原作が混在する可能性あり）', '不明（提供情報からは原作特定不可）', '不明（原作名が特定できない）'] or
            details.get('original_work', '').startswith('不明（推定：') or
            not details.get('character_name') or 
            details.get('character_name') in ['不明', '不明（特定不可）', '不明（特定できず）', '不明（確定情報なし）', '不明（フルネームの特定不可）', '不明（提供情報からはキャラクター特定不可）', '不明（キャラクター名が特定できない）']
        )
        
        # カスタムタクソノミーの設定（原作・キャラが特定できた場合のみ）
        custom_taxonomies = {}
        
        # 作品形式は常に設定
        if details.get('product_format'):
            custom_taxonomies['product_format'] = details.get('product_format', '')
        
        # 原作・キャラが特定できた場合のみ設定
        if not is_unknown_work_or_character:
            if details.get('original_work'):
                custom_taxonomies['original_work'] = details.get('original_work', '')
            if character_taxonomy:
                custom_taxonomies['character_name'] = character_taxonomy
        
        print(f"Debug: カスタムタクソノミー設定 - 不明判定: {is_unknown_work_or_character}, 設定項目: {list(custom_taxonomies.keys())}")

        # アイキャッチ画像の事前アップロード
        featured_media_id = None
        if main_image:
            print(f"🖼️  アイキャッチ画像の事前アップロード開始 - URL: {main_image}")
            try:
                wp_poster = WordPressPoster(WP_URL, WP_USERNAME, WP_APP_PASSWORD)
                featured_media_id = await wp_poster.upload_media_from_url(main_image, f"featured_{hash(url) % 10000}.jpg")
                if featured_media_id:
                    print(f"✅ アイキャッチ画像アップロード成功 - Media ID: {featured_media_id}")
                else:
                    print(f"⚠️  アイキャッチ画像アップロード失敗")
            except Exception as e:
                print(f"⚠️  アイキャッチ画像アップロード中にエラー: {str(e)}")

        # 記事タイトルの生成（商品名【キャラ名】形式）
        article_title = clean_title(details['title'])  # タイトルをクリーニング
        
        # キャラクター名が特定できている場合は【キャラ名】を追加
        if character_taxonomy and not is_unknown_work_or_character:
            # 複数キャラクターの場合は最初のキャラクター名のみ使用
            first_character = validation_result['validated_characters'][0] if validation_result['validated_characters'] else character_taxonomy.split(',')[0].strip()
            article_title = f"{clean_title(details['title'])}【{first_character}】"
            print(f"📝 記事タイトル生成: {article_title}")
        else:
            print(f"📝 記事タイトル（キャラ名なし）: {article_title}")

        # WordPress投稿データの準備
        post_data = {
            'title': article_title,  # 商品名【キャラ名】形式のタイトル
            'content': article_content,
            'status': post_status,  # 照合結果に基づく投稿ステータス
            'date': wordpress_date,
            'slug': product_id,  # 品番をスラッグに設定
            'categories': categories,  # 作者・サークル名をカテゴリに設定
            'tags': tags,  # ジャンル、シチュエーションをタグに設定
            'custom_taxonomies': custom_taxonomies,  # 原作・キャラが特定できた場合のみ設定
            'featured_media_id': featured_media_id  # アイキャッチ画像IDを追加
        }
        
        # 投稿データの詳細ログ
        print(f"📋 WordPress投稿データ詳細:")
        print(f"   タイトル: {article_title}")
        print(f"   投稿ステータス: {post_status}")
        print(f"   投稿日時: {wordpress_date}")
        print(f"   品番（スラッグ）: {product_id}")
        print(f"   カテゴリ数: {len(categories)}")
        print(f"   タグ数: {len(tags)}")
        print(f"   カスタムタクソノミー: {list(custom_taxonomies.keys())}")
        print(f"   アイキャッチ画像ID: {featured_media_id}")
        print(f"   コンテンツ長: {len(article_content)}文字")
        
        # コンテンツの構成要素チェック
        content_elements = []
        if 'wp:image' in article_content:
            content_elements.append('画像')
        if 'wp:table' in article_content:
            content_elements.append('テーブル')
        if 'wp:button' in article_content:
            content_elements.append('ボタン')
        if 'wp:heading' in article_content:
            content_elements.append('見出し')
        print(f"   コンテンツ構成要素: {', '.join(content_elements) if content_elements else 'なし'}")

        # WordPressに投稿
        print(f"Debug: WordPress認証情報確認")
        print(f"Debug: WP_URL = {WP_URL}")
        print(f"Debug: WP_USERNAME = {WP_USERNAME}")
        print(f"Debug: WP_APP_PASSWORD = {'設定済み' if WP_APP_PASSWORD else '未設定'}")
        
        if not all([WP_URL, WP_USERNAME, WP_APP_PASSWORD]):
            error_message = f"WordPress APIの認証情報が設定されていません - URL: {'設定済み' if WP_URL else '未設定'}, Username: {'設定済み' if WP_USERNAME else '未設定'}, Password: {'設定済み' if WP_APP_PASSWORD else '未設定'}"
            print(f"Error: {error_message}")
            raise ValueError(error_message)
        
        if not wp_poster:
            wp_poster = WordPressPoster(WP_URL, WP_USERNAME, WP_APP_PASSWORD)
        post_response = await wp_poster.create_post(post_data)

        if post_response and 'id' in post_response:
            # アイキャッチ画像の最終確認
            if featured_media_id:
                result_featured_media = post_response.get('featured_media', 0)
                if result_featured_media == featured_media_id:
                    print(f"✅ アイキャッチ画像設定確認完了 - Post ID: {post_response['id']}, Media ID: {featured_media_id}")
                else:
                    print(f"⚠️  アイキャッチ画像の最終確認で不一致 - 期待: {featured_media_id}, 実際: {result_featured_media}")
            else:
                print(f"ℹ️  メイン画像がないため、アイキャッチ画像なしで投稿")
            # 投稿成功時の処理
            post_url = post_response.get('link', '')
            print(f"Success: Posted to WordPress as {status_text}. URL: {post_url}")
            
            # 行データの列数を確認し、必要に応じて拡張
            while len(row) < 9:  # 必要な列数は9（0-8のインデックス）
                row.append('')
            
            # スプレッドシートの更新
            if excluded_by_prefilter:
                row[0] = '下書き保存'  # ステータスを更新
                row[5] = ''  # 予約日時はクリア
                row[8] = f"事前フィルタリングで除外: {excluded_reason}"  # 除外理由を記録
                print(f"📝 事前フィルタリング除外のため下書き保存として処理")
            elif validation_result['is_match']:
                row[0] = '予約投稿'  # ステータスを更新
                row[5] = scheduled_time.strftime('%m/%d %H:%M')  # F列: 予約投稿日時をMM/DD hh:mm形式
                row[8] = validation_result['match_reason']  # 照合結果の理由を記録
                print(f"✅ 予約投稿として処理: {scheduled_time.strftime('%m/%d %H:%M')}")
            else:
                row[0] = '下書き保存'  # ステータスを更新
                row[5] = ''  # 予約日時はクリア
                row[8] = validation_result['match_reason']  # 照合結果の理由を記録
                print(f"📝 下書き保存として処理（投稿時間カウントに含めない）")
            
            row[6] = f'=HYPERLINK("{post_url}", "{post_response["id"]}")'  # 記事URLを更新
            row[7] = datetime.now(jst).strftime('%m/%d %H:%M')  # H列: 最終処理日時をMM/DD hh:mm形式
            
            # 照合結果に基づいてスプレッドシートの原作名・キャラ名を更新
            # 一致・不一致に関わらず、Grokの推定結果でスプレッドシートを更新
            if validation_result['validated_original_work'] or validation_result['validated_characters']:
                # Grokの推定結果でスプレッドシートを更新
                if validation_result['validated_original_work']:
                    row[1] = validation_result['validated_original_work']  # B列: 原作名
                    print(f"Debug: 原作名を更新: {validation_result['validated_original_work']}")
                
                if validation_result['validated_characters']:
                    row[2] = ', '.join(validation_result['validated_characters'][:5])  # C列: キャラ名（最大5名）
                    print(f"Debug: キャラ名を更新: {', '.join(validation_result['validated_characters'][:5])}")
                
                # 一致した場合のみキーワード管理シートに追加
                if validation_result['is_match']:
                    print("Debug: キーワード管理シートに新しいキャラクター情報を追加中...")
                    try:
                        ss.add_character_to_keywords(
                            validation_result['validated_original_work'],
                            validation_result['validated_characters']
                        )
                        print("Debug: キーワード管理シートへの追加処理完了")
                    except Exception as e:
                        print(f"Warning: キーワード管理シートへの追加中にエラー: {str(e)}")
            
            # グローバル最終予約時間を更新（予約投稿の場合のみ）
            if validation_result['is_match'] and not excluded_by_prefilter:
                global_last_scheduled_time = scheduled_time
                print(f"🕐 グローバル最終予約時間を更新: {scheduled_time.strftime('%m/%d %H:%M')}")
            
            # E列（商品名）が空の場合は設定
            if len(row) <= 4 or not row[4]:  # E列が存在しないか空の場合
                # 行データの列数を確認し、必要に応じて拡張
                while len(row) < 5:  # E列まで確保
                    row.append('')
                row[4] = details['title']  # E列: 商品名
                print(f"Debug: E列（商品名）を設定: {details['title']}")
            else:
                print(f"Debug: E列（商品名）は既に設定済み、書き換えをスキップ: {row[4]}")
            
            ss.update_row(ss.product_sheet, row_idx, row)
            
            # 予約投稿の場合のみTrueを返す（投稿時間カウントに含める）
            return validation_result['is_match']
        else:
            # 投稿失敗時の処理
            error_message = "WordPress投稿に失敗しました"
            print(f"Error: {error_message}")
            
            # 行データの列数を確認し、必要に応じて拡張
            while len(row) < 9:
                row.append('')
            
            # スプレッドシートにエラー情報を記録
            row[0] = 'エラー'
            row[7] = datetime.now(jst).strftime('%m/%d %H:%M')
            row[8] = error_message
            ss.update_row(ss.product_sheet, row_idx, row)
            
            return False

    except Exception as e:
        # エラー発生時の処理
        error_message = str(e)
        print(f"Error in process_product: {error_message}")
        
        # 行データの列数を確認し、必要に応じて拡張
        while len(row) < 9:
            row.append('')
        
        # スプレッドシートにエラー情報を記録
        row[0] = 'エラー'
        row[7] = datetime.now(jst).strftime('%m/%d %H:%M')
        row[8] = error_message
        ss.update_row(ss.product_sheet, row_idx, row)
        
        return False

def validate_grok_results_with_sheet(grok_result, sheet_original_work, sheet_character):
    """
    Grokの推測結果とスプレッドシートの情報を照合する（JSON形式に依存しない設計）
    
    Args:
        grok_result: OpenAI APIからの推測結果（JSON文字列またはテキスト）
        sheet_original_work: スプレッドシートの原作名
        sheet_character: スプレッドシートのキャラ名
    
    Returns:
        dict: {
            'is_match': bool,  # 一致するかどうか
            'validated_original_work': str,  # 検証済み原作名
            'validated_characters': list,  # 検証済みキャラクター名リスト（最大5名）
            'match_reason': str  # 一致/不一致の理由
        }
    """
    try:
        print(f"Debug: OpenAI結果の型: {type(grok_result)}")
        print(f"Debug: OpenAI結果の内容: {grok_result}")
        
        # 1. API呼び出し失敗の場合
        if grok_result is None:
            print("Warning: OpenAI API呼び出し失敗")
            return create_fallback_result(sheet_original_work, sheet_character, 'OpenAI API呼び出し失敗')
        
        # 2. 空の応答の場合
        if not grok_result or (isinstance(grok_result, str) and not grok_result.strip()):
            print("Warning: OpenAI APIから空の応答")
            return create_fallback_result(sheet_original_work, sheet_character, 'OpenAI APIから空の応答')
        
        # 3. 応答内容の解析
        grok_data = None
        
        if isinstance(grok_result, str):
            # 3-1. JSON形式の解析を試行
            grok_data = try_parse_json(grok_result)
            
            # 3-2. JSON解析に失敗した場合、正規表現ベースの抽出を試行
            if grok_data is None:
                print("Debug: JSON解析失敗、正規表現ベースの抽出を試行...")
                grok_data = extract_info_from_text_response(grok_result)
                
                if grok_data is None:
                    print("Debug: 正規表現ベースの抽出も失敗")
                    return create_fallback_result(sheet_original_work, sheet_character, 
                                                'OpenAI応答から情報抽出失敗（JSON・正規表現の両方で失敗）')
        elif isinstance(grok_result, dict):
            # 既にdict形式の場合
            grok_data = grok_result
        else:
            print(f"Warning: 予期しないデータ型: {type(grok_result)}")
            return create_fallback_result(sheet_original_work, sheet_character, 
                                        f'予期しないデータ型: {type(grok_result)}')
        
        # 4. 抽出されたデータから原作名とキャラクター名を取得
        grok_original, grok_characters = extract_work_and_characters(grok_data)
        
        print(f"Debug: 抽出結果 - 原作: '{grok_original}', キャラ: {grok_characters}")
        print(f"Debug: スプレッドシート - 原作: '{sheet_original_work}', キャラ: '{sheet_character}'")
        
        # 5. 照合処理
        original_match = check_original_work_match(grok_original, sheet_original_work)
        character_match = check_character_match(grok_characters, sheet_character)
        
        # 6. 結果の構築
        return build_validation_result(
            original_match, character_match, 
            grok_original, grok_characters,
            sheet_original_work, sheet_character
        )
        
    except Exception as e:
        print(f"Error: OpenAI結果の照合中にエラー: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return create_fallback_result(sheet_original_work, sheet_character, f'照合処理エラー: {str(e)}')

def create_fallback_result(sheet_original_work, sheet_character, reason):
    """フォールバック結果を作成"""
    # スプレッドシートに情報がある場合は一致として扱う
    has_sheet_info = bool(sheet_original_work and sheet_character)
    return {
        'is_match': has_sheet_info,
        'validated_original_work': sheet_original_work or '',
        'validated_characters': [sheet_character] if sheet_character else [],
        'match_reason': f"{reason} - スプレッドシート情報{'を採用' if has_sheet_info else 'なし'}"
    }

def try_parse_json(text_response):
    """JSON解析を試行（複数のパターンに対応）"""
    if not text_response:
        return None
    
    # パターン1: 完全なJSON形式
    try:
        return json.loads(text_response)
    except json.JSONDecodeError:
        pass
    
    # パターン2: JSON部分を抽出
    if '{' in text_response and '}' in text_response:
        json_start = text_response.find('{')
        json_end = text_response.rfind('}') + 1
        json_str = text_response[json_start:json_end]
        
        try:
            result = json.loads(json_str)
            print(f"Debug: JSON部分抽出成功: {json_str[:100]}...")
            return result
        except json.JSONDecodeError as e:
            print(f"Debug: JSON部分抽出も失敗: {str(e)}")
    
    # パターン3: 複数のJSONブロックがある場合（最初のものを使用）
    json_blocks = re.findall(r'\{[^{}]*\}', text_response)
    for block in json_blocks:
        try:
            result = json.loads(block)
            print(f"Debug: JSONブロック抽出成功: {block}")
            return result
        except json.JSONDecodeError:
            continue
    
    print(f"Debug: すべてのJSON解析パターンが失敗")
    return None

def extract_work_and_characters(grok_data):
    """データから原作名とキャラクター名を抽出（新しいプロンプト形式対応）"""
    if not grok_data or not isinstance(grok_data, dict):
        return '', []
    
    # 新しいプロンプト形式（judgement_result）に対応
    if 'judgement_result' in grok_data:
        judgement_result = grok_data.get('judgement_result', '相違')
        is_match = judgement_result == '一致'
        
        print(f"Debug: 新しいプロンプト形式を検出 - 判定結果: {judgement_result}")
        
        if is_match:
            # 一致の場合は、元のスプレッドシート情報を使用
            print(f"Debug: 一致のため、スプレッドシート情報を使用")
            return '', []  # 空を返して、呼び出し元でスプレッドシート情報を使用
        else:
            # 相違の場合は、正しい情報を使用
            correct_original = grok_data.get('correct_original_work', '').strip()
            correct_character = grok_data.get('correct_character_name', '').strip()
            
            # 「不明」系の表記を統一
            if correct_original in ['不明（特定不可）', '不明（特定できず）', '不明（確定情報なし）', '不明（複数の原作が混在する可能性あり）', '不明（提供情報からは原作特定不可）', '不明（原作名が特定できない）'] or correct_original.startswith('不明（推定：'):
                correct_original = '不明'
            if correct_character in ['不明（特定不可）', '不明（特定できず）', '不明（確定情報なし）', '不明（フルネームの特定不可）', '不明（提供情報からはキャラクター特定不可）', '不明（キャラクター名が特定できない）']:
                correct_character = '不明'
            
            correct_characters = [correct_character] if correct_character else []
            print(f"Debug: 相違のため正しい情報を使用 - 原作: '{correct_original}', キャラ: {correct_characters}")
            return correct_original, correct_characters
    
    # 旧形式（原作の一致/キャラクターの一致）に対応
    elif '原作の一致' in grok_data or 'キャラクターの一致' in grok_data:
        original_match = grok_data.get('原作の一致', '不一致') == '一致'
        character_match = grok_data.get('キャラクターの一致', '不一致') == '一致'
        
        print(f"Debug: 旧形式を検出 - 原作一致: {original_match}, キャラ一致: {character_match}")
        
        if original_match and character_match:
            # 両方一致の場合は、元のスプレッドシート情報を使用
            print(f"Debug: 原作・キャラクター両方一致のため、スプレッドシート情報を使用")
            return '', []  # 空を返して、呼び出し元でスプレッドシート情報を使用
        else:
            # 不一致の場合は、正しい情報を使用
            correct_original = grok_data.get('正しい原作名', '').strip()
            correct_character = grok_data.get('正しいキャラクター名', '').strip()
            
            # 「不明」系の表記を統一
            if correct_original in ['不明（特定不可）', '不明（特定できず）', '不明（確定情報なし）', '不明（複数の原作が混在する可能性あり）', '不明（提供情報からは原作特定不可）', '不明（原作名が特定できない）'] or correct_original.startswith('不明（推定：'):
                correct_original = '不明'
            if correct_character in ['不明（特定不可）', '不明（特定できず）', '不明（確定情報なし）', '不明（フルネームの特定不可）', '不明（提供情報からはキャラクター特定不可）', '不明（キャラクター名が特定できない）']:
                correct_character = '不明'
            
            correct_characters = [correct_character] if correct_character else []
            print(f"Debug: 不一致のため正しい情報を使用 - 原作: '{correct_original}', キャラ: {correct_characters}")
            return correct_original, correct_characters
    
    # 従来のキャラクター名リスト形式に対応
    grok_original = grok_data.get('原作名', '').strip()
    grok_characters = []
    char_list = grok_data.get('キャラクター名リスト', [])
    
    # 「不明」系の表記を統一
    if grok_original in ['不明（特定不可）', '不明（特定できず）', '不明（確定情報なし）', '不明（複数の原作が混在する可能性あり）', '不明（提供情報からは原作特定不可）', '不明（原作名が特定できない）'] or grok_original.startswith('不明（推定：'):
        grok_original = '不明'
    
    if isinstance(char_list, list):
        for char_item in char_list[:5]:  # 最大5名
            if isinstance(char_item, dict):
                char_name = char_item.get('名前', '').strip()
            else:
                char_name = str(char_item).strip()
            
            # 「不明」系の表記を統一
            if char_name in ['不明（特定不可）', '不明（特定できず）', '不明（確定情報なし）', '不明（フルネームの特定不可）', '不明（提供情報からはキャラクター特定不可）', '不明（キャラクター名が特定できない）']:
                char_name = '不明'
            
            if char_name:
                grok_characters.append(char_name)
    elif isinstance(char_list, str):
        # 文字列の場合は分割
        char_names = re.split(r'[、,，・\s]+', char_list)
        for name in char_names[:5]:
            name = name.strip()
            
            # 「不明」系の表記を統一
            if name in ['不明（特定不可）', '不明（特定できず）', '不明（確定情報なし）', '不明（フルネームの特定不可）', '不明（提供情報からはキャラクター特定不可）', '不明（キャラクター名が特定できない）']:
                name = '不明'
            
            if name:
                grok_characters.append(name)
    
    return grok_original, grok_characters

def check_original_work_match(grok_original, sheet_original_work):
    """原作名の照合"""
    if not sheet_original_work or not grok_original:
        return False
    
    # 完全一致
    if sheet_original_work.lower() == grok_original.lower():
        return True
    
    # 部分一致（どちらかが他方を含む）
    if (sheet_original_work.lower() in grok_original.lower() or 
        grok_original.lower() in sheet_original_work.lower()):
        return True
    
    return False

def check_character_match(grok_characters, sheet_character):
    """キャラクター名の照合"""
    if not sheet_character or not grok_characters:
        return False
    
    for grok_char in grok_characters:
        # フルネームでの照合
        if (sheet_character.lower() == grok_char.lower() or
            sheet_character.lower() in grok_char.lower() or
            grok_char.lower() in sheet_character.lower()):
            return True
        
        # 名前部分での照合
        grok_name_parts = grok_char.split()
        sheet_name_parts = sheet_character.split()
        
        for grok_part in grok_name_parts:
            for sheet_part in sheet_name_parts:
                if (grok_part.lower() == sheet_part.lower() or
                    grok_part.lower() in sheet_part.lower() or
                    sheet_part.lower() in grok_part.lower()):
                    return True
    
    return False

def build_validation_result(original_match, character_match, grok_original, grok_characters, sheet_original_work, sheet_character):
    """照合結果を構築（一致/不一致確認形式対応）"""
    
    # 一致/不一致確認形式の場合の特別処理
    if not grok_original and not grok_characters:
        # extract_work_and_charactersで空が返された場合（両方一致の場合）
        print("Debug: 原作・キャラクター両方一致のため、スプレッドシート情報をそのまま使用")
        return {
            'is_match': True,
            'validated_original_work': sheet_original_work or '',
            'validated_characters': [sheet_character] if sheet_character else [],
            'match_reason': '原作・キャラクター両方一致のため、スプレッドシート情報を採用'
        }
    
    # 従来の照合ロジック
    is_match = original_match and character_match
    
    if is_match:
        # 一致した場合：OpenAIの結果を使用
        validated_original = grok_original if grok_original else sheet_original_work
        validated_chars = grok_characters[:5] if grok_characters else ([sheet_character] if sheet_character else [])
        match_reason = f"原作名とキャラクター名が一致。追加キャラクター{len(grok_characters)}名を含む"
    else:
        # 不一致の場合の処理
        if grok_original or grok_characters:
            # 正しい情報がある場合は正しい情報を使用
            validated_original = grok_original if grok_original else sheet_original_work
            validated_chars = grok_characters[:5] if grok_characters else ([sheet_character] if sheet_character else [])
            match_reason = f"不一致のため正しい情報を採用（正しい原作: '{grok_original}', 正しいキャラ: {grok_characters}）"
        else:
            # 正しい情報もない場合はスプレッドシート情報を使用
            validated_original = sheet_original_work or ''
            validated_chars = [sheet_character] if sheet_character else []
            
            if not original_match and not character_match:
                match_reason = "原作名とキャラクター名の両方が不一致"
            elif not original_match:
                match_reason = f"原作名が不一致（OpenAI: '{grok_original}' vs Sheet: '{sheet_original_work}'）"
            else:
                match_reason = f"キャラクター名が不一致（OpenAI: {grok_characters} vs Sheet: '{sheet_character}'）"
    
    print(f"Debug: 照合結果 - 一致: {is_match}, 理由: {match_reason}")
    
    return {
        'is_match': is_match,
        'validated_original_work': validated_original,
        'validated_characters': validated_chars,
        'match_reason': match_reason
    }

async def call_openai_api_with_images(prompt, image_urls, max_tokens=600):
    """
    OpenAI API（GPT-4V）を画像付きで呼び出す関数
    """
    if not OPENAI_API_KEY:
        print("Warning: OPENAI_API_KEY が設定されていません。元のテキストを返します。")
        return None
    
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    # 画像URLを最大5枚に制限
    limited_images = image_urls[:5] if image_urls else []
    
    # メッセージコンテンツを構築
    content = [{"type": "text", "text": prompt}]
    
    # 画像を追加（最大5枚、女性の顔のみという指示をプロンプトに含める）
    for i, img_url in enumerate(limited_images):
        content.append({
            "type": "image_url",
            "image_url": {"url": img_url}
        })
        print(f"Debug: 顔画像 {i+1}/{len(limited_images)} をOpenAI APIに送信: {img_url[:50]}...")
    
    data = {
        'model': 'gpt-4o',  # GPT-4 Omni（画像対応）
        'messages': [
            {
                'role': 'user',
                'content': content
            }
        ],
        'max_tokens': max_tokens,
        'temperature': 0.7
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=60)  # 画像処理のため60秒に延長
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"Debug: OpenAI API（画像付き）レスポンス成功 - {len(limited_images)}枚の画像を分析")
                    return result['choices'][0]['message']['content'].strip()
                else:
                    error_text = await response.text()
                    print(f"OpenAI API Error {response.status}: {error_text}")
                    return None
    except Exception as e:
        print(f"OpenAI API（画像付き）呼び出しエラー: {str(e)}")
        return None

async def main():
    # グローバル変数の宣言と初期化
    global global_last_scheduled_time
    global_last_scheduled_time = None
    print("🕐 グローバル最終予約時間を初期化しました")
    
    # デバッグ用に環境変数の値を出力
    print(f"Debug: WP_URL = {WP_URL}")
    print(f"Debug: WP_USERNAME = {WP_USERNAME}")
    print(f"Debug: WP_APP_PASSWORD = {'設定済み' if WP_APP_PASSWORD else '未設定'}")

    # SpreadsheetManagerのインスタンスを作成
    ss = SpreadsheetManager()

    # ===== キーワード検索処理（重複防止強化版） =====
    print("🔍 キーワード検索処理を開始（重複防止強化版）")
    
    keywords_to_process = ss.get_active_keywords()
    
    print(f"Debug in main: アクティブなキーワード数: {len(keywords_to_process)}")

    if not keywords_to_process:
        print("⚠️  アクティブなキーワードがありません。既存の未処理商品のみを処理します。")
    else:
        print(f"📋 {len(keywords_to_process)}件のアクティブなキーワードで商品検索を実行")
        
        # バッチ処理用のデータを準備
        products_to_add = []
        
        try:
            for kw_data in keywords_to_process:
                keyword = kw_data.get('keyword')
                original_work = kw_data.get('original_work', '')
                character_name = kw_data.get('character_name', '')
                
                if not keyword:
                    print(f"Warning: 空のキーワードをスキップ: {kw_data}")
                    continue
                
                print(f"🔍 キーワード検索: {keyword} (原作: {original_work}, キャラ: {character_name})")
                
                # APIを使って商品CIDリストを取得
                product_cids_from_search = await fanza_scraper.search_fanza_products_by_keyword(keyword)
                
                print(f"   検索ヒット: {len(product_cids_from_search)}件")
                
                # バッチ用リストに追加（重複チェックは後で一括実行）
                for cid in product_cids_from_search:
                    url = f"https://www.dmm.co.jp/dc/doujin/-/detail/=/cid={cid}/"
                    product_data = {
                        'status': '未処理',
                        'url': url,
                        'title': '',
                        'original_work': original_work,
                        'character_name': character_name,
                        'reserve_date': '',
                        'post_url': '',
                        'last_processed': '',
                        'error_details': ''
                    }
                    products_to_add.append(product_data)
                    print(f"   新規商品追加予定: {cid}")
                
        
        except Exception as e:
            print(f"❌ キーワード検索中にエラー: {str(e)}")
        
        # 重複チェックのバッチ実行（最適化）
        if products_to_add:
            print(f"🔍 {len(products_to_add)}件の商品の重複チェックをバッチ実行中...")
            
            # URLリストを抽出
            urls_to_check = [product['url'] for product in products_to_add]
            
            # 一括重複チェック（最適化版）
            duplicate_results = ss.check_products_batch(urls_to_check)
            
            # 重複していない商品のみフィルタリング
            filtered_products = []
            for product in products_to_add:
                if not duplicate_results.get(product['url'], True):  # 重複していない場合
                    filtered_products.append(product)
                else:
                    cid = ss.extract_product_code(product['url'])
                    print(f"   ⚠️  品番 {cid} は既に登録済みのためスキップ")
            
            print(f"   重複チェック結果: {len(products_to_add)}件 → {len(filtered_products)}件（{len(products_to_add) - len(filtered_products)}件の重複を除外）")
            
            # フィルタリング後の商品をバッチ追加
            if filtered_products:
                print(f"📝 {len(filtered_products)}件の新商品をバッチ追加中...")
                if ss.add_products_batch(filtered_products):
                    print(f"✅ {len(filtered_products)}件の新商品を追加完了")
                else:
                    print("❌ バッチ追加に失敗")
            else:
                print("📋 追加する新商品はありませんでした（全て重複）")
        else:
            print("📋 検索結果がありませんでした")

    # ===== 未処理商品の処理（重複防止強化版） =====
    print("\n" + "="*60)
    print("📋 未処理商品の処理を開始（重複防止強化版）")
    
    products_to_process_on_sheet = get_unprocessed_products(ss)
    print(f"未処理データ件数: {len(products_to_process_on_sheet)}")

    if not products_to_process_on_sheet:
        print("✅ 処理対象の未処理商品がありません。")
        return

    successful_post_count = 0

    for idx, prod_info in enumerate(products_to_process_on_sheet):
        row_idx = prod_info['row_idx']
        row_data = prod_info['row']
        actual_url_for_processing = row_data[3]

        print(f"\n{'='*60}")
        print(f"📋 処理開始: {idx+1}/{len(products_to_process_on_sheet)} - Row {row_idx}")
        print(f"🔗 URL: {actual_url_for_processing}")
        
        # 【重要】処理前に最新のスプレッドシート状態を確認（重複防止）
        print("🔄 最新状態確認中...")
        latest_row_data = ss._get_sheet_values(ss.product_sheet, f'A{row_idx}:I{row_idx}', value_render_option='FORMULA')
        
        if latest_row_data and len(latest_row_data) > 0:
            latest_row = latest_row_data[0]
            latest_status = str(latest_row[0]).strip() if latest_row[0] else ''
            latest_post_url = latest_row[6] if len(latest_row) > 6 else ''
            latest_scheduled_date = latest_row[5] if len(latest_row) > 5 else ''
            
            print(f"   最新ステータス: '{latest_status}'")
            print(f"   最新記事URL: '{latest_post_url}'")
            print(f"   最新予約日時: '{latest_scheduled_date}'")
            
            # 【重要】厳密な処理済みチェック
            excluded_statuses = {
                '予約投稿', '投稿済み', '投稿完了', '公開済み', '処理済み', 
                '下書き保存', '下書き', 'draft', 'published', 'scheduled',
                'エラー', 'スキップ', 'skip', 'error', '除外', '無効'
            }
            
            # ステータス、記事URL、予約日時のいずれかが設定されていれば処理済み
            if (latest_status in excluded_statuses or 
                (latest_post_url and str(latest_post_url).strip()) or 
                (latest_scheduled_date and str(latest_scheduled_date).strip())):
                print(f"⚠️  Row {row_idx} は既に処理済み（ステータス: '{latest_status}'）- 100%重複防止でスキップ")
                continue
        
        print("✅ 最新状態確認完了 - 処理続行")

        # 詳細取得＆投稿処理を実行
        result = await process_product(ss, row_idx, row_data, actual_url_for_processing)
        
        # グローバル最終予約時間の状態をログ出力
        if global_last_scheduled_time:
            print(f"🕐 現在のグローバル最終予約時間: {global_last_scheduled_time.strftime('%m/%d %H:%M')}")
        else:
            print(f"🕐 グローバル最終予約時間: 未設定")
        
        # 投稿が成功した場合のみカウントを増やす
        if result:
            successful_post_count += 1

    print(f"\n🎉 処理完了: {successful_post_count}件の投稿が成功しました")
    
    # 商品管理シートの整形
    print("\n📋 商品管理シートを整形中...")
    ss.format_product_sheet()
    print("✅ 商品管理シート整形完了（品番・投稿IDリンク化）")

def extract_info_from_text_response(text_response):
    """
    JSON形式以外のテキスト応答から原作名とキャラクター名を抽出する
    
    Args:
        text_response: OpenAI APIからのテキスト応答
    
    Returns:
        dict: 抽出された情報
    """
    if not text_response or not isinstance(text_response, str):
        return None
    
    print(f"Debug: テキスト応答からの情報抽出を開始: {text_response[:200]}...")
    
    # 抽出結果を格納する辞書
    extracted_info = {
        '原作名': '',
        'キャラクター名リスト': [],
        '信頼度スコア': 0.5
    }
    
    # 原作名の抽出パターン
    original_patterns = [
        r'原作[：:]\s*([^\n\r]+)',
        r'原作名[：:]\s*([^\n\r]+)',
        r'作品[：:]\s*([^\n\r]+)',
        r'元ネタ[：:]\s*([^\n\r]+)',
        r'出典[：:]\s*([^\n\r]+)',
        r'(?:から|より)の?「([^」]+)」',
        r'「([^」]+)」(?:の|から)',
        r'(?:アニメ|ゲーム|漫画|小説)「([^」]+)」'
    ]
    
    # キャラクター名の抽出パターン
    character_patterns = [
        r'キャラクター[：:]\s*([^\n\r]+)',
        r'キャラ[：:]\s*([^\n\r]+)',
        r'登場人物[：:]\s*([^\n\r]+)',
        r'(?:主人公|ヒロイン)[：:]\s*([^\n\r]+)',
        r'([^\s]+(?:アスナ|美琴|レム|ラム|エミリア|初音ミク|鹿目まどか|暁美ほむら|巴マミ|佐倉杏子|美樹さやか|涼宮ハルヒ|長門有希|朝比奈みくる|綾波レイ|惣流アスカ|葛城ミサト|碇シンジ|真希波マリ|式波アスカ)[^\s]*)',
        r'([^\s]*(?:さん|ちゃん|様|君|先生|先輩|後輩))',
        r'([一-龯ひらがなカタカナ]{2,8}(?:アスナ|美琴|レム|ラム|エミリア|ミク|まどか|ほむら|マミ|杏子|さやか|ハルヒ|有希|みくる|レイ|アスカ|ミサト|シンジ|マリ))'
    ]
    
    # 原作名を抽出
    for pattern in original_patterns:
        match = re.search(pattern, text_response, re.IGNORECASE)
        if match:
            original_work = match.group(1).strip()
            # 不要な文字を除去
            original_work = re.sub(r'[「」『』【】\(\)（）]', '', original_work)
            original_work = original_work.strip('、。,.')
            if len(original_work) > 1 and len(original_work) < 50:
                extracted_info['原作名'] = original_work
                print(f"Debug: 原作名を抽出: '{original_work}'")
                break
    
    # キャラクター名を抽出
    characters_found = set()
    for pattern in character_patterns:
        matches = re.finditer(pattern, text_response, re.IGNORECASE)
        for match in matches:
            char_text = match.group(1).strip()
            # 複数のキャラクター名が含まれている場合は分割
            char_candidates = re.split(r'[、,，・\s]+', char_text)
            
            for char in char_candidates:
                char = char.strip()
                # 不要な文字を除去
                char = re.sub(r'[「」『』【】\(\)（）]', '', char)
                char = char.strip('、。,.')
                
                # 有効なキャラクター名の条件
                if (len(char) >= 2 and len(char) <= 20 and 
                    not re.match(r'^[0-9]+$', char) and  # 数字のみは除外
                    not char.lower() in ['原作', 'キャラクター', 'キャラ', '登場人物', '主人公', 'ヒロイン']):
                    characters_found.add(char)
                    if len(characters_found) >= 5:  # 最大5名
                        break
            
            if len(characters_found) >= 5:
                break
    
    # キャラクター名リストを作成
    extracted_info['キャラクター名リスト'] = list(characters_found)[:5]
    
    print(f"Debug: 抽出されたキャラクター名: {extracted_info['キャラクター名リスト']}")
    
    # 信頼度スコアを計算
    score = 0.3  # ベーススコア
    if extracted_info['原作名']:
        score += 0.3
    if extracted_info['キャラクター名リスト']:
        score += 0.2 * min(len(extracted_info['キャラクター名リスト']), 2)
    
    extracted_info['信頼度スコア'] = min(score, 0.9)
    
    print(f"Debug: テキスト抽出結果 - 原作: '{extracted_info['原作名']}', キャラ: {extracted_info['キャラクター名リスト']}, 信頼度: {extracted_info['信頼度スコア']}")
    
    return extracted_info

if __name__ == "__main__":
    asyncio.run(main()) 