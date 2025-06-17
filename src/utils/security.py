import os
import base64
import hashlib
import hmac
import secrets
from typing import Dict, Optional, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import re
import json
from pathlib import Path
from datetime import datetime

class SecurityManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.key_file = Path("config/encryption.key")
        self._load_or_generate_key()

    def _load_or_generate_key(self):
        """暗号化キーの読み込みまたは生成"""
        if self.key_file.exists():
            with open(self.key_file, "rb") as f:
                self.key = f.read()
        else:
            self.key = Fernet.generate_key()
            self.key_file.parent.mkdir(exist_ok=True)
            with open(self.key_file, "wb") as f:
                f.write(self.key)
        self.fernet = Fernet(self.key)

    def encrypt_data(self, data: str) -> str:
        """データの暗号化"""
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt_data(self, encrypted_data: str) -> str:
        """データの復号化"""
        return self.fernet.decrypt(encrypted_data.encode()).decode()

    def hash_password(self, password: str, salt: Optional[bytes] = None) -> Tuple[str, bytes]:
        """パスワードのハッシュ化"""
        if salt is None:
            salt = secrets.token_bytes(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key.decode(), salt

    def verify_password(self, password: str, hashed_password: str, salt: bytes) -> bool:
        """パスワードの検証"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return hmac.compare_digest(key, hashed_password.encode())

    def generate_api_key(self) -> str:
        """APIキーの生成"""
        return secrets.token_urlsafe(32)

    def validate_api_key(self, api_key: str) -> bool:
        """APIキーの検証"""
        return bool(re.match(r'^[A-Za-z0-9_-]{43}$', api_key))

    def sanitize_input(self, input_str: str) -> str:
        """入力値のサニタイズ"""
        # HTMLエスケープ
        input_str = input_str.replace("&", "&amp;")
        input_str = input_str.replace("<", "&lt;")
        input_str = input_str.replace(">", "&gt;")
        input_str = input_str.replace('"', "&quot;")
        input_str = input_str.replace("'", "&#x27;")
        return input_str

    def validate_email(self, email: str) -> bool:
        """メールアドレスの検証"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def validate_url(self, url: str) -> bool:
        """URLの検証"""
        pattern = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        return bool(re.match(pattern, url))

    def secure_file_operations(self, file_path: str, mode: str = 'r') -> None:
        """セキュアなファイル操作"""
        path = Path(file_path)
        
        # パスの検証
        if not path.is_absolute():
            raise ValueError("絶対パスを使用してください")
        
        # ファイルの存在確認
        if mode == 'r' and not path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
        
        # パーミッションの確認
        if mode == 'r':
            if not os.access(file_path, os.R_OK):
                raise PermissionError(f"ファイルの読み取り権限がありません: {file_path}")
        elif mode == 'w':
            if not os.access(path.parent, os.W_OK):
                raise PermissionError(f"ディレクトリの書き込み権限がありません: {path.parent}")

    def encrypt_config_file(self, config_data: Dict) -> None:
        """設定ファイルの暗号化"""
        encrypted_data = self.encrypt_data(json.dumps(config_data))
        with open(self.config_path, "w") as f:
            json.dump({"encrypted": encrypted_data}, f)

    def decrypt_config_file(self) -> Dict:
        """設定ファイルの復号化"""
        with open(self.config_path, "r") as f:
            data = json.load(f)
        if "encrypted" in data:
            decrypted_data = self.decrypt_data(data["encrypted"])
            return json.loads(decrypted_data)
        return data

    def secure_logging(self, message: str, level: str = "INFO") -> None:
        """セキュアなログ記録"""
        # 機密情報のマスク
        message = re.sub(r'password=["\'](.*?)["\']', 'password="****"', message)
        message = re.sub(r'api_key=["\'](.*?)["\']', 'api_key="****"', message)
        
        # ログファイルへの書き込み
        log_file = Path("logs/secure.log")
        log_file.parent.mkdir(exist_ok=True)
        
        timestamp = datetime.now().isoformat()
        with open(log_file, "a") as f:
            f.write(f"{timestamp} [{level}] {message}\n")

    def validate_json_schema(self, data: Dict, schema: Dict) -> bool:
        """JSONスキーマの検証"""
        def validate_type(value, expected_type):
            if expected_type == "string":
                return isinstance(value, str)
            elif expected_type == "number":
                return isinstance(value, (int, float))
            elif expected_type == "boolean":
                return isinstance(value, bool)
            elif expected_type == "object":
                return isinstance(value, dict)
            elif expected_type == "array":
                return isinstance(value, list)
            return False

        for key, value in data.items():
            if key not in schema:
                return False
            if not validate_type(value, schema[key]):
                return False
        return True 