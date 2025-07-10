#!/usr/bin/env python3
"""
改良版同人WordPress自動投稿システム - テストスクリプト
品質チェック機能とタイトルクリーニング機能を含む
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
import sys

# プロジェクトのルートディレクトリをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 環境変数の読み込み
from dotenv import load_dotenv
load_dotenv('API.env')

# メイン関数をインポート
from auto_wp_post import (
    clean_title,
    validate_product_data,
    generate_article_content
)
from src.utils import fanza_scraper

class ImprovedSystemTester:
    """改良版システムテスタークラス"""
    
    def __init__(self):
        self.output_dir = Path("test_output")
        self.output_dir.mkdir(exist_ok=True)
        self.test_results = []
    
    async def test_single_product(self, product_url, expected_original="", expected_character=""):
        """単一商品の改良版テスト"""
        print(f"\n{'='*80}")
        print(f"🧪 改良版システムテスト開始")
        print(f"🔗 商品URL: {product_url}")
        print(f"📝 期待する原作: {expected_original}")
        print(f"👤 期待するキャラ: {expected_character}")
        print(f"{'='*80}\n")
        
        try:
            # 1. 商品詳細取得
            print("1️⃣ 商品詳細情報取得中...")
            details = await fanza_scraper.scrape_fanza_product_details(
                product_url, expected_original, expected_character
            )
            print(f"✅ 商品詳細取得完了")
            print(f"   タイトル: {details.get('title', 'N/A')}")
            print(f"   サークル: {details.get('circle_name', 'N/A')}")
            print(f"   作者: {details.get('author_name', 'N/A')}")
            
            # 2. 品質チェック機能テスト
            print("\n2️⃣ 品質チェック実行中...")
            validation_result = validate_product_data(details)
            print(f"📊 品質チェック結果:")
            print(f"   品質スコア: {validation_result['quality_score']}%")
            print(f"   エラー数: {len(validation_result['errors'])}")
            print(f"   警告数: {len(validation_result['warnings'])}")
            print(f"   有効性: {'✅ 有効' if validation_result['is_valid'] else '❌ 無効'}")
            
            if validation_result['errors']:
                print("   🔴 エラー詳細:")
                for error in validation_result['errors']:
                    print(f"     - {error}")
            
            if validation_result['warnings']:
                print("   🟡 警告詳細:")
                for warning in validation_result['warnings']:
                    print(f"     - {warning}")
            
            # 3. タイトルクリーニングテスト
            print("\n3️⃣ タイトルクリーニング実行中...")
            original_title = details.get('title', '')
            cleaned_title = clean_title(original_title)
            print(f"   元のタイトル: {original_title}")
            print(f"   クリーニング後: {cleaned_title}")
            print(f"   変更有無: {'✅ 変更あり' if original_title != cleaned_title else '🔄 変更なし'}")
            
            # 4. 記事生成テスト
            print("\n4️⃣ 記事生成実行中...")
            
            # サンプル画像処理
            sample_images = details.get('sample_images', [])
            main_image = sample_images[0] if sample_images else ""
            gallery_images = sample_images[:5]  # 最大5枚
            
            # Grokリライト用のダミーデータ
            grok_description = f"{details.get('description', '')} （※Grokリライト版）"
            grok_lead = f"{cleaned_title}の魅力的な作品をご紹介します。"
            grok_seo = f"{cleaned_title}の同人作品情報"
            
            article_content, seo_description = generate_article_content(
                details, main_image, gallery_images, product_url,
                grok_description, grok_lead, grok_seo
            )
            
            print(f"✅ 記事生成完了")
            print(f"   記事文字数: {len(article_content)}文字")
            print(f"   SEO説明文字数: {len(seo_description)}文字")
            print(f"   メイン画像: {'✅ あり' if main_image else '❌ なし'}")
            print(f"   ギャラリー画像: {len(gallery_images)}枚")
            
            # 5. コンテンツ構成要素チェック
            print("\n5️⃣ コンテンツ構成要素チェック...")
            content_elements = []
            if 'wp:image' in article_content:
                content_elements.append('画像')
            if 'wp:table' in article_content:
                content_elements.append('テーブル')
            if 'wp:button' in article_content:
                content_elements.append('ボタン')
            if 'wp:heading' in article_content:
                content_elements.append('見出し')
            if 'wp:paragraph' in article_content:
                content_elements.append('段落')
            
            print(f"   構成要素: {', '.join(content_elements) if content_elements else 'なし'}")
            
            # 6. 最終記事タイトル生成
            character_name = details.get('character_name', '')
            if character_name and character_name not in ['不明', '不明（特定不可）']:
                final_title = f"{cleaned_title}【{character_name.split(',')[0].strip()}】"
            else:
                final_title = cleaned_title
            
            print(f"\n6️⃣ 最終記事タイトル: {final_title}")
            
            # 7. テスト結果まとめ
            test_result = {
                'timestamp': datetime.now().isoformat(),
                'product_url': product_url,
                'quality_check': validation_result,
                'title_cleaning': {
                    'original': original_title,
                    'cleaned': cleaned_title,
                    'changed': original_title != cleaned_title
                },
                'extracted_data': {
                    'title': details.get('title', ''),
                    'cleaned_title': cleaned_title,
                    'final_title': final_title,
                    'circle_name': details.get('circle_name', ''),
                    'author_name': details.get('author_name', ''),
                    'description': details.get('description', ''),
                    'character_name': details.get('character_name', ''),
                    'original_work': details.get('original_work', ''),
                    'price': details.get('price', ''),
                    'page_count': details.get('page_count', ''),
                    'product_format': details.get('product_format', ''),
                    'genres': details.get('genres', [])
                },
                'article_data': {
                    'content_length': len(article_content),
                    'seo_description_length': len(seo_description),
                    'has_main_image': bool(main_image),
                    'gallery_images_count': len(gallery_images),
                    'content_elements': content_elements
                },
                'expected_vs_actual': {
                    'expected_original': expected_original,
                    'actual_original': details.get('original_work', ''),
                    'expected_character': expected_character,
                    'actual_character': details.get('character_name', ''),
                    'original_match': expected_original == details.get('original_work', ''),
                    'character_match': expected_character in details.get('character_name', '')
                }
            }
            
            # 8. 結果ファイル出力
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # JSON結果
            json_file = self.output_dir / f"improved_test_{timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(test_result, f, ensure_ascii=False, indent=2)
            
            # HTML記事プレビュー
            html_file = self.output_dir / f"article_preview_{timestamp}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(self._generate_html_preview(test_result, article_content, final_title))
            
            print(f"\n✅ テスト完了！")
            print(f"📁 出力ファイル:")
            print(f"   📊 JSON結果: {json_file}")
            print(f"   📄 HTMLプレビュー: {html_file}")
            
            self.test_results.append(test_result)
            return test_result
            
        except Exception as e:
            print(f"\n❌ テストエラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_html_preview(self, test_result, article_content, title):
        """HTMLプレビュー生成"""
        quality_check = test_result['quality_check']
        title_cleaning = test_result['title_cleaning']
        extracted = test_result['extracted_data']
        article_data = test_result['article_data']
        comparison = test_result['expected_vs_actual']
        
        return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - テスト結果</title>
    <style>
        body {{ 
            font-family: 'Hiragino Sans', 'Yu Gothic', sans-serif; 
            line-height: 1.6; 
            margin: 20px; 
            background-color: #f5f5f5;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .test-header {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            padding: 20px; 
            border-radius: 10px; 
            margin-bottom: 20px;
        }}
        .quality-check {{ 
            background: white; 
            padding: 20px; 
            border-radius: 10px; 
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .score {{ 
            font-size: 2em; 
            font-weight: bold; 
            color: #28a745;
        }}
        .error {{ color: #dc3545; }}
        .warning {{ color: #ffc107; }}
        .success {{ color: #28a745; }}
        .article-preview {{ 
            background: white; 
            padding: 30px; 
            border-radius: 10px; 
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .metadata {{ 
            background: #f8f9fa; 
            padding: 15px; 
            border-radius: 5px; 
            margin: 10px 0;
        }}
        table {{ 
            border-collapse: collapse; 
            width: 100%; 
            margin: 10px 0;
        }}
        th, td {{ 
            border: 1px solid #ddd; 
            padding: 12px; 
            text-align: left;
        }}
        th {{ 
            background-color: #f2f2f2; 
            font-weight: bold;
        }}
        .match {{ background-color: #d4edda; }}
        .mismatch {{ background-color: #f8d7da; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="test-header">
            <h1>🧪 改良版システムテスト結果</h1>
            <p><strong>実行時刻:</strong> {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}</p>
            <p><strong>商品URL:</strong> <a href="{test_result['product_url']}" target="_blank" style="color: #ffffff; text-decoration: underline;">{test_result['product_url']}</a></p>
        </div>
        
        <div class="quality-check">
            <h2>📊 品質チェック結果</h2>
            <div style="display: flex; align-items: center; margin-bottom: 15px;">
                <span class="score">{quality_check['quality_score']}%</span>
                <div style="margin-left: 20px;">
                    <div>{'✅ 有効' if quality_check['is_valid'] else '❌ 無効'}</div>
                    <div>エラー: {len(quality_check['errors'])}件 / 警告: {len(quality_check['warnings'])}件</div>
                </div>
            </div>
            
            {f'''<div class="error">
                <h4>🔴 エラー詳細:</h4>
                <ul>{''.join(f'<li>{error}</li>' for error in quality_check['errors'])}</ul>
            </div>''' if quality_check['errors'] else ''}
            
            {f'''<div class="warning">
                <h4>🟡 警告詳細:</h4>
                <ul>{''.join(f'<li>{warning}</li>' for warning in quality_check['warnings'])}</ul>
            </div>''' if quality_check['warnings'] else ''}
        </div>
        
        <div class="quality-check">
            <h2>✂️ タイトルクリーニング結果</h2>
            <table>
                <tr>
                    <th>項目</th>
                    <th>内容</th>
                </tr>
                <tr>
                    <td>元のタイトル</td>
                    <td>{title_cleaning['original']}</td>
                </tr>
                <tr>
                    <td>クリーニング後</td>
                    <td>{title_cleaning['cleaned']}</td>
                </tr>
                <tr>
                    <td>変更有無</td>
                    <td>{'✅ 変更あり' if title_cleaning['changed'] else '🔄 変更なし'}</td>
                </tr>
                <tr>
                    <td>最終タイトル</td>
                    <td><strong>{extracted['final_title']}</strong></td>
                </tr>
            </table>
        </div>
        
        <div class="quality-check">
            <h2>📋 抽出データ検証</h2>
            <table>
                <tr>
                    <th>項目</th>
                    <th>期待値</th>
                    <th>抽出値</th>
                    <th>判定</th>
                </tr>
                <tr class="{'match' if comparison['original_match'] else 'mismatch'}">
                    <td>原作名</td>
                    <td>{comparison['expected_original'] or '未指定'}</td>
                    <td>{comparison['actual_original'] or 'なし'}</td>
                    <td>{'✅ 一致' if comparison['original_match'] else '❌ 不一致'}</td>
                </tr>
                <tr class="{'match' if comparison['character_match'] else 'mismatch'}">
                    <td>キャラクター名</td>
                    <td>{comparison['expected_character'] or '未指定'}</td>
                    <td>{comparison['actual_character'] or 'なし'}</td>
                    <td>{'✅ 一致' if comparison['character_match'] else '❌ 不一致'}</td>
                </tr>
            </table>
            
            <h3>📝 詳細情報</h3>
            <div class="metadata">
                <p><strong>サークル名:</strong> {extracted['circle_name'] or 'なし'}</p>
                <p><strong>作者名:</strong> {extracted['author_name'] or 'なし'}</p>
                <p><strong>価格:</strong> {extracted['price'] or 'なし'}</p>
                <p><strong>ページ数:</strong> {extracted['page_count'] or 'なし'}</p>
                <p><strong>作品形式:</strong> {extracted['product_format'] or 'なし'}</p>
                <p><strong>ジャンル:</strong> {', '.join(extracted['genres']) if extracted['genres'] else 'なし'}</p>
            </div>
        </div>
        
        <div class="quality-check">
            <h2>📰 記事データ統計</h2>
            <div class="metadata">
                <p><strong>記事本文文字数:</strong> {article_data['content_length']:,}文字</p>
                <p><strong>SEO説明文字数:</strong> {article_data['seo_description_length']}文字</p>
                <p><strong>メイン画像:</strong> {'✅ あり' if article_data['has_main_image'] else '❌ なし'}</p>
                <p><strong>ギャラリー画像:</strong> {article_data['gallery_images_count']}枚</p>
                <p><strong>構成要素:</strong> {', '.join(article_data['content_elements']) if article_data['content_elements'] else 'なし'}</p>
            </div>
        </div>
        
        <div class="article-preview">
            <h2>📄 記事プレビュー</h2>
            <hr>
            <h1>{title}</h1>
            {article_content}
        </div>
    </div>
</body>
</html>"""

