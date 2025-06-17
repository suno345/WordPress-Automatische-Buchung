import os
import json
from typing import Any, Dict, Optional
from pathlib import Path
import logging
from dotenv import load_dotenv

class ConfigManager:
    """設定管理クラス"""

    def __init__(self, env_path: str = "API.env"):
        """
        初期化

        Args:
            env_path: 環境変数ファイルのパス
        """
        self.env_path = env_path
        self._load_env()

    def _load_env(self):
        """環境変数の読み込み"""
        if os.path.exists(self.env_path):
            load_dotenv(self.env_path, override=True)

    def get(self, key: str, default: Any = None) -> Any:
        """
        設定値を取得

        Args:
            key: 設定キー
            default: デフォルト値

        Returns:
            設定値
        """
        return os.getenv(key, default)

    def set(self, key: str, value: Any):
        """
        設定値を設定

        Args:
            key: 設定キー
            value: 設定値
        """
        os.environ[key] = str(value)

    def get_all(self) -> dict:
        """
        全ての設定値を取得

        Returns:
            設定値の辞書
        """
        return dict(os.environ)

class Config_Manager:
    """アプリケーションの設定を管理するクラス"""

    def __init__(self, config_dir: str = "config"):
        """
        初期化メソッド

        Args:
            config_dir (str): 設定ファイルを保存するディレクトリパス
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 環境変数の読み込み
        self.env_manager = ConfigManager()
        
        # ロガーの設定
        self.logger = logging.getLogger("config_manager")
        self.logger.setLevel(logging.INFO)
        
        # 設定ファイルのパス
        self.config_file = self.config_dir / "config.json"
        
        # デフォルト設定
        self.default_config = {
            "fanza": {
                "api_id": self.env_manager.get("FANZA_API_ID", ""),
                "affiliate_id": self.env_manager.get("FANZA_AFFILIATE_ID", ""),
                "cache_expiry": {
                    "product_info": 3600,  # 1時間
                    "search_results": 1800  # 30分
                }
            },
            "wordpress": {
                "url": self.env_manager.get("WP_URL", ""),
                "username": self.env_manager.get("WP_USERNAME", ""),
                "password": self.env_manager.get("WP_PASSWORD", ""),
                "categories": ["同人"],
                "tags": ["FANZA"]
            },
            "scheduler": {
                "max_retries": 3,
                "retry_delay": 60,  # 秒
                "posts_per_day": 24,
                "post_interval": 60  # 分
            },
            "grok": {
                "api_key": self.env_manager.get("GROK_API_KEY", ""),
                "model": "grok-1",
                "max_tokens": 1000,
                "temperature": 0.7
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "logs/app.log"
            }
        }
        
        # 設定の読み込み
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """
        設定を読み込む

        Returns:
            Dict[str, Any]: 設定データ
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.logger.info("設定ファイルを読み込みました")
                return config
            except Exception as e:
                self.logger.error(f"設定ファイルの読み込みに失敗しました: {e}")
                return self.default_config
        else:
            self.logger.info("設定ファイルが存在しないため、デフォルト設定を使用します")
            return self.default_config

    def save_config(self) -> bool:
        """
        設定を保存する

        Returns:
            bool: 保存が成功したかどうか
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            self.logger.info("設定を保存しました")
            return True
        except Exception as e:
            self.logger.error(f"設定の保存に失敗しました: {e}")
            return False

    def get_config(self, section: Optional[str] = None) -> Dict[str, Any]:
        """
        設定を取得する

        Args:
            section (Optional[str]): 取得する設定セクション

        Returns:
            Dict[str, Any]: 設定データ
        """
        if section:
            return self.config.get(section, {})
        return self.config

    def update_config(self, section: str, key: str, value: Any) -> bool:
        """
        設定を更新する

        Args:
            section (str): 更新する設定セクション
            key (str): 更新する設定キー
            value (Any): 更新する値

        Returns:
            bool: 更新が成功したかどうか
        """
        try:
            if section not in self.config:
                self.config[section] = {}
            self.config[section][key] = value
            return self.save_config()
        except Exception as e:
            self.logger.error(f"設定の更新に失敗しました: {e}")
            return False

    def validate_config(self) -> bool:
        """
        設定の妥当性を検証する

        Returns:
            bool: 設定が妥当かどうか
        """
        required_fields = {
            "fanza": ["api_id", "affiliate_id"],
            "wordpress": ["url", "username", "password"],
            "grok": ["api_key"]
        }
        
        for section, fields in required_fields.items():
            if section not in self.config:
                self.logger.error(f"必須セクション '{section}' が存在しません")
                return False
            
            for field in fields:
                if field not in self.config[section] or not self.config[section][field]:
                    self.logger.error(f"必須フィールド '{section}.{field}' が設定されていません")
                    return False
        
        return True

    def get_env_value(self, key: str, default: Any = None) -> Any:
        """
        環境変数の値を取得する

        Args:
            key (str): 環境変数名
            default (Any): デフォルト値

        Returns:
            Any: 環境変数の値
        """
        return self.env_manager.get(key, default)

    def set_env_value(self, key: str, value: str) -> None:
        """
        環境変数の値を設定する

        Args:
            key (str): 環境変数名
            value (str): 設定する値
        """
        self.env_manager.set(key, value)

    def reset_to_defaults(self) -> bool:
        """
        設定をデフォルト値にリセットする

        Returns:
            bool: リセットが成功したかどうか
        """
        try:
            self.config = self.default_config.copy()
            return self.save_config()
        except Exception as e:
            self.logger.error(f"設定のリセットに失敗しました: {e}")
            return False 