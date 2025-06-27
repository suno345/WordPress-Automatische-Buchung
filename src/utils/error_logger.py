import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import json
from pathlib import Path

class Error_Logger:
    """アプリケーション全体のエラーログを管理するクラス"""

    def __init__(self, log_dir: str = "logs"):
        """
        初期化メソッド

        Args:
            log_dir (str): ログファイルを保存するディレクトリパス
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # ロガーの設定
        self.logger = logging.getLogger("error_logger")
        self.logger.setLevel(logging.ERROR)
        
        # ファイルハンドラの設定
        log_file = self.log_dir / f"error_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.ERROR)
        
        # フォーマッタの設定
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # ハンドラの追加
        self.logger.addHandler(file_handler)
        
        # エラー統計の初期化
        self.error_stats: Dict[str, int] = {}
        self.error_details: Dict[str, list] = {}

    def log_error(
        self,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        product_id: Optional[str] = None
    ) -> None:
        """
        エラーをログに記録する

        Args:
            error_type (str): エラーの種類（例：'API_ERROR', 'PROCESSING_ERROR'）
            message (str): エラーメッセージ
            details (Optional[Dict[str, Any]]): エラーの詳細情報
            product_id (Optional[str]): 関連する商品ID
        """
        # エラーメッセージの構築
        log_message = f"[{error_type}] {message}"
        if product_id:
            log_message = f"[Product: {product_id}] {log_message}"
        
        # エラーの記録
        self.logger.error(log_message, exc_info=True)
        
        # エラー統計の更新
        self.error_stats[error_type] = self.error_stats.get(error_type, 0) + 1
        
        # エラー詳細の保存
        error_detail = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'details': details or {},
            'product_id': product_id
        }
        
        if error_type not in self.error_details:
            self.error_details[error_type] = []
        self.error_details[error_type].append(error_detail)
        
        # エラー詳細をJSONファイルに保存
        self._save_error_details()

    def get_error_stats(self) -> Dict[str, int]:
        """
        エラー統計を取得する

        Returns:
            Dict[str, int]: エラータイプごとの発生回数
        """
        return self.error_stats

    def get_error_details(self, error_type: Optional[str] = None) -> Dict[str, list]:
        """
        エラー詳細を取得する

        Args:
            error_type (Optional[str]): 特定のエラータイプの詳細を取得する場合に指定

        Returns:
            Dict[str, list]: エラータイプごとの詳細情報
        """
        if error_type:
            return {error_type: self.error_details.get(error_type, [])}
        return self.error_details

    def clear_error_stats(self) -> None:
        """エラー統計をクリアする"""
        self.error_stats.clear()
        self.error_details.clear()
        self._save_error_details()

    def _save_error_details(self) -> None:
        """エラー詳細をJSONファイルに保存する"""
        stats_file = self.log_dir / "error_stats.json"
        details_file = self.log_dir / "error_details.json"
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.error_stats, f, ensure_ascii=False, indent=2)
        
        with open(details_file, 'w', encoding='utf-8') as f:
            json.dump(self.error_details, f, ensure_ascii=False, indent=2)

    def load_error_details(self) -> None:
        """保存されたエラー詳細を読み込む"""
        stats_file = self.log_dir / "error_stats.json"
        details_file = self.log_dir / "error_details.json"
        
        if stats_file.exists():
            with open(stats_file, 'r', encoding='utf-8') as f:
                self.error_stats = json.load(f)
        
        if details_file.exists():
            with open(details_file, 'r', encoding='utf-8') as f:
                self.error_details = json.load(f)

    def get_daily_error_summary(self) -> Dict[str, Any]:
        """
        本日のエラーサマリーを取得する

        Returns:
            Dict[str, Any]: 本日のエラー統計と詳細
        """
        today = datetime.now().strftime('%Y%m%d')
        today_errors = {
            'stats': {},
            'details': {}
        }
        
        for error_type, details in self.error_details.items():
            today_details = [
                detail for detail in details
                if detail['timestamp'].startswith(today)
            ]
            
            if today_details:
                today_errors['stats'][error_type] = len(today_details)
                today_errors['details'][error_type] = today_details
        
        return today_errors 