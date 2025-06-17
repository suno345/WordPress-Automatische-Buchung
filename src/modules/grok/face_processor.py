import cv2
import numpy as np
from typing import List, Tuple, Optional
import requests
from io import BytesIO
from PIL import Image
from tenacity import retry, stop_after_attempt, wait_exponential
from ...utils.logger import Logger
from ...utils.config_manager import ConfigManager

class FaceProcessorError(Exception):
    """FaceProcessorのエラー基底クラス"""
    pass

class ImageDownloadError(FaceProcessorError):
    """画像ダウンロードエラー"""
    pass

class ImageProcessingError(FaceProcessorError):
    """画像処理エラー"""
    pass

class FaceDetectionError(FaceProcessorError):
    """顔検出エラー"""
    pass

class FaceCroppingError(FaceProcessorError):
    """顔切り出しエラー"""
    pass

class FaceProcessor:
    """顔画像処理クラス"""

    def __init__(self):
        """初期化"""
        self.logger = Logger()
        self.config_manager = ConfigManager()
        self.face_config = self.config_manager.get_face_detection_config()
        self.api_config = self.config_manager.get_api_config()

        try:
            # Haar Cascade分類器の読み込み
            self.logger.debug("Loading face detection models")
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + self.face_config["models"]["regular_face"]
            )
            self.anime_face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + self.face_config["models"]["anime_face"]
            )
            
            if self.face_cascade.empty() or self.anime_face_cascade.empty():
                error_msg = self.config_manager.get_error_message("face_detection", "model_load")
                self.logger.error(error_msg)
                raise FaceDetectionError(error_msg)
            
            # リトライ設定
            self.max_retries = self.api_config["max_retries"]
            self.retry_delay = self.api_config["retry_delay"]

            self.logger.info("FaceProcessor initialized successfully")

        except Exception as e:
            self.logger.error(f"Initialization failed: {str(e)}")
            raise FaceProcessorError(f"Initialization failed: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    def download_image(self, url: str) -> Optional[np.ndarray]:
        """
        画像をダウンロード

        Args:
            url: 画像URL

        Returns:
            Optional[np.ndarray]: 画像データ（失敗時はNone）

        Raises:
            ImageDownloadError: ダウンロード失敗
        """
        try:
            self.logger.debug(f"Downloading image from URL: {url}")
            response = requests.get(url, timeout=self.api_config["timeout"])
            response.raise_for_status()
            
            # 画像データをNumPy配列に変換
            image = Image.open(BytesIO(response.content))
            image_array = np.array(image)

            self.logger.debug(
                "Image downloaded successfully",
                extra={"image_shape": image_array.shape}
            )

            return image_array

        except requests.exceptions.RequestException as e:
            error_msg = self.config_manager.get_error_message("api", "timeout")
            self.logger.error(f"Failed to download image from {url}: {str(e)}")
            raise ImageDownloadError(f"{error_msg}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Failed to process downloaded image: {str(e)}")
            raise ImageDownloadError(f"Failed to process downloaded image: {str(e)}")

    def detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        画像から顔を検出

        Args:
            image: 画像データ

        Returns:
            List[Tuple[int, int, int, int]]: 検出された顔の座標リスト (x, y, w, h)

        Raises:
            FaceDetectionError: 顔検出失敗
        """
        try:
            self.logger.debug("Starting face detection")

            if image is None or image.size == 0:
                raise FaceDetectionError("Invalid image data")

            # グレースケール変換
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 通常の顔検出
            self.logger.debug("Detecting regular faces")
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=self.face_config["detection_params"]["scale_factor"],
                minNeighbors=self.face_config["detection_params"]["min_neighbors"],
                minSize=self.face_config["detection_params"]["min_size"]
            )
            
            # アニメ顔検出
            self.logger.debug("Detecting anime faces")
            anime_faces = self.anime_face_cascade.detectMultiScale(
                gray,
                scaleFactor=self.face_config["detection_params"]["scale_factor"],
                minNeighbors=self.face_config["detection_params"]["min_neighbors"],
                minSize=self.face_config["detection_params"]["min_size"]
            )
            
            # 結果を結合
            all_faces = list(faces) + list(anime_faces)
            
            if len(all_faces) == 0:
                error_msg = self.config_manager.get_error_message("face_detection", "no_faces")
                self.logger.warning(error_msg)
                raise FaceDetectionError(error_msg)
            
            self.logger.debug(
                "Face detection completed",
                extra={
                    "regular_faces": len(faces),
                    "anime_faces": len(anime_faces),
                    "total_faces": len(all_faces)
                }
            )
            
            return all_faces

        except cv2.error as e:
            error_msg = self.config_manager.get_error_message("face_detection", "processing")
            self.logger.error(f"OpenCV error during face detection: {str(e)}")
            raise FaceDetectionError(f"{error_msg}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Face detection failed: {str(e)}")
            raise FaceDetectionError(f"Face detection failed: {str(e)}")

    def crop_face(
        self,
        image: np.ndarray,
        face_coords: Tuple[int, int, int, int],
        padding: Optional[float] = None
    ) -> Optional[np.ndarray]:
        """
        顔部分を切り出し

        Args:
            image: 画像データ
            face_coords: 顔の座標 (x, y, w, h)
            padding: パディング率（顔の大きさに対する割合）

        Returns:
            Optional[np.ndarray]: 切り出された顔画像（失敗時はNone）

        Raises:
            FaceCroppingError: 顔切り出し失敗
        """
        try:
            if padding is None:
                padding = self.face_config["cropping"]["padding"]

            self.logger.debug(
                "Cropping face from image",
                extra={"face_coords": face_coords, "padding": padding}
            )

            if image is None or image.size == 0:
                raise FaceCroppingError("Invalid image data")

            x, y, w, h = face_coords
            
            # 最小顔サイズのチェック
            if w < self.face_config["cropping"]["min_face_size"] or \
               h < self.face_config["cropping"]["min_face_size"]:
                self.logger.warning(
                    "Face size is too small",
                    extra={"width": w, "height": h, "min_size": self.face_config["cropping"]["min_face_size"]}
                )
                return None
            
            # パディングの計算
            pad_x = int(w * padding)
            pad_y = int(h * padding)
            
            # 画像の範囲内に収まるように調整
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(image.shape[1], x + w + pad_x)
            y2 = min(image.shape[0], y + h + pad_y)
            
            # 顔部分を切り出し
            face_image = image[y1:y2, x1:x2]
            
            if face_image.size == 0:
                raise FaceCroppingError("Cropped face image is empty")

            self.logger.debug(
                "Face cropping completed",
                extra={"cropped_shape": face_image.shape}
            )
            
            return face_image

        except Exception as e:
            self.logger.error(f"Face cropping failed: {str(e)}")
            raise FaceCroppingError(f"Face cropping failed: {str(e)}")

    def process_image(self, image_url: str) -> List[bytes]:
        """
        画像URLから顔を検出して切り出し

        Args:
            image_url: 画像URL

        Returns:
            List[bytes]: 切り出された顔画像のリスト（JPEG形式）

        Raises:
            ImageProcessingError: 画像処理失敗
        """
        try:
            self.logger.info(f"Processing image from URL: {image_url}")

            # 画像ダウンロード
            image = self.download_image(image_url)
            if image is None:
                return []

            # 顔検出
            faces = self.detect_faces(image)
            
            # 顔切り出し
            face_images = []
            for i, face_coords in enumerate(faces, 1):
                self.logger.debug(f"Processing face {i}/{len(faces)}")
                face_image = self.crop_face(image, face_coords)
                if face_image is not None:
                    # JPEG形式に変換
                    _, buffer = cv2.imencode('.jpg', face_image)
                    face_images.append(buffer.tobytes())

            self.logger.info(
                "Image processing completed",
                extra={"faces_detected": len(faces), "faces_cropped": len(face_images)}
            )
            
            return face_images

        except Exception as e:
            error_msg = self.config_manager.get_error_message("face_detection", "processing")
            self.logger.error(f"Image processing failed: {str(e)}")
            raise ImageProcessingError(f"{error_msg}: {str(e)}")

    def process_image_urls(self, urls: List[str], max_faces: Optional[int] = None) -> List[bytes]:
        """
        複数の画像URLから顔を検出して切り出し

        Args:
            urls: 画像URLのリスト
            max_faces: 処理する最大顔数

        Returns:
            List[bytes]: 切り出された顔画像のリスト（JPEG形式）

        Raises:
            ImageProcessingError: 画像処理失敗
        """
        try:
            if max_faces is None:
                max_faces = self.face_config["cropping"]["max_faces"]

            self.logger.info(
                "Starting batch image processing",
                extra={"url_count": len(urls), "max_faces": max_faces}
            )

            if not urls:
                raise ImageProcessingError("No image URLs provided")

            all_face_images = []
            for i, url in enumerate(urls, 1):
                try:
                    self.logger.debug(f"Processing image {i}/{len(urls)}")
                    face_images = self.process_image(url)
                    all_face_images.extend(face_images)
                    
                    if len(all_face_images) >= max_faces:
                        self.logger.info(f"Reached maximum face limit ({max_faces})")
                        break

                except ImageProcessingError as e:
                    self.logger.warning(
                        f"Failed to process image {i}: {str(e)}",
                        extra={"url": url}
                    )
                    continue

            self.logger.info(
                "Batch image processing completed",
                extra={
                    "total_faces": len(all_face_images),
                    "processed_urls": i
                }
            )
            
            return all_face_images[:max_faces]

        except Exception as e:
            error_msg = self.config_manager.get_error_message("face_detection", "processing")
            self.logger.error(f"Batch image processing failed: {str(e)}")
            raise ImageProcessingError(f"{error_msg}: {str(e)}") 