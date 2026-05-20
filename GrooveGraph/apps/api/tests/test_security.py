from app.security import TokenCipher


def test_token_cipher_encrypts_and_decrypts_token() -> None:
    cipher = TokenCipher("unit-test-fernet-secret")

    encrypted = cipher.encrypt("spotify-access-token")

    assert encrypted is not None
    assert encrypted != "spotify-access-token"
    assert cipher.decrypt(encrypted) == "spotify-access-token"


def test_token_cipher_preserves_none() -> None:
    cipher = TokenCipher("unit-test-fernet-secret")

    assert cipher.encrypt(None) is None
    assert cipher.decrypt(None) is None
