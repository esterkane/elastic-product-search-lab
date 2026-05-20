import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import settings


class TokenCipher:
    def __init__(self, secret: str) -> None:
        if not secret:
            raise ValueError("FERNET_SECRET is required for OAuth token encryption.")
        self._fernet = Fernet(self._normalize_secret(secret))

    def encrypt(self, value: str | None) -> str | None:
        if value is None:
            return None
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, value: str | None) -> str | None:
        if value is None:
            return None
        return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")

    @staticmethod
    def _normalize_secret(secret: str) -> bytes:
        raw = secret.encode("utf-8")
        try:
            Fernet(raw)
            return raw
        except ValueError:
            digest = hashlib.sha256(raw).digest()
            return base64.urlsafe_b64encode(digest)


token_cipher = TokenCipher(settings.fernet_secret)
