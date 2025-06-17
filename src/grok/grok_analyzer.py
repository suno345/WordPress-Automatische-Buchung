"""
xAI APIを使用して商品画像と情報を分析し、原作名・キャラ名を推測するモジュール
"""
import os
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image
import numpy as np
from insightface.app import FaceAnalysis
from dotenv import load_dotenv

class Grok_Analyzer:
    """xAI APIを使用して商品分析を行うクラス"""
    
    def __init__(self):
        """初期化"""
        # 環境変数の読み込み
        load_dotenv()
        
        # APIキーの取得
        self.api_key = os.getenv('XAI_API_KEY')
        if not self.api_key:
            raise ValueError("xAI APIの認証情報が設定されていません")
        
        # API設定
        self.api_base = "https://api.x.ai/v1"  # 修正: 正しいxAI APIのエンドポイント
        self.endpoint = "/chat/completions"
        self.model = "grok-3"  # xAI公式モデル名
        
        # 顔検出モデルの初期化
        self.face_analyzer = FaceAnalysis(name='buffalo_l', root='.')
        self.face_analyzer.prepare(ctx_id=-1, det_size=(640, 640))
        
        # キャッシュディレクトリの設定
        self.cache_dir = os.getenv('CACHE_DIR', 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # レート制限の設定
        self.rate_limit = asyncio.Semaphore(1)  # 1秒に1リクエスト
        self.last_request_time = 0
    
    async def analyze_product(self, product_info):
        """商品情報を分析し、原作名・キャラ名を推測する"""
        try:
            # キャッシュの確認
            cache_key = f"analysis_{product_info['product_id']}"
            cached_result = await self._get_cache(cache_key)
            if cached_result:
                return cached_result
            
            # 顔画像の取得
            face_images = await self._get_face_images(product_info)
            if not face_images:
                raise Exception("顔画像が見つかりません")
            
            # プロンプトの作成
            prompt = self._create_analysis_prompt(product_info, face_images)
            
            # APIリクエストの送信
            async with self.rate_limit:
                await self._respect_rate_limit()
                try:
                    timeout = aiohttp.ClientTimeout(total=30)  # タイムアウトを30秒に設定
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        headers = {
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        }
                        data = {
                            "model": self.model,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.7,
                            "max_tokens": 1000
                        }
                        print("[DEBUG] xAI APIリクエストを送信")
                        async with session.post(
                            f"{self.api_base}{self.endpoint}",
                            headers=headers,
                            json=data
                        ) as response:
                            if response.status != 200:
                                error_data = await response.text()
                                print(f"[ERROR] xAI APIエラー: {error_data}")
                                raise ValueError(f"xAI APIリクエスト失敗: {response.status}")
                            
                            response_data = await response.json()
                            return response_data["choices"][0]["message"]["content"]
                            
                except aiohttp.ClientError as e:
                    print(f"[ERROR] xAI API接続エラー: {str(e)}")
                    raise ValueError(f"xAI API接続に失敗: {str(e)}")
                
        except Exception as e:
            print(f"[ERROR] 商品分析に失敗: {str(e)}")
            raise ValueError(f"商品分析に失敗: {str(e)}")
    
    def _create_analysis_prompt(self, product_info, face_images):
        """分析用のプロンプトを作成する"""
        prompt = f"""
以下の商品情報と画像から、原作名とキャラクター名を推測してください。
商品タイトル: {product_info['title']}
商品説明: {product_info.get('description', '')}
ジャンル: {', '.join(product_info.get('genre', []))}
メーカー: {', '.join(product_info.get('maker', []))}

以下のJSON形式で回答してください：
{{
    "original_work": "推測された原作名",
    "character_name": "推測されたキャラクター名",
    "confidence": 0.0-1.0の信頼度,
    "reasoning": "推測の理由"
}}
"""
        return prompt
    
    def _parse_analysis_response(self, response):
        """APIレスポンスを解析する"""
        try:
            if isinstance(response, str):
                result = json.loads(response)
            else:
                result = response
            
            # 必須フィールドの確認
            required_fields = ['original_work', 'character_name', 'confidence', 'reasoning']
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"必須フィールド '{field}' が存在しません")
            
            return result
            
        except json.JSONDecodeError:
            raise ValueError("APIレスポンスのJSON解析に失敗しました")
        except Exception as e:
            raise ValueError(f"APIレスポンスの解析に失敗: {str(e)}")
    
    async def _get_face_images(self, product_info):
        """商品画像から顔画像を取得する"""
        try:
            face_images = []
            # 修正: 正しいデータ構造から画像URLを取得
            sample_images = product_info.get('sample_images', [])
            
            for image_url in sample_images[:5]:  # 最大5枚まで処理
                try:
                    # 画像のダウンロード
                    async with aiohttp.ClientSession() as session:
                        async with session.get(image_url) as response:
                            if response.status == 200:
                                image_data = await response.read()
                                image = Image.open(BytesIO(image_data))
                                
                                # 顔の検出とトリミング
                                face_image = await self._detect_and_crop_face(image)
                                if face_image:
                                    face_images.append(face_image)
                except Exception as e:
                    continue  # 個別の画像処理エラーは無視
            
            return face_images
            
        except Exception as e:
            raise Exception(f"顔画像の取得に失敗: {str(e)}")
    
    async def _detect_and_crop_face(self, image):
        """画像から顔を検出し、トリミングする"""
        try:
            # PIL画像をRGBに変換してからNumPy配列に変換
            if image.mode != 'RGB':
                image = image.convert('RGB')
            image_np = np.array(image)
            
            # 顔の検出
            faces = self.face_analyzer.get(image_np)
            print(f"[DEBUG] 検出された顔の数: {len(faces)}")
            
            if not faces:
                print("[DEBUG] 顔が検出されませんでした")
                return None
            
            # 最大の顔を選択
            max_face = max(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))
            
            # 信頼度の確認（閾値を0.3に下げる）
            if max_face.det_score < 0.3:  # 修正: 閾値を0.5から0.3に下げる
                print(f"[DEBUG] 顔の信頼度が低すぎます: {max_face.det_score}")
                return None
            
            print(f"[DEBUG] 検出された顔の信頼度: {max_face.det_score}")
            print(f"[DEBUG] トリミング範囲: {max_face.bbox[:2]} - {max_face.bbox[2:]}")
            
            # 顔の周りの領域を切り出し
            face_image = image.crop((
                max(0, int(max_face.bbox[0])),
                max(0, int(max_face.bbox[1])),
                min(image.width, int(max_face.bbox[2])),
                min(image.height, int(max_face.bbox[3]))
            ))
            
            print("[DEBUG] 顔画像の処理が完了しました")
            return face_image
            
        except Exception as e:
            print(f"[ERROR] 顔の検出中にエラーが発生: {str(e)}")
            return None
    
    async def _get_cache(self, key):
        """キャッシュからデータを取得する"""
        try:
            cache_file = os.path.join(self.cache_dir, f"{key}.json")
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    if datetime.fromisoformat(cache_data['timestamp']) + timedelta(days=7) > datetime.now():
                        return cache_data['data']
            return None
        except Exception:
            return None
    
    async def _save_cache(self, key, data):
        """データをキャッシュに保存する"""
        try:
            cache_file = os.path.join(self.cache_dir, f"{key}.json")
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise Exception(f"キャッシュの保存に失敗: {str(e)}")
    
    async def _respect_rate_limit(self):
        """レート制限を遵守する"""
        now = datetime.now().timestamp()
        if now - self.last_request_time < 1.0:  # 1秒間隔
            await asyncio.sleep(1.0 - (now - self.last_request_time))
        self.last_request_time = datetime.now().timestamp() 