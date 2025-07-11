# 同人WordPress自動投稿システム

FANZA APIとAI分析を組み合わせた同人作品の自動投稿システム

## 🎯 システム概要

### 主要機能
- **FANZA API連携**: 商品情報の自動取得
- **AI分析**: Gemini/Grokによるキャラクター・原作認識
- **WordPress自動投稿**: カテゴリ・タグ・カスタムフィールド完全対応
- **画像処理**: サンプル画像の自動取得・検証
- **アフィリエイト**: FANZA提携リンクの自動生成
- **重複管理**: Google Sheetsによる投稿履歴管理

### 投稿スケジュール
- **実行時刻**: 毎日 0:00
- **投稿数**: 48件/日（30分間隔で予約投稿）
- **検索方式**: キーワード順次検索（A列TRUE順）

## 📝 WordPress投稿完成形

### 🏷️ 投稿構造

#### **1. 基本情報**
```
タイトル: 【作品タイトル】キャラクター名
本文: リッチなHTML構造
ステータス: future（予約投稿）
投稿日時: 翌日の指定時刻（30分間隔）
```

#### **2. カテゴリ**
```
プライマリ: FANZAジャンル（例：CG・イラスト、漫画、動画）
セカンダリ: 作品形式（例：同人誌、音声作品、ゲーム）
フォールバック: 同人作品
```

#### **3. タグ**
```
- サークル名
- 作者名（サークル名と異なる場合のみ）
```

#### **4. カスタムフィールド（meta_input）**
```php
meta_input: {
    'original_work': '原作名（例：初音ミク、艦隊これくしょん）',
    'character_name': 'キャラクター名（例：初音ミク、島風）',
    'circle_name': 'サークル名',
    'author_name': '作者名',
    'product_format': '商品形式（例：同人誌、音声作品）',
    'page_count': 'ページ数',
    'fanza_product_id': 'FANZA商品ID',
    'ai_confidence': 'AI分析信頼度（0-100）',
    'analysis_source': '分析ソース（gemini/grok）'
}
```

### 🖼️ 投稿コンテンツ構造

#### **1. リード文**
```
{作品タイトル}は{キャラクター名}が{原作名}の同人作品です。
```

#### **2. 作品情報テーブル**
```html
<!-- wp:table -->
<figure class="wp-block-table">
<table>
<tbody>
<tr><td>サークル名</td><td>{サークル名}</td></tr>
<tr><td>作者名</td><td>{作者名}</td></tr>
<tr><td>原作名</td><td>{原作名}</td></tr>
<tr><td>キャラクター名</td><td>{キャラクター名}</td></tr>
<tr><td>形式</td><td>{商品形式}</td></tr>
<tr><td>ページ数</td><td>{ページ数}</td></tr>
</tbody>
</table>
</figure>
<!-- /wp:table -->
```

#### **3. 画像ギャラリー**
```html
<!-- wp:gallery -->
<figure class="wp-block-gallery">
<figure class="wp-block-image"><img src="{サンプル画像URL1}" alt="サンプル画像"/></figure>
<figure class="wp-block-image"><img src="{サンプル画像URL2}" alt="サンプル画像"/></figure>
<!-- 最大15枚まで -->
</figure>
<!-- /wp:gallery -->
```

#### **4. 作品説明**
```html
<!-- wp:paragraph -->
<p>{AI生成またはFANZA説明文}</p>
<!-- /wp:paragraph -->
```

#### **5. アフィリエイトリンク**
```html
<!-- wp:button -->
<div class="wp-block-button">
<a class="wp-block-button__link" href="{FANZAアフィリエイトURL}" target="_blank" rel="noopener">
FANZAでこの作品をチェックする
</a>
</div>
<!-- /wp:button -->
```

### 📊 データフロー

