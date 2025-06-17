import sys
import traceback
import asyncio
from src.spreadsheet.spreadsheet_manager import SpreadsheetManager
from src.fanza.fanza_data_retriever import FANZA_Data_Retriever
from src.utils.discord_notify import send_discord_error
from src.utils.wp_api import post_to_wordpress
from src.utils.wp_article_generator import generate_wp_article
from src.utils.fanza_scraper import search_fanza_products_by_keyword
# 必要に応じて他のモジュールもimport


def build_product_row(product, keyword_info):
    # 22カラム分のデータを整形
    return {
        'url': product.get('URL', product.get('url', '')),
        'title': product.get('title', ''),
        'character_name': keyword_info.get('character_name', ''),
        'original_work': product.get('iteminfo', {}).get('original', [''])[0] if 'iteminfo' in product and 'original' in product['iteminfo'] else '',
        'circle_name': product.get('maker', [''])[0] if isinstance(product.get('maker'), list) else product.get('maker', ''),
        'genre': ','.join([g['name'] for g in product.get('iteminfo', {}).get('genre', [])]) if 'iteminfo' in product and 'genre' in product['iteminfo'] else '',
        'status': '未処理',
        'reserve_date': '',
        'post_url': '',
        'error_details': '',
        'description': product.get('description', ''),
        'catch_copy': product.get('catch_copy', ''),
        'main_image': product.get('sampleImageURL', {}).get('sample_l', [''])[0] if product.get('sampleImageURL', {}).get('sample_l') else '',
        'gallery_images': ','.join(product.get('sampleImageURL', {}).get('sample_l', [])[1:]) if product.get('sampleImageURL', {}).get('sample_l') and len(product.get('sampleImageURL', {}).get('sample_l')) > 1 else '',
        'price': product.get('prices', {}).get('price', ''),
        'release_date': product.get('date', ''),
        'seo_title': '',
        'seo_description': '',
        'keywords': keyword_info.get('keyword', ''),
        'custom_category': '',
        'custom_tags': ''
    }


async def main():
    try:
        sheet_manager = SpreadsheetManager()
        fanza = FANZA_Data_Retriever()
        keywords = sheet_manager.get_active_keywords()
        print(f"取得キーワード数: {len(keywords)}")
        for kw in keywords:
            print(f"キーワード: {kw['keyword']} / キャラクター名: {kw['character_name']}")
            try:
                urls = await search_fanza_products_by_keyword(kw['keyword'])
                print(f"  → スクレイピング取得URL数: {len(urls)}")
                for url in urls:
                    if not url:
                        print("    [SKIP] URLなし")
                        continue
                    if sheet_manager.check_product_exists(url):
                        print(f"    [SKIP] 登録済: {url}")
                        continue
                    try:
                        # 商品詳細情報はAPIで取得（なければURLのみで最低限投稿）
                        product = await fanza.get_product_info(url.split('cid=')[-1].replace('/', ''))
                        if not product:
                            product = {'URL': url, 'title': url, 'description': '', 'sampleImageURL': {}}
                        row_data = build_product_row(product, kw)
                        article = generate_wp_article(product, kw)
                        try:
                            wp_url = post_to_wordpress(
                                title=article['title'],
                                content=article['content'],
                                status='publish',
                                categories=article['categories'],
                                tags=article['tags'],
                                eyecatch=article['eyecatch'],
                                **article['custom_taxonomies']
                            )
                            print(f"    [WP] 投稿成功: {wp_url}")
                            row_data['post_url'] = wp_url
                            row_data['status'] = '投稿完了'
                            sheet_manager.add_product(row_data)
                            sheet_manager.update_product_status(url, '投稿完了', wp_url)
                        except Exception as wp_e:
                            print(f"    [WP ERROR] 投稿失敗: {url} {wp_e}")
                            row_data['error_details'] = str(wp_e)
                            sheet_manager.add_product(row_data)
                            sheet_manager.update_product_error(url, str(wp_e))
                            await send_discord_error(f"WordPress投稿失敗: {url}\n{wp_e}")
                    except Exception as e:
                        print(f"    [ERROR] 追加処理失敗: {url} {e}")
                        sheet_manager.update_product_error(url, str(e))
                        await send_discord_error(f"追加処理失敗: {url}\n{e}")
            except Exception as e:
                print(f"  [ERROR] 商品URLスクレイピング失敗: {e}")
                traceback.print_exc()
                await send_discord_error(f"商品URLスクレイピング失敗: {kw['keyword']}\n{e}")
    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()
        await send_discord_error(f"致命的エラー\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 