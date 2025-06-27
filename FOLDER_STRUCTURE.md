# 📁 整理後のフォルダ構造

## 🎯 整理の目的
- **重複ファイル削除**: 同じ機能の複数ファイルを統合
- **VPS最適化**: 軽量で効率的な構造
- **保守性向上**: 明確な責任分離
- **シンプル化**: 不要な階層を削除

## 📂 新しい構造

```
src/
├── vps_main.py              # VPS向けメインエントリーポイント
├── core/                    # コア機能（ビジネスロジック）
│   ├── fanza/
│   │   └── data_retriever.py    # FANZA API & スクレイピング統合版
│   ├── grok/
│   │   └── analyzer.py          # Grok AI分析（顔認識含む）
│   ├── wordpress/
│   │   ├── poster.py            # WordPress投稿（即時・下書き対応）
│   │   └── article_generator.py # 記事生成（SWELL最適化）
│   └── spreadsheet/
│       └── manager.py           # Google Sheets管理
├── utils/                   # ユーティリティ（共通機能）
│   ├── logger.py                # 基本ログ機能
│   ├── error_logger.py          # エラーログ特化
│   ├── config_manager.py        # 設定管理
│   └── fanza_scraper.py         # Webスクレイピング
└── scheduler/
    └── vps_orchestrator.py      # VPS向け軽量オーケストレーター
```

## 🔄 削除された重複ファイル

### 統合前の問題
```
❌ 重複していたファイル:
- src/grok/grok_analyzer.py
- src/grok_analyzer/grok_analyzer.py  
- src/analyzer/grok_analyzer.py
- src/modules/grok/api_client.py

- src/wordpress/wordpress_poster.py
- src/wordpress_poster/wordpress_poster.py
- src/modules/wordpress/wordpress_poster.py

- src/logger/error_logger.py
- src/error/error_logger.py
- src/utils/error_logger.py

- src/monitor/monitor.py
- src/monitoring/monitor.py
- src/utils/monitor.py
```

### 統合後の解決
```
✅ 統合されたファイル:
- core/grok/analyzer.py (最良版を選択)
- core/wordpress/poster.py (VPS最適化版)
- utils/error_logger.py (機能統合版)
- utils/logger.py (基本ログ機能)
```

## 🚀 VPS向け最適化

### 軽量化された機能
- **同時実行数制限**: 2タスクまで
- **メモリ使用量制限**: 512MB
- **予約投稿削除**: 即時投稿のみ
- **キャラ名取得失敗**: 下書き保存

### 新機能
- **下書き自動保存**: キャラ名取得失敗時
- **エラー回復**: 次の商品へ自動スキップ
- **リソース監視**: VPS制約内での動作
- **cron最適化**: 軽量エントリーポイント

## 📊 変更点サマリー

| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| ディレクトリ数 | 15個 | 6個 |
| ファイル数 | 40+個 | 11個 |
| 重複ファイル | 12個 | 0個 |
| メインエントリー | 2個 | 1個 |
| 予約投稿 | あり | なし |
| 下書き保存 | なし | あり |

## 🔧 使用方法

### VPS向け実行
```bash
# 日次投稿
python src/vps_main.py --mode daily --max-posts 3

# キーワード投稿  
python src/vps_main.py --mode keyword --keyword "キャラ名" --max-posts 2

# デバッグモード
python src/vps_main.py --mode daily --max-posts 1 --debug
```

### 従来版（バックアップ）
```bash
# バックアップディレクトリから実行可能
python backup_old_structure/main.py --daily
```

## 📋 バックアップ情報

- **完全バックアップ**: `backup_old_structure/` に保存
- **復元可能**: 問題時は旧構造に戻せます
- **参考用**: 機能の詳細確認に使用可能

## 🎉 整理完了後の利点

1. **開発効率**: ファイル場所が明確
2. **保守性**: 責任範囲が明確
3. **VPS最適**: リソース効率的
4. **エラー削減**: import文の簡素化
5. **機能向上**: 下書き保存等の新機能

---

**注意**: 整理前の構造は `backup_old_structure/` に保存されています。