import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
from cryptography.fernet import Fernet
from argon2 import PasswordHasher

class SecurityManager:
    """セキュリティ関連の機能を管理するクラス"""

    def __init__(self, encryption_key: Optional[str] = None):
        """
        初期化

        Args:
            encryption_key: 暗号化キー（オプション）
        """
        self.encryption_key = encryption_key or os.getenv('ENCRYPTION_KEY')
        if not self.encryption_key:
            self.encryption_key = Fernet.generate_key().decode()
        
        self.fernet = Fernet(self.encryption_key.encode())
        self.password_hasher = PasswordHasher()

    def encrypt_data(self, data: str) -> str:
        """
        データを暗号化

        Args:
            data: 暗号化するデータ

        Returns:
            暗号化されたデータ
        """
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt_data(self, encrypted_data: str) -> str:
        """
        データを復号化

        Args:
            encrypted_data: 復号化するデータ

        Returns:
            復号化されたデータ
        """
        return self.fernet.decrypt(encrypted_data.encode()).decode()

    def hash_password(self, password: str) -> str:
        """
        パスワードをハッシュ化

        Args:
            password: ハッシュ化するパスワード

        Returns:
            ハッシュ化されたパスワード
        """
        return self.password_hasher.hash(password)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        パスワードを検証

        Args:
            password: 検証するパスワード
            hashed_password: ハッシュ化されたパスワード

        Returns:
            検証結果
        """
        try:
            self.password_hasher.verify(hashed_password, password)
            return True
        except Exception:
            return False

    def secure_google_credentials(self, credentials_path: str) -> None:
        """
        Google認証情報を安全に保存

        Args:
            credentials_path: 認証情報ファイルのパス
        """
        try:
            # 認証情報の読み込み
            with open(credentials_path, 'r', encoding='utf-8') as f:
                credentials = json.load(f)

            # 機密情報の暗号化
            if 'private_key' in credentials:
                credentials['private_key'] = self.encrypt_data(credentials['private_key'])
            if 'client_email' in credentials:
                credentials['client_email'] = self.encrypt_data(credentials['client_email'])

            # 暗号化された認証情報の保存
            secure_path = f"{credentials_path}.secure"
            with open(secure_path, 'w', encoding='utf-8') as f:
                json.dump(credentials, f, indent=2, ensure_ascii=False)

            # 元のファイルを削除
            os.remove(credentials_path)

        except Exception as e:
            raise Exception(f"認証情報の暗号化に失敗しました: {e}")

    def load_google_credentials(self, secure_credentials_path: str) -> Dict[str, Any]:
        """
        暗号化されたGoogle認証情報を読み込み

        Args:
            secure_credentials_path: 暗号化された認証情報ファイルのパス

        Returns:
            復号化された認証情報
        """
        try:
            # 暗号化された認証情報の読み込み
            with open(secure_credentials_path, 'r', encoding='utf-8') as f:
                credentials = json.load(f)

            # 機密情報の復号化
            if 'private_key' in credentials:
                credentials['private_key'] = self.decrypt_data(credentials['private_key'])
            if 'client_email' in credentials:
                credentials['client_email'] = self.decrypt_data(credentials['client_email'])

            return credentials

        except Exception as e:
            raise Exception(f"認証情報の復号化に失敗しました: {e}")

    def generate_api_key(self) -> str:
        """
        APIキーを生成

        Returns:
            生成されたAPIキー
        """
        return Fernet.generate_key().decode()

    def validate_api_key(self, api_key: str) -> bool:
        """
        APIキーの形式を検証

        Args:
            api_key: 検証するAPIキー

        Returns:
            検証結果
        """
        try:
            Fernet(api_key.encode())
            return True
        except Exception:
            return False 