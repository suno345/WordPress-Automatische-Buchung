# 🤖 Gemini + Grok ハイブリッド分析システム

## 📋 変更概要

### 旧システム（OpenAI + ローカルモデル）
```
❌ 問題点:
- models/ フォルダ: 600MB（顔認識モデル）
- OpenAI API: 高コスト
- ローカル処理: VPSリソース消費大
- 単一API依存: 障害点
```

### 新システム（Gemini + Grok ハイブリッド）
```
✅ 改善点:
- Gemini API: キャラクター・顔認識（日本コンテンツに強い）
- Grok API: 商品説明文生成（創造性重視）
- 600MB削減: modelsフォルダ不要
- コスト削減: Gemini無料枠 + Grok低価格
- 冗長性: 2つのAI API
```

## 🏗️ 新しいアーキテクチャ

### ハイブリッド分析フロー
```
商品情報
    ↓
[Gemini API]
キャラクター認識・顔認識
    ↓
キャラクター分析結果
    ↓
[Grok API]
商品説明文生成
    ↓
最終結果統合
```

### 作成されたファイル
```
src/core/
├── gemini/
│   └── analyzer.py              # Gemini キャラクター分析
├── grok/
│   └── description_generator.py # Grok 説明文生成
└── hybrid_analyzer.py           # 統合分析クラス

prompts/
├── gemini_character_prompt.txt  # Gemini 用プロンプト
└── grok_description_prompt.txt  # Grok 用プロンプト
```

## ⚙️ 設定方法

### 1. API キー設定
`.env` ファイルに以下を追加：

```bash
# Google Gemini API（キャラクター・顔認識用）
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-1.5-flash
GEMINI_RPM_LIMIT=15

# xAI Grok API（商品説明文生成用）
GROK_API_KEY=your_grok_api_key
GROK_BASE_URL=https://api.x.ai/v1
GROK_MODEL=grok-beta
GROK_RPM_LIMIT=50
```

### 2. API キー取得方法

**Gemini API:**
1. [Google AI Studio](https://aistudio.google.com/) にアクセス
2. 「Get API key」をクリック
3. プロジェクト作成してAPIキー生成
4. **無料枠**: 月15RPM（十分な容量）

**Grok API:**
1. [xAI Console](https://console.x.ai/) にアクセス
2. アカウント作成・ログイン
3. API キー生成
4. **低価格**: OpenAIより安価

## 🔧 使用方法

### VPS実行（変更なし）
```bash
# 既存コマンドがそのまま使用可能
python src/vps_main.py --mode daily --max-posts 3
```

### 内部処理（自動）
```python
# 1. Gemini でキャラクター分析
character_result = await gemini_analyzer.analyze_product(product_info)

# 2. Grok で説明文生成
description = await grok_generator.generate_description(product_info, character_result)

# 3. 結果統合
final_result = {
    'character_name': '春日野穹',
    'original_work': 'ヨスガノソラ', 
    'confidence': 85,
    'generated_description': '魅力的な説明文...',
    'analysis_method': 'hybrid'
}
```

## 📊 品質管理

### 品質スコア（0-100点）
- **キャラクター認識**: 0-50点（信頼度ベース）
- **キャラクター名**: 0-20点（有無）
- **原作名**: 0-15点（有無）
- **説明文品質**: 0-15点（長さ・内容）

### 信頼度別の処理
- **70%以上**: キャラクター名明記
- **50-69%**: 控えめな表現
- **50%未満**: キャラクター名使わず

## 💾 ディスク容量削減

### 削除可能ファイル
```bash
# 600MB のモデルファイル削除
rm -rf models/

# その他不要ファイル
rm -rf backup_old_structure/ tests/ docs/
```

### VPS軽量化効果
- **削除前**: 1.2GB
- **削除後**: 0.6GB  
- **削減量**: 600MB（50%削減）

## 🚀 メリット

### コスト面
- **Gemini**: 月15RPM無料（キャラ認識十分）
- **Grok**: OpenAIより安価（説明文生成）
- **OpenAI**: 不要（削除可能）

### 精度面
- **アニメキャラ認識**: Gemini が優秀
- **日本コンテンツ**: Gemini 特化
- **説明文品質**: Grok の創造性

### 運用面
- **VPS軽量**: 600MB削減
- **冗長性**: 2つのAPI
- **スケーラブル**: API制限分散

## 🔄 移行手順

### 1. 不要ファイル削除
```bash
./scripts/cleanup_vps_files.sh
```

### 2. API キー設定
```bash
nano .env
# Gemini と Grok のAPIキー追加
```

### 3. 動作確認
```bash
python src/vps_main.py --mode daily --max-posts 1 --debug
```

### 4. VPS展開
```bash
./scripts/vps_deploy.sh
```

## 📈 期待効果

1. **コスト削減**: API費用50%以上削減
2. **精度向上**: アニメキャラ認識精度向上
3. **軽量化**: VPS容量50%削減  
4. **安定性**: 複数API冗長化
5. **保守性**: モデル管理不要

---

**注意**: 既存の Grok_Analyzer クラスはハイブリッド分析として動作するため、既存コードの変更は最小限です。