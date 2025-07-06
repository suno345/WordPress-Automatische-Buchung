#!/usr/bin/env python3
"""
記事構成チェックツール

生成された記事の構成、カテゴリ、タグを詳しく確認するツール
"""

import re
from pathlib import Path
import sys

# プロジェクトのルートディレクトリをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class ArticleChecker:
    """記事構成チェッククラス"""
    
    def __init__(self):
        self.checks = []
    
    def check_article_structure(self, content, title="", categories=[], tags=[], custom_taxonomies={}):
        """記事構成の詳細チェック"""
        print(f"\n{'='*60}")
        print(f"📝 記事構成チェック開始")
        print(f"{'='*60}\n")
        
        results = {
            'title_check': self._check_title(title),
            'content_structure': self._check_content_structure(content),
            'seo_elements': self._check_seo_elements(content),
            'categories_tags': self._check_categories_tags(categories, tags, custom_taxonomies),
            'wordpress_blocks': self._check_wordpress_blocks(content),
            'images': self._check_images(content),
            'links': self._check_links(content),
            'free_reading_section': self._check_free_reading_section(content)
        }
        
        self._print_check_results(results)
        return results
    
    def _check_title(self, title):
        """タイトルのチェック"""
        print("1️⃣ タイトルチェック")
        checks = []
        
        # 基本チェック
        if title:
            checks.append({"item": "タイトル存在", "status": "✅", "value": title})
        else:
            checks.append({"item": "タイトル存在", "status": "❌", "value": "タイトルなし"})
        
        # キャラクター名の【】記法チェック
        if "【" in title and "】" in title:
            character_match = re.search(r'【([^】]+)】', title)
            if character_match:
                character = character_match.group(1)
                checks.append({"item": "キャラ名記法", "status": "✅", "value": f"キャラ: {character}"})
            else:
                checks.append({"item": "キャラ名記法", "status": "❌", "value": "【】記法が不正"})
        else:
            checks.append({"item": "キャラ名記法", "status": "⚠️", "value": "キャラ名なし"})
        
        # 文字数チェック
        if title:
            title_length = len(title)
            if 20 <= title_length <= 60:
                checks.append({"item": "タイトル文字数", "status": "✅", "value": f"{title_length}文字"})
            elif title_length < 20:
                checks.append({"item": "タイトル文字数", "status": "⚠️", "value": f"{title_length}文字（短い）"})
            else:
                checks.append({"item": "タイトル文字数", "status": "⚠️", "value": f"{title_length}文字（長い）"})
        
        self._print_checks(checks)
        return checks
    
    def _check_content_structure(self, content):
        """コンテンツ構造のチェック"""
        print("\n2️⃣ コンテンツ構造チェック")
        checks = []
        
        # 期待されるセクション
        expected_sections = [
            ("作品情報", r"<h2[^>]*>作品情報</h2>"),
            ("サンプル画像", r"<h2[^>]*>サンプル画像</h2>"),
            ("作品紹介", r"<h2[^>]*>作品紹介</h2>"),
            ("無料で読める？", r"<h2[^>]*>.*無料で読める.*</h2>")
        ]
        
        for section_name, pattern in expected_sections:
            if re.search(pattern, content):
                checks.append({"item": f"{section_name}セクション", "status": "✅", "value": "存在"})
            else:
                checks.append({"item": f"{section_name}セクション", "status": "❌", "value": "不存在"})
        
        # テーブルの存在チェック
        if "<table>" in content and "</table>" in content:
            table_count = content.count("<table>")
            checks.append({"item": "作品情報テーブル", "status": "✅", "value": f"{table_count}個"})
        else:
            checks.append({"item": "作品情報テーブル", "status": "❌", "value": "なし"})
        
        # コンテンツ長チェック
        content_length = len(content)
        if content_length > 2000:
            checks.append({"item": "コンテンツ量", "status": "✅", "value": f"{content_length}文字"})
        else:
            checks.append({"item": "コンテンツ量", "status": "⚠️", "value": f"{content_length}文字（少ない）"})
        
        self._print_checks(checks)
        return checks
    
    def _check_seo_elements(self, content):
        """SEO要素のチェック"""
        print("\n3️⃣ SEO要素チェック")
        checks = []
        
        # メタ説明に相当する要素
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL)
        if paragraphs:
            first_paragraph = paragraphs[0]
            first_p_length = len(re.sub(r'<[^>]+>', '', first_paragraph))
            if 50 <= first_p_length <= 160:
                checks.append({"item": "リード文長さ", "status": "✅", "value": f"{first_p_length}文字"})
            else:
                checks.append({"item": "リード文長さ", "status": "⚠️", "value": f"{first_p_length}文字"})
        
        # 見出し構造
        h2_count = len(re.findall(r'<h2[^>]*>', content))
        h3_count = len(re.findall(r'<h3[^>]*>', content))
        checks.append({"item": "見出し構造", "status": "✅", "value": f"H2:{h2_count}個, H3:{h3_count}個"})
        
        # 内部リンク
        internal_links = re.findall(r'href="(/[^"]*)"', content)
        if internal_links:
            checks.append({"item": "内部リンク", "status": "✅", "value": f"{len(internal_links)}個"})
        else:
            checks.append({"item": "内部リンク", "status": "⚠️", "value": "なし"})
        
        self._print_checks(checks)
        return checks
    
    def _check_categories_tags(self, categories, tags, custom_taxonomies):
        """カテゴリ・タグのチェック"""
        print("\n4️⃣ カテゴリ・タグチェック")
        checks = []
        
        # カテゴリ
        if categories and any(cat for cat in categories if cat):
            clean_categories = [cat for cat in categories if cat and cat.strip()]
            checks.append({"item": "カテゴリ", "status": "✅", "value": f"{len(clean_categories)}個: {', '.join(clean_categories)}"})
        else:
            checks.append({"item": "カテゴリ", "status": "❌", "value": "なし"})
        
        # タグ
        if tags:
            checks.append({"item": "タグ", "status": "✅", "value": f"{len(tags)}個: {', '.join(tags[:5])}"})
        else:
            checks.append({"item": "タグ", "status": "❌", "value": "なし"})
        
        # カスタムタクソノミー
        if custom_taxonomies:
            for key, value in custom_taxonomies.items():
                if value and value.strip():
                    checks.append({"item": f"カスタム:{key}", "status": "✅", "value": value})
                else:
                    checks.append({"item": f"カスタム:{key}", "status": "❌", "value": "未設定"})
        else:
            checks.append({"item": "カスタムタクソノミー", "status": "❌", "value": "なし"})
        
        self._print_checks(checks)
        return checks
    
    def _check_wordpress_blocks(self, content):
        """WordPressブロックのチェック"""
        print("\n5️⃣ WordPressブロックチェック")
        checks = []
        
        # ブロックコメント
        block_patterns = [
            ("段落ブロック", r"<!-- wp:paragraph -->"),
            ("見出しブロック", r"<!-- wp:heading -->"),
            ("テーブルブロック", r"<!-- wp:table -->"),
            ("HTMLブロック", r"<!-- wp:html -->"),
            ("ボタンブロック", r"<!-- wp:button -->")
        ]
        
        for block_name, pattern in block_patterns:
            count = len(re.findall(pattern, content))
            if count > 0:
                checks.append({"item": block_name, "status": "✅", "value": f"{count}個"})
            else:
                checks.append({"item": block_name, "status": "❌", "value": "なし"})
        
        self._print_checks(checks)
        return checks
    
    def _check_images(self, content):
        """画像のチェック"""
        print("\n6️⃣ 画像チェック")
        checks = []
        
        # 画像タグ
        img_tags = re.findall(r'<img[^>]*>', content)
        if img_tags:
            checks.append({"item": "画像数", "status": "✅", "value": f"{len(img_tags)}個"})
            
            # alt属性のチェック
            alt_count = len(re.findall(r'<img[^>]*alt="[^"]*"[^>]*>', content))
            if alt_count == len(img_tags):
                checks.append({"item": "alt属性", "status": "✅", "value": "全画像に設定"})
            else:
                checks.append({"item": "alt属性", "status": "⚠️", "value": f"{alt_count}/{len(img_tags)}に設定"})
            
            # loading="lazy"のチェック
            lazy_count = len(re.findall(r'<img[^>]*loading="lazy"[^>]*>', content))
            if lazy_count > 0:
                checks.append({"item": "遅延読み込み", "status": "✅", "value": f"{lazy_count}個に設定"})
            else:
                checks.append({"item": "遅延読み込み", "status": "⚠️", "value": "未設定"})
        else:
            checks.append({"item": "画像", "status": "❌", "value": "なし"})
        
        self._print_checks(checks)
        return checks
    
    def _check_links(self, content):
        """リンクのチェック"""
        print("\n7️⃣ リンクチェック")
        checks = []
        
        # アフィリエイトリンク
        affiliate_links = re.findall(r'href="([^"]*dmm\.co\.jp[^"]*)"', content)
        if affiliate_links:
            checks.append({"item": "アフィリエイトリンク", "status": "✅", "value": f"{len(affiliate_links)}個"})
        else:
            checks.append({"item": "アフィリエイトリンク", "status": "❌", "value": "なし"})
        
        # 外部リンクのrel属性
        external_links = re.findall(r'<a[^>]*href="http[^"]*"[^>]*>', content)
        nofollow_count = len(re.findall(r'<a[^>]*href="http[^"]*"[^>]*rel="[^"]*nofollow[^"]*"[^>]*>', content))
        
        if external_links:
            if nofollow_count == len(external_links):
                checks.append({"item": "外部リンクrel属性", "status": "✅", "value": "全てnofollow設定"})
            else:
                checks.append({"item": "外部リンクrel属性", "status": "⚠️", "value": f"{nofollow_count}/{len(external_links)}にnofollow"})
        
        self._print_checks(checks)
        return checks
    
    def _check_free_reading_section(self, content):
        """無料で読める？セクションのチェック"""
        print("\n8️⃣ 無料で読める？セクションチェック")
        checks = []
        
        # SEOキーワード（raw）の存在
        if "raw" in content.lower():
            raw_count = content.lower().count("raw")
            checks.append({"item": "rawキーワード", "status": "✅", "value": f"{raw_count}回出現"})
        else:
            checks.append({"item": "rawキーワード", "status": "❌", "value": "なし"})
        
        # 海賊版サイトの警告
        warning_keywords = ["海賊版", "違法", "リスク", "危険"]
        warning_found = any(keyword in content for keyword in warning_keywords)
        if warning_found:
            checks.append({"item": "警告文", "status": "✅", "value": "海賊版リスクの説明あり"})
        else:
            checks.append({"item": "警告文", "status": "❌", "value": "警告文なし"})
        
        # FANZA公式への誘導
        if "FANZA" in content and ("公式" in content or "正規" in content):
            checks.append({"item": "正規サイト誘導", "status": "✅", "value": "FANZA公式への誘導あり"})
        else:
            checks.append({"item": "正規サイト誘導", "status": "❌", "value": "誘導文なし"})
        
        self._print_checks(checks)
        return checks
    
    def _print_checks(self, checks):
        """チェック結果の出力"""
        for check in checks:
            print(f"  {check['status']} {check['item']}: {check['value']}")
    
    def _print_check_results(self, results):
        """総合結果の出力"""
        print(f"\n{'='*60}")
        print(f"📊 総合チェック結果")
        print(f"{'='*60}")
        
        total_checks = 0
        passed_checks = 0
        
        for category, checks in results.items():
            for check in checks:
                total_checks += 1
                if check['status'] == '✅':
                    passed_checks += 1
        
        success_rate = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
        
        print(f"✅ 合格: {passed_checks}項目")
        print(f"⚠️ 警告: {total_checks - passed_checks}項目")
        print(f"📈 合格率: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print(f"🎉 記事品質: 良好")
        elif success_rate >= 60:
            print(f"⚠️ 記事品質: 改善推奨")
        else:
            print(f"❌ 記事品質: 要改善")

def check_test_output(test_output_dir="test_output"):
    """テスト出力ファイルの記事構成をチェック"""
    output_dir = Path(test_output_dir)
    if not output_dir.exists():
        print(f"❌ {test_output_dir} ディレクトリが見つかりません")
        return
    
    html_files = list(output_dir.glob("*article*.html"))
    if not html_files:
        print(f"❌ {test_output_dir} に記事HTMLファイルが見つかりません")
        return
    
    checker = ArticleChecker()
    
    for html_file in html_files:
        print(f"\n📄 ファイル: {html_file.name}")
        
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # HTMLから記事タイトルを抽出
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', content)
            title = title_match.group(1) if title_match else ""
            
            # 記事コンテンツ部分を抽出
            article_match = re.search(r'<div class="article-content">(.*?)</div>', content, re.DOTALL)
            article_content = article_match.group(1) if article_match else content
            
            # メタデータを抽出（簡易）
            categories = []
            tags = []
            custom_taxonomies = {}
            
            # カテゴリとタグの抽出
            if "カテゴリ:" in content:
                cat_match = re.search(r'カテゴリ:</strong>\s*([^<]*)', content)
                if cat_match:
                    categories = [c.strip() for c in cat_match.group(1).split(',') if c.strip()]
            
            if "タグ:" in content:
                tag_match = re.search(r'タグ:</strong>\s*([^<]*)', content)
                if tag_match:
                    tags = [t.strip() for t in tag_match.group(1).split(',') if t.strip()]
            
            # カスタムタクソノミーの抽出
            taxonomy_matches = re.findall(r'<li>([^:]+):\s*([^<]*)</li>', content)
            for key, value in taxonomy_matches:
                if value.strip():
                    custom_taxonomies[key] = value.strip()
            
            # チェック実行
            checker.check_article_structure(article_content, title, categories, tags, custom_taxonomies)
            
        except Exception as e:
            print(f"❌ ファイル読み込みエラー: {e}")

if __name__ == "__main__":
    print("📝 記事構成チェックツール")
    print("=" * 40)
    print("1. test_outputディレクトリの記事をチェック")
    print("2. 手動で記事内容をチェック")
    
    choice = input("選択してください (1-2): ").strip()
    
    if choice == "1":
        check_test_output()
    elif choice == "2":
        print("❌ 手動チェック機能は未実装です")
    else:
        print("❌ 無効な選択です")