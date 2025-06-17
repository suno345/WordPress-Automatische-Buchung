#!/usr/bin/env python3
"""
商品タイトルから原作の相違を事前に検出するフィルタリング機能
"""
import re

class PreFilter:
    """商品の事前フィルタリングクラス"""
    
    # 原作識別パターン（確実に判定できるもの）
    ORIGINAL_WORK_PATTERNS = {
        'ブルーアーカイブ': [
            r'ブル[◯○〇]?カ',
            r'ブルアカ',
            r'BA(?![A-Z])',  # BAの後に他の文字が続かない場合
            r'Blue\s*Archive',
            r'一之瀬',
            r'角楯',
            r'砂狼',
            r'奥空',
            r'生塩',
            r'黒見',
            r'白洲',
            r'早瀬',
            r'伊草',
            r'才羽',
            r'下江',
            r'鰐淵',
            r'火宮',
            r'美甘',
            r'桐生',
            r'室笠',
            r'久田',
            r'歌住',
            r'小鳥遊',
            r'ア[◯○〇]?ナ.*カ[◯○〇]?ン',  # ア◯ナ&カ◯ンパターン
        ],
        'ソードアート・オンライン': [
            r'SA[◯○〇]?',
            r'SAO',
            r'Sword\s*Art\s*Online',
            r'結城',
            r'桐ヶ谷',
            r'朝田',
            r'篠崎',
            r'新川',
            r'神代',
            r'有田',
            r'安岐',
            r'四方',
            r'比嘉',
            r'藍原',
            r'仲村',
            r'渋谷',
            r'西園',
            r'アインクラッド',
            r'アルヴヘイム',
            r'ガンゲイル',
            r'アンダーワールド',
        ],
        'Re:ゼロから始める異世界生活': [
            r'リゼロ',
            r'Re:?ゼロ',
            r'Re:?Zero',
            r'ナツキ.*スバル',
            r'エミリア.*たん',
            r'レム.*ラム',
            r'ベアトリス',
            r'ロズワール',
            r'ガーフィール',
            r'オットー',
            r'フレデリカ',
            r'ペトラ',
            r'クルシュ',
            r'フェリス',
            r'ヴィルヘルム',
            r'ユリウス',
            r'アナスタシア',
        ],
        '五等分の花嫁': [
            r'五等分',
            r'5等分',
            r'中野.*[一二三四五]玖',
            r'中野.*[いちにさんよんご]つば',
            r'一花.*二乃.*三玖.*四葉.*五月',
            r'上杉.*風太郎',
        ],
        'ボーカロイド': [
            r'初音.*ミク',
            r'鏡音.*リン',
            r'鏡音.*レン',
            r'巡音.*ルカ',
            r'KAITO',
            r'MEIKO',
            r'ボカロ',
            r'VOCALOID',
            r'ミクダヨー',
        ],
        'デスノート': [
            r'デスノート',
            r'Death\s*Note',
            r'夜神.*月',
            r'L.*エル',
            r'弥.*海砂',
            r'ニア',
            r'メロ',
            r'リューク',
            r'レム.*死神',  # デスノートのレム（死神）
        ],
        'とある科学の超電磁砲': [
            r'とある科学',
            r'超電磁砲',
            r'レールガン',
            r'御坂.*美琴',
            r'白井.*黒子',
            r'初春.*飾利',
            r'佐天.*涙子',
            r'食蜂.*操祈',
        ],
        'とある魔術の禁書目録': [
            r'とある魔術',
            r'禁書目録',
            r'インデックス',
            r'上条.*当麻',
            r'インデックス.*シスター',
        ],
        'ウマ娘': [
            r'ウマ娘',
            r'Uma\s*Musume',
            r'スペシャルウィーク',
            r'サイレンススズカ',
            r'トウカイテイオー',
            r'オグリキャップ',
            r'ゴールドシップ',
            r'ダイワスカーレット',
            r'ウオッカ',
            r'エルコンドルパサー',
        ],
        'アズールレーン': [
            r'アズ[◯○〇]?レ',
            r'アズレン',
            r'Azur\s*Lane',
            r'エンタープライズ.*空母',
            r'ベルファスト.*メイド',
            r'プリンツ.*オイゲン',
        ],
        'Fate': [
            r'Fate',
            r'フェイト',
            r'セイバー.*アルトリア',
            r'遠坂.*凛',
            r'間桐.*桜',
            r'衛宮.*士郎',
            r'ギルガメッシュ',
            r'イシュタル',
            r'エレシュキガル',
            r'マシュ.*キリエライト',
            r'藤丸.*立香',
        ],
    }
    
    # 除外すべきキーワード（明らかに異なる原作を示す）
    EXCLUSION_PATTERNS = {
        'ソードアート・オンライン': [
            # ブルーアーカイブ関連
            r'ブル[◯○〇]?カ', r'ブルアカ', r'BA(?![A-Z])', r'Blue\s*Archive',
            r'一之瀬', r'角楯', r'砂狼', r'奥空', r'生塩', r'黒見', r'白洲',
            r'ア[◯○〇]?ナ.*カ[◯○〇]?ン',  # ア◯ナ&カ◯ンパターン
            # その他の原作
            r'リゼロ', r'Re:?ゼロ', r'五等分', r'ボカロ', r'VOCALOID',
            r'デスノート', r'とある科学', r'超電磁砲', r'ウマ娘', r'アズ[◯○〇]?レ',
        ],
        'ブルーアーカイブ': [
            # SAO関連
            r'SA[◯○〇]?', r'SAO', r'Sword\s*Art\s*Online',
            r'結城', r'桐ヶ谷', r'朝田', r'アインクラッド', r'アルヴヘイム',
            # その他の原作
            r'リゼロ', r'Re:?ゼロ', r'五等分', r'ボカロ', r'VOCALOID',
            r'デスノート', r'とある科学', r'超電磁砲', r'ウマ娘',
        ],
        'Re:ゼロから始める異世界生活': [
            # SAO関連
            r'SA[◯○〇]?', r'SAO', r'結城', r'桐ヶ谷',
            # ブルーアーカイブ関連
            r'ブル[◯○〇]?カ', r'ブルアカ', r'BA(?![A-Z])', r'一之瀬', r'角楯',
            # その他
            r'五等分', r'ボカロ', r'デスノート', r'とある科学', r'ウマ娘',
        ],
    }
    
    @classmethod
    def detect_original_work_from_title(cls, title: str) -> str:
        """タイトルから原作を検出（確実性の高いパターンのみ）"""
        if not title:
            return ""
        
        title_clean = title.upper()
        
        # 各原作のパターンをチェック
        for original_work, patterns in cls.ORIGINAL_WORK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, title_clean, re.IGNORECASE):
                    return original_work
        
        return ""
    
    @classmethod
    def detect_character_from_title(cls, title: str, original_work: str) -> str:
        """タイトルから特定の原作のキャラクター名を検出"""
        if not title or not original_work:
            return ""
        
        # 原作別のキャラクター検出パターン
        character_patterns = {
            'ソードアート・オンライン': {
                '結城アスナ': [r'アスナ(?!.*一之瀬)', r'結城.*アスナ', r'明日奈'],
                '桐ヶ谷直葉': [r'直葉', r'桐ケ?谷.*直葉', r'リーファ'],
                '桐ヶ谷和人': [r'キリト', r'桐ケ?谷.*和人', r'和人'],
                '朝田詩乃': [r'シノン', r'朝田.*詩乃', r'詩乃'],
                '綾野珪子': [r'シリカ', r'綾野.*珪子', r'珪子'],
                '篠崎里香': [r'リズベット', r'篠崎.*里香', r'里香'],
                '新川恵': [r'サチ', r'新川.*恵'],
                '紺野木綿季': [r'ユウキ', r'紺野.*木綿季', r'木綿季'],
            },
            'ブルーアーカイブ': {
                '一之瀬アスナ': [r'一之瀬.*アスナ', r'アスナ.*一之瀬', r'ア[◯○〇]?ナ(?=.*ブル)', r'アスナ(?=.*ブルアカ)'],
                '角楯カリン': [r'角楯.*カリン', r'カリン.*角楯', r'カ[◯○〇]?ン'],
                '砂狼シロコ': [r'砂狼.*シロコ', r'シロコ.*砂狼', r'シロコ'],
                '奥空ホシノ': [r'奥空.*ホシノ', r'ホシノ.*奥空', r'ホシノ'],
                '生塩ノノミ': [r'生塩.*ノノミ', r'ノノミ.*生塩', r'ノノミ'],
            },
            'Re:ゼロから始める異世界生活': {
                'レム': [r'レム(?!.*死神)', r'レム(?!.*デスノート)'],
                'ラム': [r'ラム'],
                'エミリア': [r'エミリア', r'EMT'],
                'ベアトリス': [r'ベアトリス', r'ベア子'],
            }
        }
        
        if original_work not in character_patterns:
            return ""
        
        # 該当原作のキャラクターパターンをチェック
        for character_name, patterns in character_patterns[original_work].items():
            for pattern in patterns:
                if re.search(pattern, title, re.IGNORECASE):
                    return character_name
        
        return ""
    
    @classmethod
    def is_character_match(cls, detected_char: str, expected_char: str) -> bool:
        """キャラクター名の一致判定"""
        if not detected_char or not expected_char:
            return False
        
        # 完全一致
        if detected_char == expected_char:
            return True
        
        # 部分一致（どちらかが他方を含む）
        if (detected_char in expected_char or expected_char in detected_char):
            return True
        
        # 名前部分での一致（姓名を分割して比較）
        detected_parts = detected_char.split()
        expected_parts = expected_char.split()
        
        for d_part in detected_parts:
            for e_part in expected_parts:
                if d_part == e_part and len(d_part) > 1:
                    return True
        
        return False
    
    @classmethod
    def should_exclude_product(cls, title: str, expected_original: str, expected_character: str) -> dict:
        """
        商品を除外すべきかどうかを判定
        
        Returns:
            dict: {
                'should_exclude': bool,
                'reason': str,
                'detected_original': str,
                'detected_character': str,
                'action': str,  # 'exclude', 'correct_character', 'proceed'
                'confidence': float
            }
        """
        if not title or not expected_original:
            return {
                'should_exclude': False,
                'reason': '',
                'detected_original': '',
                'detected_character': '',
                'action': 'proceed',
                'confidence': 0.0
            }
        
        # タイトルから原作を検出
        detected_original = cls.detect_original_work_from_title(title)
        
        # タイトルからキャラクター名を検出
        detected_character = cls.detect_character_from_title(title, expected_original)
        
        # 検出された原作が期待される原作と異なる場合（原作相違）
        if detected_original and detected_original != expected_original:
            return {
                'should_exclude': True,
                'reason': f"タイトルから検出された原作「{detected_original}」が期待される原作「{expected_original}」と異なります",
                'detected_original': detected_original,
                'detected_character': detected_character,
                'action': 'exclude',
                'confidence': 0.9
            }
        
        # 原作は一致するが、キャラクター名が相違する場合
        if (detected_character and expected_character and 
            not cls.is_character_match(detected_character, expected_character)):
            return {
                'should_exclude': False,  # 除外はしない
                'reason': f"原作は一致するが、キャラクター名が相違（検出: 「{detected_character}」vs 期待: 「{expected_character}」）",
                'detected_original': detected_original or expected_original,
                'detected_character': detected_character,
                'action': 'correct_character',  # キャラクター名を修正
                'confidence': 0.8
            }
        
        # 除外パターンをチェック（原作相違のみ）
        if expected_original in cls.EXCLUSION_PATTERNS:
            exclusion_patterns = cls.EXCLUSION_PATTERNS[expected_original]
            for pattern in exclusion_patterns:
                if re.search(pattern, title, re.IGNORECASE):
                    return {
                        'should_exclude': True,
                        'reason': f"タイトルに期待される原作「{expected_original}」と相違するパターン「{pattern}」が検出されました",
                        'detected_original': detected_original or '不明',
                        'detected_character': detected_character,
                        'action': 'exclude',
                        'confidence': 0.8
                    }
        
        return {
            'should_exclude': False,
            'reason': '',
            'detected_original': detected_original,
            'detected_character': detected_character,
            'action': 'proceed',
            'confidence': 0.5
        }
    
    @classmethod
    def get_character_full_name(cls, original_work: str, short_name: str) -> str:
        """原作とキャラクター短縮名からフルネームを取得"""
        character_mapping = {
            'ブルーアーカイブ': {
                'アスナ': '一之瀬アスナ',
                'カリン': '角楯カリン',
                'シロコ': '砂狼シロコ',
                'ホシノ': '奥空ホシノ',
                'ノノミ': '生塩ノノミ',
                'セリカ': '黒見セリカ',
                'アヤネ': '白洲アヤネ',
                'ユウカ': '早瀬ユウカ',
                'アカリ': '伊草アカリ',
                'ムツキ': '才羽ムツキ',
                'カヨコ': '下江カヨコ',
                'アル': '鰐淵アル',
                'ヒフミ': '火宮ヒフミ',
                'ネル': '美甘ネル',
                'ユズ': '桐生ユズ',
                'モモイ': '室笠モモイ',
                'ミドリ': '久田ミドリ',
                'アリス': '歌住アリス',
                'ヒナ': '小鳥遊ヒナ',
            },
            'ソードアート・オンライン': {
                'アスナ': '結城アスナ',
                'キリト': '桐ヶ谷和人',
                'シノン': '朝田詩乃',
                'リーファ': '桐ヶ谷直葉',
                'ユウキ': '紺野木綿季',
                'シリカ': '綾野珪子',
                'リズベット': '篠崎里香',
                'サチ': '新川恵',
                'ユナ': '神代凛子',
                'エイジ': '有田洋翔',
                'レイ': '安岐礼奈',
                'ティア': '四方茉莉',
                'ロニエ': '比嘉遼音',
                'ティーゼ': '藍原椿',
                'ソルティリーナ': '仲村奏恵',
                'フレニーカ': '渋谷香音',
                'リネル': '西園梨々花',
            },
            'Re:ゼロから始める異世界生活': {
                'レム': 'レム',
                'ラム': 'ラム',
                'エミリア': 'エミリア',
                'ベアトリス': 'ベアトリス',
                'ペトラ': 'ペトラ・レイテ',
                'フレデリカ': 'フレデリカ・バウマン',
                'クルシュ': 'クルシュ・カルステン',
                'フェリス': 'フェリックス・アーガイル',
                'プリシラ': 'プリシラ・バーリエル',
                'アナスタシア': 'アナスタシア・ホーシン',
                'エルザ': 'エルザ・グランヒルテ',
                'メィリィ': 'メィリィ・ポートルート',
            }
        }
        
        if original_work in character_mapping and short_name in character_mapping[original_work]:
            return character_mapping[original_work][short_name]
        
        return short_name 