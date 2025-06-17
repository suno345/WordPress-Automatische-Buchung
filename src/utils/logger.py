import logging
import os
from datetime import datetime
from typing import Optional
from .config_manager import ConfigManager
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger

class Logger:
    """ログ管理クラス"""

    _instance = None
    _logger = None

    def __new__(cls):
        """シングルトンパターンの実装"""
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """初期化"""
        if self._logger is None:
            self._setup_logger()

    def _setup_logger(self):
        """ロガーの設定"""
        config_manager = ConfigManager()
        log_config = config_manager.get_log_config()

        # ログディレクトリの作成
        log_dir = log_config["log_dir"]
        os.makedirs(log_dir, exist_ok=True)

        # ログファイル名の設定
        current_date = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"app_{current_date}.log"

        # ロガーの設定
        self._logger = logging.getLogger("app")
        self._logger.setLevel(log_config["log_level"])

        # 既存のハンドラーをクリア
        self._logger.handlers = []

        # JSONフォーマッターの設定
        json_formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # ファイルハンドラの設定
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(json_formatter)
        self._logger.addHandler(file_handler)

        # コンソールハンドラの設定
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(json_formatter)
        self._logger.addHandler(console_handler)

    def debug(self, message: str, extra: Optional[dict] = None):
        """
        デバッグレベルのログを出力

        Args:
            message: ログメッセージ
            extra: 追加情報
        """
        if extra:
            self._logger.debug(message, extra=extra)
        else:
            self._logger.debug(message)

    def info(self, message: str, extra: Optional[dict] = None):
        """
        情報レベルのログを出力

        Args:
            message: ログメッセージ
            extra: 追加情報
        """
        if extra:
            self._logger.info(message, extra=extra)
        else:
            self._logger.info(message)

    def warning(self, message: str, extra: Optional[dict] = None):
        """
        警告レベルのログを出力

        Args:
            message: ログメッセージ
            extra: 追加情報
        """
        if extra:
            self._logger.warning(message, extra=extra)
        else:
            self._logger.warning(message)

    def error(self, message: str, extra: Optional[dict] = None):
        """
        エラーレベルのログを出力

        Args:
            message: ログメッセージ
            extra: 追加情報
        """
        if extra:
            self._logger.error(message, extra=extra)
        else:
            self._logger.error(message)

    def critical(self, message: str, extra: Optional[dict] = None):
        """
        致命的エラーレベルのログを出力

        Args:
            message: ログメッセージ
            extra: 追加情報
        """
        if extra:
            self._logger.critical(message, extra=extra)
        else:
            self._logger.critical(message)

    def get_logger(self):
        """
        ロガーインスタンスを取得

        Returns:
            logging.Logger: ロガーインスタンス
        """
        return self._logger

def setup_logger(name: str) -> logging.Logger:
    """ロガーの設定を行う

    Args:
        name: ロガー名

    Returns:
        設定済みのロガーインスタンス
    """
    # ログディレクトリの作成
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)

    # ロガーの作成
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 既存のハンドラーをクリア
    logger.handlers = []

    # JSONフォーマッターの設定
    json_formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # ファイルハンドラーの設定
    log_file = os.path.join(log_dir, f'{datetime.now().strftime("%Y%m%d")}.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)

    # コンソールハンドラーの設定
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(json_formatter)
    logger.addHandler(console_handler)

    return logger

def get_logger(name: str) -> logging.Logger:
    """既存のロガーを取得する

    Args:
        name: ロガー名

    Returns:
        ロガーインスタンス
    """
    return logging.getLogger(name) 