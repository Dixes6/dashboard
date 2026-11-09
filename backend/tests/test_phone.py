import pytest
from app.core.phone import normalize_phone, prepare_phone_prefix_search


def test_normalize_phone_valid():
    # 11 цифр с ведущей 8
    assert normalize_phone("89123456789") == "79123456789"
    assert normalize_phone("8 (912) 345-67-89") == "79123456789"
    assert normalize_phone("8-912-345-67-89") == "79123456789"

    # 11 цифр с ведущей 7
    assert normalize_phone("+7 (912) 345-67-89") == "79123456789"
    assert normalize_phone("79123456789") == "79123456789"

    # 10 цифр на 9 дополняются 7
    assert normalize_phone("9123456789") == "79123456789"
    assert normalize_phone("912 345 67 89") == "79123456789"


def test_normalize_phone_invalid():
    # Пустой
    with pytest.raises(ValueError):
        normalize_phone("")

    # Меньше 10 цифр
    with pytest.raises(ValueError):
        normalize_phone("91234567")

    # Больше 11 цифр
    with pytest.raises(ValueError):
        normalize_phone("791234567890")

    # 10 цифр, но не на 9
    with pytest.raises(ValueError):
        normalize_phone("8123456789")

    # 11 цифр, не на 7 и не на 8
    with pytest.raises(ValueError):
        normalize_phone("19123456789")

    # Не российские мобильные
    with pytest.raises(ValueError):
        normalize_phone("+1 (912) 345-67-89")


def test_prepare_phone_prefix_search():
    # Пользователь вводит 912, 8912 или +7912 — ведущие 7/8 отбрасываются
    assert prepare_phone_prefix_search("912") == "7912%"
    assert prepare_phone_prefix_search("8912") == "7912%"
    assert prepare_phone_prefix_search("+7912") == "7912%"
    assert prepare_phone_prefix_search("+7 (912)") == "7912%"
    assert prepare_phone_prefix_search("8-912") == "7912%"
    assert prepare_phone_prefix_search("9") == "79%"
