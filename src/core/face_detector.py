"""
顔検出・トリミング機能モジュール
アニメ・マンガ画像に特化した顔検出機能
"""

import cv2
import numpy as np
from PIL import Image
import aiohttp
import asyncio
from typing import Optional, List, Tuple, Union
from io import BytesIO
import os
from pathlib import Path

from src.utils.logger import get_logger
from src.utils.error_logger import Error_Logger

class Face_Detector:
    """顔検出・トリミング機能クラス"""
    
    def __init__(self):
        """初期化"""
        self.logger = get_logger(__name__)
        self.error_logger = Error_Logger()
        
        # OpenCVのHaar Cascadesを使用（アニメ顔検出用）
        self.anime_face_cascade = None
        self.face_cascade = None
        
        # カスケードファイルの初期化
        self._initialize_cascades()
        
        # 検出パラメータ
        self.min_face_size = (30, 30)
        self.scale_factor = 1.1
        self.min_neighbors = 5
        self.confidence_threshold = 0.3
    
    def _initialize_cascades(self):
        """カスケード分類器を初期化"""
        try:
            # OpenCVのデフォルト顔検出器
            face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if os.path.exists(face_cascade_path):
                self.face_cascade = cv2.CascadeClassifier(face_cascade_path)
                self.logger.info("OpenCV顔検出器を初期化しました")
            
            # アニメ顔検出器（存在する場合）
            anime_cascade_path = cv2.data.haarcascades + 'haarcascade_anime.xml'
            if os.path.exists(anime_cascade_path):
                self.anime_face_cascade = cv2.CascadeClassifier(anime_cascade_path)
                self.logger.info("アニメ顔検出器を初期化しました")
            else:
                self.logger.warning("アニメ顔検出器が見つかりません、汎用顔検出器を使用します")
                
        except Exception as e:
            self.error_logger.log_error("FACE_DETECTOR_INIT", f"顔検出器初期化エラー: {str(e)}")
            raise ValueError(f"顔検出器の初期化に失敗: {str(e)}")
    
    async def download_image(self, image_url: str) -> Optional[Image.Image]:
        """画像URLから画像をダウンロード"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        image = Image.open(BytesIO(image_data))
                        return image.convert('RGB')
            return None
        except Exception as e:
            self.logger.error(f"画像ダウンロードエラー: {e}")
            return None
    
    def detect_faces(self, image: Union[Image.Image, np.ndarray]) -> List[Tuple[int, int, int, int]]:
        """画像から顔を検出"""
        try:
            # PIL画像をOpenCV形式に変換
            if isinstance(image, Image.Image):
                image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            else:
                image_cv = image
            
            # グレースケール変換
            gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
            
            faces = []
            
            # アニメ顔検出器が利用可能な場合
            if self.anime_face_cascade is not None:
                anime_faces = self.anime_face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=self.scale_factor,
                    minNeighbors=self.min_neighbors,
                    minSize=self.min_face_size
                )
                faces.extend(anime_faces)
                self.logger.debug(f"アニメ顔検出: {len(anime_faces)}個")
            
            # 通常の顔検出器
            if self.face_cascade is not None:
                normal_faces = self.face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=self.scale_factor,
                    minNeighbors=self.min_neighbors,
                    minSize=self.min_face_size
                )
                faces.extend(normal_faces)
                self.logger.debug(f"通常顔検出: {len(normal_faces)}個")
            
            # 重複除去（距離が近い顔を統合）
            unique_faces = self._remove_duplicate_faces(faces)
            
            self.logger.info(f"顔検出完了: {len(unique_faces)}個の顔を検出")
            return unique_faces
            
        except Exception as e:
            self.error_logger.log_error("FACE_DETECTION_ERROR", f"顔検出エラー: {str(e)}")
            return []
    
    def _remove_duplicate_faces(self, faces: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        """重複する顔領域を除去"""
        if len(faces) <= 1:
            return faces
        
        unique_faces = []
        
        for face in faces:
            x, y, w, h = face
            is_duplicate = False
            
            for existing_face in unique_faces:
                ex, ey, ew, eh = existing_face
                
                # 重複判定（IoU: Intersection over Union）
                intersection_area = max(0, min(x + w, ex + ew) - max(x, ex)) * \
                                  max(0, min(y + h, ey + eh) - max(y, ey))
                
                face_area = w * h
                existing_area = ew * eh
                union_area = face_area + existing_area - intersection_area
                
                if union_area > 0:
                    iou = intersection_area / union_area
                    if iou > 0.5:  # 50%以上重複している場合は重複とみなす
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                unique_faces.append(face)
        
        return unique_faces
    
    def crop_face(self, image: Union[Image.Image, np.ndarray], face_coords: Tuple[int, int, int, int], 
                  padding_ratio: float = 0.2) -> Optional[Image.Image]:
        """顔領域をトリミング"""
        try:
            x, y, w, h = face_coords
            
            # PIL画像に変換
            if isinstance(image, np.ndarray):
                if image.shape[2] == 3:  # BGR to RGB
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(image)
            
            # パディングを追加
            padding_w = int(w * padding_ratio)
            padding_h = int(h * padding_ratio)
            
            # トリミング座標を計算
            crop_x = max(0, x - padding_w)
            crop_y = max(0, y - padding_h)
            crop_w = min(image.width, x + w + padding_w)
            crop_h = min(image.height, y + h + padding_h)
            
            # 顔画像をトリミング
            face_image = image.crop((crop_x, crop_y, crop_w, crop_h))
            
            self.logger.debug(f"顔トリミング完了: {crop_x},{crop_y} -> {crop_w},{crop_h}")
            return face_image
            
        except Exception as e:
            self.error_logger.log_error("FACE_CROP_ERROR", f"顔トリミングエラー: {str(e)}")
            return None
    
    async def detect_and_crop_faces_from_url(self, image_url: str, max_faces: int = 5) -> List[Image.Image]:
        """画像URLから顔を検出してトリミング"""
        try:
            # 画像をダウンロード
            image = await self.download_image(image_url)
            if not image:
                return []
            
            # 顔を検出
            faces = self.detect_faces(image)
            if not faces:
                return []
            
            # 顔をサイズ順でソート（大きい順）
            faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
            
            # 最大数まで処理
            faces = faces[:max_faces]
            
            # 各顔をトリミング
            face_images = []
            for face_coords in faces:
                face_image = self.crop_face(image, face_coords)
                if face_image:
                    face_images.append(face_image)
            
            self.logger.info(f"顔検出・トリミング完了: {len(face_images)}個の顔画像を生成")
            return face_images
            
        except Exception as e:
            self.error_logger.log_error("FACE_DETECTION_CROP_ERROR", f"顔検出・トリミングエラー: {str(e)}")
            return []
    
    def detect_and_crop_faces_from_image(self, image: Image.Image, max_faces: int = 5) -> List[Image.Image]:
        """PIL画像から顔を検出してトリミング"""
        try:
            # 顔を検出
            faces = self.detect_faces(image)
            if not faces:
                return []
            
            # 顔をサイズ順でソート（大きい順）
            faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
            
            # 最大数まで処理
            faces = faces[:max_faces]
            
            # 各顔をトリミング
            face_images = []
            for face_coords in faces:
                face_image = self.crop_face(image, face_coords)
                if face_image:
                    face_images.append(face_image)
            
            self.logger.info(f"顔検出・トリミング完了: {len(face_images)}個の顔画像を生成")
            return face_images
            
        except Exception as e:
            self.error_logger.log_error("FACE_DETECTION_CROP_ERROR", f"顔検出・トリミングエラー: {str(e)}")
            return []
    
    async def process_product_images(self, product_info: dict, max_images: int = 3, max_faces_per_image: int = 2) -> List[Image.Image]:
        """商品情報から画像を取得し、顔検出・トリミングを実行"""
        try:
            # 画像URLを取得
            image_urls = []
            
            # sample_imagesから取得
            if 'sample_images' in product_info:
                image_urls.extend(product_info['sample_images'][:max_images])
            
            # imageURLから取得（FANZA API形式）
            elif 'imageURL' in product_info:
                if isinstance(product_info['imageURL'], dict):
                    if 'large' in product_info['imageURL']:
                        image_urls.append(product_info['imageURL']['large'])
                    elif 'medium' in product_info['imageURL']:
                        image_urls.append(product_info['imageURL']['medium'])
                else:
                    image_urls.append(product_info['imageURL'])
            
            if not image_urls:
                self.logger.warning("処理する画像URLが見つかりません")
                return []
            
            # 各画像から顔を検出・トリミング
            all_face_images = []
            
            for image_url in image_urls:
                face_images = await self.detect_and_crop_faces_from_url(image_url, max_faces_per_image)
                all_face_images.extend(face_images)
                
                # 非同期処理間隔
                await asyncio.sleep(0.1)
            
            self.logger.info(f"商品画像処理完了: {len(all_face_images)}個の顔画像を抽出")
            return all_face_images
            
        except Exception as e:
            self.error_logger.log_error("PRODUCT_FACE_PROCESSING_ERROR", f"商品画像顔処理エラー: {str(e)}")
            return []

# 既存コードとの互換性のための関数
async def detect_and_crop_face(image: Image.Image) -> Optional[Image.Image]:
    """単一の顔検出・トリミング（既存コードとの互換性用）"""
    detector = Face_Detector()
    face_images = detector.detect_and_crop_faces_from_image(image, max_faces=1)
    return face_images[0] if face_images else None