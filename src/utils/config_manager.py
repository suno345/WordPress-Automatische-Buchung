import os
import json
from typing import Any, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

class ConfigManager:
    """設定管理クラス（シングルトン）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_file: str = "config.json", env_file: str = ".env"):
        if self._initialized:
            return

        self.config_file = config_file
        self.env_file = env_file
        self.config: Dict[str, Any] = {}
        self.load_defaults()
        self.load_env()
        self.load_config()
        self._initialized = True

    def load_defaults(self) -> None:
        """デフォルト設定を読み込む"""
        self.config = {
            "POSTING_HOURS": [9, 12, 15, 18, 21],
            "POSTS_PER_DAY": 3,
            "MIN_POST_INTERVAL": 3,
            "LOG_DIR": "logs",
            "MAX_LOG_SIZE": 10485760,  # 10MB
            "LOG_BACKUP_COUNT": 5,
            "IMAGE_QUALITY": 85,
            "MAX_IMAGE_SIZE": 5242880,  # 5MB
            "THUMBNAIL_SIZE": (800, 600)
        }

    def load_env(self) -> None:
        """環境変数から設定を読み込む"""
        if os.path.exists(self.env_file):
            load_dotenv(self.env_file)
        
        env_mapping = {
            "FANZA_API_KEY": "FANZA_API_KEY",
            "FANZA_SITE_ID": "FANZA_SITE_ID",
            "WP_API_URL": "WP_API_URL",
            "WP_USERNAME": "WP_USERNAME",
            "WP_PASSWORD": "WP_PASSWORD"
        }

        for env_var, config_key in env_mapping.items():
            if value := os.getenv(env_var):
                self.config[config_key] = value

    def load_config(self) -> None:
        """設定ファイルから設定を読み込む"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    self.config.update(config_data)
        except Exception as e:
            print(f"設定ファイルの読み込みに失敗しました: {e}")

    def save_config(self) -> None:
        """設定をファイルに保存"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"設定ファイルの保存に失敗しました: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """設定値を設定"""
        self.config[key] = value
        self.save_config()

    def update(self, config_dict: Dict[str, Any]) -> None:
        """設定値を一括更新"""
        self.config.update(config_dict)
        self.save_config()

    def reset(self) -> None:
        """設定をリセット"""
        self.config.clear()
        self.load_defaults()
        self.save_config()

    def get_all(self) -> Dict[str, Any]:
        """全設定値を取得"""
        return self.config.copy()

    def set_defaults(self) -> None:
        """デフォルト値を設定"""
        self.load_defaults()
        self.save_config()

    def _load_defaults(self):
        """デフォルト設定の読み込み"""
        self._config = {
            'LOG_DIR': 'logs',
            'LOG_LEVEL': 'INFO',
            'LOG_FORMAT': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'LOG_DATE_FORMAT': '%Y-%m-%d %H:%M:%S',
            'LOG_MAX_BYTES': 10485760,  # 10MB
            'LOG_BACKUP_COUNT': 5,
            'POSTING_HOURS': [10, 14, 18],
            'MAX_POSTS_PER_DAY': 3,
            'MIN_POST_INTERVAL': 3600,  # 1時間
            'MAX_RETRIES': 3,
            'RETRY_DELAY': 5,
            'TIMEOUT': 30,
            'BATCH_SIZE': 10,
            'QUALITY_THRESHOLD': 0.8
        }

    def _load_env(self):
        """環境変数の読み込み"""
        load_dotenv()
        env_vars = {
            'FANZA_API_KEY': os.getenv('FANZA_API_KEY'),
            'FANZA_AFFILIATE_ID': os.getenv('FANZA_AFFILIATE_ID'),
            'WP_URL': os.getenv('WP_URL'),
            'WP_USERNAME': os.getenv('WP_USERNAME'),
            'WP_PASSWORD': os.getenv('WP_PASSWORD'),
            'WP_APP_PASSWORD': os.getenv('WP_APP_PASSWORD'),
            'SPREADSHEET_ID': os.getenv('SPREADSHEET_ID'),
            'CREDENTIALS_FILE': os.getenv('CREDENTIALS_FILE'),
            'TOKEN_FILE': os.getenv('TOKEN_FILE')
        }
        for key, value in env_vars.items():
            if value is not None:
                self._config[key] = value

    def _load_config(self):
        """設定ファイルの読み込み"""
        config_file = Path('config/config.json')
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                self._config.update(config_data)

    def get_log_config(self) -> Dict[str, Any]:
        """
        ログ設定を取得

        Returns:
            Dict[str, Any]: ログ設定
        """
        return self._config["log"]

    def get_api_config(self) -> Dict[str, Any]:
        """
        API設定を取得

        Returns:
            Dict[str, Any]: API設定
        """
        return self._config["api"]

    def get_face_detection_config(self) -> Dict[str, Any]:
        """
        顔検出設定を取得

        Returns:
            Dict[str, Any]: 顔検出設定
        """
        return self._config["face_detection"]

    def get_description_config(self) -> Dict[str, Any]:
        """
        説明生成設定を取得

        Returns:
            Dict[str, Any]: 説明生成設定
        """
        return self._config["description"]

    def get_optimization_config(self) -> Dict[str, Any]:
        """
        コンテンツ最適化設定を取得

        Returns:
            Dict[str, Any]: コンテンツ最適化設定
        """
        return self._config["optimization"]

    def get_error_message(self, category: str, error_type: str) -> str:
        """
        エラーメッセージを取得

        Args:
            category: エラーカテゴリ
            error_type: エラータイプ

        Returns:
            str: エラーメッセージ
        """
        return self._config["error_messages"].get(category, {}).get(error_type, "不明なエラーが発生しました")

    def get_config(self) -> Dict[str, Any]:
        """
        全設定を取得

        Returns:
            Dict[str, Any]: 全設定
        """
        return self._config

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        設定を更新

        Args:
            new_config: 新しい設定
        """
        self._config.update(new_config)

    def reset_config(self) -> None:
        """設定をリセット"""
        self._config = {}
        self._load_defaults()
        self._load_env()
        self._load_config() 