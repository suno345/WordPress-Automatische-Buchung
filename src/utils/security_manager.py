import os
import json
import base64
import hashlib
import re
import secrets
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from src.utils.logger import Logger
from src.utils.config_manager import ConfigManager
from pathlib import Path

class SecurityManager:
    """セキュリティ管理クラス"""

    def __init__(self, key_file: str = 'config/encryption_key.key'):
        self.logger = Logger.get_logger(__name__)
        self.config = ConfigManager()
        self.key_file = Path(key_file)
        self.key = self._load_or_generate_key()
        self.cipher_suite = Fernet(self.key)

    def _load_or_generate_key(self) -> bytes:
        """暗号化キーの読み込みまたは生成"""
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            self.key_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.key_file, 'wb') as f:
                f.write(key)
            return key

    def generate_api_key(self) -> str:
        """APIキーの生成"""
        return secrets.token_urlsafe(32)

    def encrypt_config_file(self, config_file: str) -> None:
        """設定ファイルの暗号化"""
        with open(config_file, 'r', encoding='utf-8') as f:
            data = f.read()
        encrypted_data = self.cipher_suite.encrypt(data.encode())
        with open(f"{config_file}.enc", 'wb') as f:
            f.write(encrypted_data)

    def decrypt_config_file(self, encrypted_file: str) -> str:
        """暗号化された設定ファイルの復号化"""
        with open(encrypted_file, 'rb') as f:
            encrypted_data = f.read()
        decrypted_data = self.cipher_suite.decrypt(encrypted_data)
        return decrypted_data.decode()

    def validate_email(self, email: str) -> bool:
        """メールアドレスの検証"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def sanitize_input(self, input_str: str) -> str:
        """入力のサニタイズ"""
        return re.sub(r'<[^>]*>', '', input_str)

    def hash_password(self, password: str) -> str:
        """パスワードのハッシュ化"""
        salt = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}${base64.b64encode(key).decode()}"

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """パスワードの検証"""
        salt, key = stored_hash.split('$')
        new_key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return base64.b64encode(new_key).decode() == key

    def test_api_key_generation(self) -> str:
        """APIキー生成のテスト"""
        return self.generate_api_key()

    def test_config_encryption(self, config_file: str) -> bool:
        """設定ファイル暗号化のテスト"""
        try:
            self.encrypt_config_file(config_file)
            decrypted_data = self.decrypt_config_file(f"{config_file}.enc")
            with open(config_file, 'r', encoding='utf-8') as f:
                original_data = f.read()
            return decrypted_data == original_data
        except Exception as e:
            print(f"Error: {e}")
            return False

    def test_email_validation(self, email: str) -> bool:
        """メールアドレス検証のテスト"""
        return self.validate_email(email)

    def test_input_sanitization(self, input_str: str) -> str:
        """入力サニタイズのテスト"""
        return self.sanitize_input(input_str)

if __name__ == '__main__':
    # テスト実行
    security = SecurityManager()
    print(f"API Key: {security.test_api_key_generation()}")
    print(f"Config Encryption: {security.test_config_encryption('config/config.json')}")
    print(f"Email Validation: {security.test_email_validation('test@example.com')}")
    print(f"Input Sanitization: {security.test_input_sanitization('<script>alert(\'XSS\')</script>')}") 