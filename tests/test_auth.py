from app.auth import hash_password, is_supported_password_hash, verify_password


def test_verify_password_returns_false_for_invalid_hash() -> None:
    assert verify_password("anything", "not-a-real-hash") is False


def test_hash_password_roundtrip() -> None:
    password_hash = hash_password("secret")

    assert is_supported_password_hash(password_hash)
    assert verify_password("secret", password_hash)
    assert not verify_password("wrong", password_hash)
