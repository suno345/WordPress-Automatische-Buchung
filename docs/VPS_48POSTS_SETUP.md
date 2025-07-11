# VPS 48件予約投稿システム セットアップガイド

毎日0時に翌日分48件を30分間隔で予約投稿するシステムです。

## 🎯 システム概要

### 実行スケジュール
- **実行時刻**: 毎日 0:00
- **処理内容**: 翌日分48件の予約投稿を作成
- **投稿時間**: 翌日 0:30 から 30分間隔で48件
- **完了条件**: 48件予約完了まで継続実行

### 🆕 キーワード順次検索システム
- **A列がTRUEのキーワード**から順次検索
- **最終処理日時**の古い順に自動選択
- **検索実行後に最終処理日時を自動更新**
- **キーワードが無い場合は通常検索にフォールバック**

### 投稿スケジュール例
```
翌日 0:30 → 1件目投稿（キーワード1）
翌日 1:00 → 2件目投稿（キーワード2）
翌日 1:30 → 3件目投稿（キーワード3）
...
翌日 23:30 → 47件目投稿（キーワード47）
翌日 24:00 → 48件目投稿（キーワード48 or キーワード1循環）
```

### キーワード管理シート構造
| A列 | B列 | C列 | D列 | E列 | F列 | G列 |
|-----|-----|-----|-----|-----|-----|-----|
| 処理フラグ | 原作名 | キャラ名 | 検索キーワード | 最終処理日時 | 最終処理結果 | 備考 |
| TRUE | 初音ミク | 初音ミク | 初音ミク | 2025-01-01 12:00:00 | 成功: 3件 | |
| TRUE | 艦これ | 島風 | 島風 艦これ | 2025-01-01 11:30:00 | 成功: 2件 | |

## 🚀 セットアップ手順

### 1. 自動セットアップ実行

```bash
cd /home/member1/wordpress-auto-post

# 実行権限付与
chmod +x scripts/setup_48posts_cron.sh

# セットアップ実行
./scripts/setup_48posts_cron.sh
```

### 2. 手動セットアップ（必要に応じて）

```bash
# 1. ログファイル作成
sudo mkdir -p /var/log
sudo touch /var/log/wordpress-auto-post-48.log
sudo chown member1:member1 /var/log/wordpress-auto-post-48.log

# 2. cron設定
crontab -e

# 以下を追加
0 0 * * * cd /home/member1/wordpress-auto-post && /home/member1/wordpress-auto-post/venv/bin/python src/vps_main.py --mode schedule48 >> /var/log/wordpress-auto-post-48.log 2>&1
```

## 🧪 テスト実行

### 手動テスト
```bash
# デバッグモードでテスト実行
python src/vps_main.py --mode schedule48 --debug

# 通常モードでテスト実行
python src/vps_main.py --mode schedule48
```

## 📊 監視・管理

### 監視ダッシュボード
```bash
# 総合監視スクリプト実行
chmod +x scripts/monitor_48posts.sh
./scripts/monitor_48posts.sh
```

### ログ確認
```bash
# リアルタイムログ監視
tail -f /var/log/wordpress-auto-post-48.log

# 今日の実行状況確認
grep "$(date +%Y-%m-%d)" /var/log/wordpress-auto-post-48.log

# エラーのみ抽出
grep -i error /var/log/wordpress-auto-post-48.log
```

### cron実行状況確認
```bash
# cron設定確認
crontab -l

# cronサービス状態確認
sudo systemctl status cron

# cron実行ログ確認
sudo tail -f /var/log/cron.log
```

## ⚙️ システム設定

### 環境変数設定
`.env`ファイルで以下を調整可能：

```bash
# VPS向け軽量設定
VPS_MAX_CONCURRENT_TASKS=2     # 同時実行タスク数
VPS_POSTS_PER_RUN=5           # 1回あたりの取得商品数
RETRY_ATTEMPTS=2              # リトライ回数

# API制限対応
MAX_SAMPLE_IMAGES=15          # 画像取得上限
```

### WordPress予約投稿設定
WordPressの投稿スケジュール機能を使用：
- 投稿ステータス: `future`
- 投稿時刻: 指定時刻で自動公開

## 🔧 トラブルシューティング

### よくある問題と解決方法

#### 1. 48件予約投稿が完了しない
```bash
# 原因確認
tail -50 /var/log/wordpress-auto-post-48.log

# 解決策
# - API制限に引っかかった場合: 翌日まで待機
# - 商品重複の場合: 正常動作（新規商品が少ない）
# - エラーの場合: ログでエラー内容を確認
```

#### 2. cron実行されない
```bash
# cron設定確認
crontab -l

# cronサービス再起動
sudo systemctl restart cron

# 手動実行でエラー確認
cd /home/member1/wordpress-auto-post
python src/vps_main.py --mode schedule48 --debug
```

#### 3. メモリ不足エラー
```bash
# メモリ使用量確認
free -h

# プロセス終了
pkill -f vps_main.py

# 設定調整（.env）
VPS_MAX_CONCURRENT_TASKS=1
VPS_POSTS_PER_RUN=3
```

#### 4. API制限エラー
```bash
# エラーログ確認
grep -i "api.*limit\|rate.*limit" /var/log/wordpress-auto-post-48.log

# 対策
# - FANZA API: 1日1000件まで
# - Gemini API: 1分60件まで
# - Grok API: プラン次第
```

## 📈 パフォーマンス最適化

### 推奨設定（VPSスペック別）

#### 低スペック VPS (1GB RAM)
```bash
VPS_MAX_CONCURRENT_TASKS=1
VPS_POSTS_PER_RUN=3
MAX_SAMPLE_IMAGES=10
```

#### 中スペック VPS (2GB RAM)
```bash
VPS_MAX_CONCURRENT_TASKS=2
VPS_POSTS_PER_RUN=5
MAX_SAMPLE_IMAGES=15
```

#### 高スペック VPS (4GB+ RAM)
```bash
VPS_MAX_CONCURRENT_TASKS=3
VPS_POSTS_PER_RUN=10
MAX_SAMPLE_IMAGES=20
```

## 🚨 注意事項

### 運用上の注意
1. **API使用量管理**
   - FANZA API: 1日1000件制限
   - Gemini API: 1分60件制限
   - 制限に近づいたら実行頻度を調整

2. **WordPress負荷**
   - 48件の予約投稿はWordPressに負荷をかけます
   - サーバー性能に応じて投稿数を調整

3. **ディスク容量**
   - ログファイルが蓄積されるため定期削除が必要
   - 画像キャッシュも定期クリア推奨

4. **コンテンツ品質**
   - キャラ名取得失敗時は下書き保存
   - 定期的な手動確認を推奨

### 停止方法
```bash
# cron設定削除
crontab -e
# schedule48行を削除

# 実行中プロセス停止
pkill -f "schedule48"

# ログファイル削除（必要に応じて）
sudo rm /var/log/wordpress-auto-post-48.log
```

## 📞 サポート

### 実行状況確認
- **毎日0:05頃**: 実行開始確認
- **毎日1:00頃**: 進捗確認（予約投稿10件程度完了予定）
- **毎日3:00頃**: 完了確認（48件予約投稿完了予定）

### 監視推奨項目
- ログファイルサイズ
- VPSメモリ使用量
- API使用量
- WordPress投稿数

---

**運用開始後は定期的な監視を行い、必要に応じて設定調整してください。**