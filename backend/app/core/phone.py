import re


def normalize_phone(raw_phone: str) -> str:
    """
    Нормализует номер телефона:
    - оставляет только цифры;
    - ведущую 8 заменяет на 7;
    - 10 цифр на 9 дополняет ведущей 7;
    - сохраняет результат в формате 79123456789.
    При невалидном номере выбрасывает ValueError.
    """
    if not raw_phone or not isinstance(raw_phone, str):
        raise ValueError("Номер телефона не может быть пустым")

    digits = re.sub(r"\D", "", raw_phone)

    if len(digits) == 10:
        if not digits.startswith("9"):
            raise ValueError("10-значный номер телефона должен начинаться с 9")
        digits = "7" + digits
    elif len(digits) == 11:
        if digits.startswith("8"):
            digits = "7" + digits[1:]
        elif not digits.startswith("7"):
            raise ValueError("11-значный номер телефона должен начинаться с 7 или 8")
    else:
        raise ValueError("Номер телефона должен содержать 10 или 11 цифр")

    if len(digits) != 11 or not digits.startswith("79"):
        raise ValueError("Некорректный номер: должен быть российским мобильным номером (79...)")

    return digits


def prepare_phone_prefix_search(raw_query: str) -> str:
    """
    Подготавливает шаблон префикса для поиска по началу номера.
    Пользователь вводит 912, 8912 или +7912.
    Ведущие 7/8 отбрасываются, ищется номер, начинающийся на 7 + эти цифры.
    """
    digits = re.sub(r"\D", "", raw_query)
    if digits.startswith(("7", "8")):
        digits = digits[1:]
    return f"7{digits}%"
