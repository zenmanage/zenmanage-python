import pytest

from zenmanage import crc32b, is_in_bucket


def test_crc32b_deterministic() -> None:
    assert crc32b("salt:user-123") == crc32b("salt:user-123")


def test_is_in_bucket_deterministic() -> None:
    first = is_in_bucket("salt", "user-1", 50)
    second = is_in_bucket("salt", "user-1", 50)
    assert first == second


def test_is_in_bucket_percentage_edges() -> None:
    assert not is_in_bucket("salt", "user-1", 0)
    assert is_in_bucket("salt", "user-1", 100)
    assert not is_in_bucket("salt", None, 100)


def test_is_in_bucket_invalid_percentage() -> None:
    with pytest.raises(ValueError):
        is_in_bucket("salt", "user-1", -1)
    with pytest.raises(ValueError):
        is_in_bucket("salt", "user-1", 101)
