#!/bin/bash
# 変更内容をコミット

git add -A
git commit -m "[完全対応] テンプレート統合システム実装

## 主な変更内容
- SWELLボタン対応: wp-block-button → swell-block-button
- 詳細無料セクション追加: SEO対策版の海賊版警告文実装
- Jinja2テンプレートエンジン統合: templates/article.html活用
- テンプレートフォールバック機能: エラー時の既存ロジック使用

## 期待される効果
- テンプレート修正が全記事に即座反映
- 記事フォーマットの統一性向上
- 保守性の大幅改善

## テスト結果
- Phase 1: SWELLボタン + 詳細無料セクション実装完了
- Phase 2: Jinja2テンプレートエンジン導入完了  
- Phase 3: テンプレート統合実装完了
- Phase 4: 動作確認とVPS反映準備完了

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

echo "コミット完了"
git log -1 --oneline
git push origin main
echo "プッシュ完了"