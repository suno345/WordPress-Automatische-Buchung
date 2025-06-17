#!/usr/bin/env python3
"""
キャラクター名と原作の組み合わせを検証するバリデーター
"""

class CharacterValidator:
    """キャラクター名と原作の組み合わせを検証するクラス"""
    
    # 同名キャラクターの原作マッピング
    CHARACTER_MAPPING = {
        'アスナ': {
            'ソードアート・オンライン': '結城アスナ',
            'ブルーアーカイブ': '一之瀬アスナ',
        },
        'レム': {
            'Re:ゼロから始める異世界生活': 'レム',
            'デスノート': 'レム',
        },
        'ミク': {
            'ボーカロイド': '初音ミク',
            '五等分の花嫁': '中野三玖',
        },
        # 必要に応じて追加
    }
    
    # タイトルから原作を推測するパターン
    TITLE_PATTERNS = {
        'ブル◯カ': 'ブルーアーカイブ',
        'ブルアカ': 'ブルーアーカイブ',
        'BA': 'ブルーアーカイブ',
        'SA◯': 'ソードアート・オンライン',
        'SAO': 'ソードアート・オンライン',
        'リゼロ': 'Re:ゼロから始める異世界生活',
        'Re:ゼロ': 'Re:ゼロから始める異世界生活',
        '五等分': '五等分の花嫁',
        'ボカロ': 'ボーカロイド',
        'VOCALOID': 'ボーカロイド',
    }
    
    @classmethod
    def detect_original_work_from_title(cls, title: str) -> str:
        """タイトルから原作名を推測"""
        title_upper = title.upper()
        
        for pattern, original_work in cls.TITLE_PATTERNS.items():
            if pattern.upper() in title_upper:
                return original_work
        
        return ""
    
    @classmethod
    def validate_character_original_combination(cls, character_name: str, expected_original: str, title: str) -> dict:
        """キャラクター名と原作の組み合わせを検証"""
        result = {
            'is_valid': True,
            'detected_original': '',
            'expected_character_full_name': '',
            'detected_character_full_name': '',
            'mismatch_reason': ''
        }
        
        # タイトルから原作を推測
        detected_original = cls.detect_original_work_from_title(title)
        result['detected_original'] = detected_original
        
        # キャラクター名の短縮形をチェック
        short_name = character_name
        
        # フルネームからも短縮形を抽出（例: "結城アスナ" → "アスナ"）
        if '　' in character_name:  # 全角スペース
            short_name = character_name.split('　')[-1]
        elif ' ' in character_name:  # 半角スペース
            short_name = character_name.split(' ')[-1]
        else:
            # スペースがない場合、日本の名前パターンを考慮
            # 「結城アスナ」→「アスナ」、「御坂美琴」→「美琴」など
            if len(character_name) >= 3:
                # 一般的に姓は1-2文字、名は2-3文字
                if len(character_name) == 3:
                    short_name = character_name[1:]  # 1文字目を姓として除去
                elif len(character_name) == 4:
                    short_name = character_name[2:]  # 最初の2文字を姓として除去
                elif len(character_name) >= 5:
                    short_name = character_name[2:]  # 最初の2文字を姓として除去
        
        if short_name in cls.CHARACTER_MAPPING:
            # 期待される原作でのフルネーム
            if expected_original in cls.CHARACTER_MAPPING[short_name]:
                result['expected_character_full_name'] = cls.CHARACTER_MAPPING[short_name][expected_original]
            
            # 検出された原作でのフルネーム
            if detected_original and detected_original in cls.CHARACTER_MAPPING[short_name]:
                result['detected_character_full_name'] = cls.CHARACTER_MAPPING[short_name][detected_original]
                
                # 原作が異なる場合
                if detected_original != expected_original:
                    result['is_valid'] = False
                    result['mismatch_reason'] = f"原作相違: タイトルから推測される原作「{detected_original}」の「{result['detected_character_full_name']}」と、期待される原作「{expected_original}」の「{result['expected_character_full_name']}」が異なります"
        
        return result
    
    @classmethod
    def get_validation_prompt_addition(cls, character_name: str, expected_original: str, title: str) -> str:
        """バリデーション結果をプロンプトに追加する文字列を生成"""
        validation = cls.validate_character_original_combination(character_name, expected_original, title)
        
        if not validation['is_valid']:
            return f"\n\n【重要な検証情報】\n{validation['mismatch_reason']}\nこの情報を考慮して判定を行ってください。"
        
        return "" 