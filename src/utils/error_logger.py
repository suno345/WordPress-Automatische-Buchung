import logging
from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path

class ErrorLogger:
    """エラーログ管理クラス"""

    def __init__(self, log_dir: str = "logs"):
        """
        初期化

        Args:
            log_dir: ログディレクトリ
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # ロガーの設定
        self.logger = logging.getLogger("fanza_api")
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

    def log_error(
        self,
        message: str,
        error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        エラーをログに記録

        Args:
            message: エラーメッセージ
            error: 例外オブジェクト（オプション）
            context: コンテキスト情報（オプション）
        """
        log_message = message
        
        if error:
            log_message += f"\nError: {str(error)}"
        
        if context:
            log_message += f"\nContext: {context}"
        
        self.logger.error(log_message)

    def get_recent_errors(self, count: int = 10) -> list:
        """
        最近のエラーを取得

        Args:
            count: 取得するエラー数

        Returns:
            エラーログのリスト
        """
        errors = []
        log_file = self.log_dir / f"error_{datetime.now().strftime('%Y%m%d')}.log"
        
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                errors = [line.strip() for line in lines if "ERROR" in line][-count:]
        
        return errors 