import os
import json
import time
from typing import Any, Optional
from datetime import datetime
from ..utils.logger import setup_logger
from pathlib import Path

class CacheManager:
    """キャッシュ管理クラス"""

    def __init__(self, config):
        """
        初期化

        Args:
            config: 設定マネージャー
        """
        self.config = config
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.logger = setup_logger(__name__)
        self._ensure_cache_dirs()

    def _ensure_cache_dirs(self):
        """キャッシュディレクトリの存在確認と作成"""
        os.makedirs(os.path.join(self.cache_dir, 'api'), exist_ok=True)
        os.makedirs(os.path.join(self.cache_dir, 'images'), exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        """
        キャッシュファイルのパスを取得

        Args:
            key: キャッシュキー

        Returns:
            キャッシュファイルのパス
        """
        return self.cache_dir / f"{key}.json"

    def get(self, key: str) -> Optional[Any]:
        """
        キャッシュから値を取得

        Args:
            key: キャッシュキー

        Returns:
            キャッシュされた値（存在しない場合はNone）
        """
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('expiry', 0) > time.time():
                    return data.get('value')
        except Exception:
            pass

        return None

    def set(self, key: str, value: Any, expiry: int = 3600):
        """
        キャッシュに値を設定

        Args:
            key: キャッシュキー
            value: キャッシュする値
            expiry: 有効期限（秒）
        """
        cache_path = self._get_cache_path(key)
        data = {
            'value': value,
            'expiry': time.time() + expiry
        }

        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def delete(self, key: str):
        """
        キャッシュを削除

        Args:
            key: キャッシュキー
        """
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()

    def clear(self):
        """全てのキャッシュを削除"""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()

    def clear_expired(self):
        """期限切れのキャッシュを削除"""
        cache_dir = os.path.join(self.cache_dir, 'api')
        
        try:
            for filename in os.listdir(cache_dir):
                if filename.endswith('.json'):
                    cache_path = os.path.join(cache_dir, filename)
                    try:
                        with open(cache_path, 'r', encoding='utf-8') as f:
                            cache_data = json.load(f)
                            
                        if cache_data.get('expires_at', 0) < time.time():
                            os.remove(cache_path)
                            
                    except Exception as e:
                        self.logger.error(f"キャッシュファイル処理エラー (ファイル: {filename}): {str(e)}")
                        
        except Exception as e:
            self.logger.error(f"キャッシュクリーンアップエラー: {str(e)}")

    def get_cache_info(self) -> dict:
        """キャッシュの状態情報を取得"""
        cache_dir = os.path.join(self.cache_dir, 'api')
        total_size = 0
        file_count = 0
        expired_count = 0
        
        try:
            for filename in os.listdir(cache_dir):
                if filename.endswith('.json'):
                    file_count += 1
                    cache_path = os.path.join(cache_dir, filename)
                    total_size += os.path.getsize(cache_path)
                    
                    try:
                        with open(cache_path, 'r', encoding='utf-8') as f:
                            cache_data = json.load(f)
                            
                        if cache_data.get('expires_at', 0) < time.time():
                            expired_count += 1
                            
                    except Exception:
                        expired_count += 1
                        
        except Exception as e:
            self.logger.error(f"キャッシュ情報取得エラー: {str(e)}")
            
        return {
            'total_size': total_size,
            'file_count': file_count,
            'expired_count': expired_count,
            'cache_dir': self.cache_dir
        } 