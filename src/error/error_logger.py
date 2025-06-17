"""
エラーログ管理モジュール
"""
import logging
from datetime import datetime

class Error_Logger:
    def __init__(self):
        self.logger = logging.getLogger("Error_Logger")

    def log_error(self, message: str, context: dict = None):
        if context:
            self.logger.error(f"[ERROR] {datetime.now().isoformat()} {message} | context: {context}")
        else:
            self.logger.error(f"[ERROR] {datetime.now().isoformat()} {message}")

    def log_warning(self, message: str):
        self.logger.warning(f"[WARNING] {datetime.now().isoformat()} {message}")

    def log_info(self, message: str):
        self.logger.info(f"[INFO] {datetime.now().isoformat()} {message}")

    def log_debug(self, message: str):
        self.logger.debug(f"[DEBUG] {datetime.now().isoformat()} {message}")

    def get_recent_errors(self):
        # ダミー実装: 実際はログファイルからエラーを抽出する処理を実装
        return [] 