```
FANZA API → スクレイピング補完 → AI分析 → 記事生成 → WordPress投稿
     ↓            ↓              ↓         ↓           ↓
  商品基本情報   画像・詳細     キャラ認識   HTML生成   予約投稿
     ↓            ↓              ↓         ↓           ↓
  Google Sheets 重複チェック  信頼度判定  カテゴリ分類  投稿完了
```

## 🔧 技術仕様

### 必要な環境変数
```bash
# FANZA API
FANZA_API_ID=your_api_id
FANZA_AFFILIATE_ID=your_affiliate_id

# WordPress
WP_URL=https://your-site.com
WP_USERNAME=your_username
WP_APP_PASSWORD=your_app_password

# AI APIs
GEMINI_API_KEY=your_gemini_key
GROK_API_KEY=your_grok_key

# Google Sheets
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
GOOGLE_SHEETS_ID=your_sheet_id

# VPS設定
VPS_MAX_CONCURRENT_TASKS=2
VPS_POSTS_PER_RUN=5
POSTS_PER_DAY=48
MAX_SAMPLE_IMAGES=15
```

### 依存関係
```
aiohttp>=3.8.0
beautifulsoup4>=4.11.0
google-api-python-client>=2.50.0
python-dotenv>=0.19.0
requests>=2.28.0
playwright>=1.20.0
```

## 🚀 運用方法

### 初回セットアップ
```bash
# リポジトリクローン
git clone https://github.com/your-repo/wordpress-auto-post.git
cd wordpress-auto-post

# 仮想環境作成
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
# .envファイルを編集

# Google Sheets認証設定
# credentials.jsonを配置

# cron設定（VPSの場合）
crontab -e
# 以下を追加：
# 0 0 * * * cd /path/to/wordpress-auto-post && /path/to/venv/bin/python src/vps_main.py --mode schedule48 >> logs/cron.log 2>&1
```

### 手動実行
```bash
# 48件予約投稿
python src/vps_main.py --mode schedule48

# デバッグモード
python src/vps_main.py --mode schedule48 --debug

# 5件テスト投稿
python src/vps_main.py --mode simple --posts 5
```

### 監視・メンテナンス
```bash
# ログ監視
tail -f logs/wordpress-auto-post-48.log

# 重複削除
python src/utils/duplicate_remover.py

# システム状況確認
python src/monitor/system_check.py
```

## 📈 期待される成果

### 投稿品質
- **キャラクター認識率**: 85%以上
- **適切なカテゴリ分類**: 95%以上
- **画像取得成功率**: 90%以上
- **アフィリエイトリンク生成**: 100%

### 運用効率
- **完全自動化**: 人手介入不要
- **重複投稿**: 0件（Google Sheets管理）
- **エラー率**: 5%以下
- **処理速度**: 48件/2-3時間

### SEO効果
- **構造化データ**: カスタムフィールドによる詳細情報
- **画像最適化**: alt属性、適切なサイズ
- **内部リンク**: 関連作品との自動リンク
- **ユーザー体験**: リッチなコンテンツ表示

## 🔒 セキュリティ

### API制限遵守
- **FANZA API**: 1日1000件制限
- **Gemini API**: 1分60件制限
- **レート制限**: 自動調整機能

### データ保護
- **API キー**: 環境変数での管理
- **認証情報**: 暗号化保存
- **ログ**: 個人情報除外

## 📞 サポート

### トラブルシューティング
- [VPS設定ガイド](docs/VPS_48POSTS_SETUP.md)
- [エラー対処法](docs/TROUBLESHOOTING.md)
- [API制限対応](docs/API_LIMITS.md)

### 更新履歴
- **v1.3.0**: 画像・アフィリンク修正、カスタムフィールド対応
- **v1.2.0**: キーワード順次検索、重複検証強化
- **v1.1.0**: 48件予約投稿システム
- **v1.0.0**: 基本的な自動投稿機能

---

**このシステムにより、高品質な同人作品紹介記事を完全自動で毎日48件投稿することが可能です。**