async def main():
    """メイン関数"""
    tester = ImprovedSystemTester()
    
    print("🧪 改良版同人WordPress自動投稿システム - テスト")
    print("=" * 80)
    print("1. 単一商品テスト")
    print("2. 複数商品テスト") 
    print("3. 終了")
    
    while True:
        choice = input("\n選択してください (1-3): ").strip()
        
        if choice == "1":
            url = input("商品URL: ").strip()
            if not url:
                print("❌ URLが入力されていません")
                continue
            original = input("期待する原作名 (空白可): ").strip()
            character = input("期待するキャラ名 (空白可): ").strip()
            await tester.test_single_product(url, original, character)
            
        elif choice == "2":
            # 複数の商品でテスト
            test_urls = [
                ("https://www.dmm.co.jp/dc/doujin/-/detail/=/cid=d_444940012132/", "NARUTO", "日向ヒナタ"),
                ("https://www.dmm.co.jp/dc/doujin/-/detail/=/cid=d_444940012133/", "", ""),
                ("https://www.dmm.co.jp/dc/doujin/-/detail/=/cid=d_444940012134/", "", "")
            ]
            
            for i, (url, original, character) in enumerate(test_urls):
                print(f"\n🧪 テスト {i+1}/{len(test_urls)}")
                await tester.test_single_product(url, original, character)
                if i < len(test_urls) - 1:
                    input("次のテストに進むにはEnterキーを押してください...")
            
        elif choice == "3":
            break
        else:
            print("❌ 無効な選択です")

if __name__ == "__main__":
    asyncio.run(main())