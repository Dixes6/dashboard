"""Tests for review fixes: validation, security exceptions, configuration, and constraints."""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from app.core.config import Settings
from app.core.security import hash_password, verify_password
from app.schemas.client import ClientCreate, ClientUpdate
from app.services.clients import create_client, update_client
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from tests.conftest import _login


def test_jwt_secret_too_short_prevents_startup():
    with pytest.raises(ValidationError) as exc_info:
        Settings(JWT_SECRET_KEY="too_short_secret")
    assert "at least 32 characters" in str(exc_info.value)


def test_jwt_secret_template_prevents_startup():
    with pytest.raises(ValidationError) as exc_info:
        Settings(JWT_SECRET_KEY="change_me_to_a_secure_random_string_at_least_32_chars")
    assert "template value" in str(exc_info.value)


def test_production_cookie_secure_false_raises_error():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            JWT_SECRET_KEY="01234567890123456789012345678901",
            APP_ENV="production",
            COOKIE_SECURE=False,
        )
    assert "COOKIE_SECURE cannot be false in production" in str(exc_info.value)


def test_production_forces_cookie_secure_true():
    # Без COOKIE_SECURE из .env флаг должен принудительно выставиться в True
    s = Settings(
        JWT_SECRET_KEY="01234567890123456789012345678901",
        APP_ENV="production",
        _env_file=None,
    )
    assert s.COOKIE_SECURE is True


def test_verify_password_argon2_exceptions():
    hashed = hash_password("secret_123")
    assert verify_password("secret_123", hashed) is True
    # VerifyMismatchError -> False
    assert verify_password("wrong", hashed) is False
    # InvalidHashError -> False
    assert verify_password("secret_123", "invalid_argon2_hash") is False

    # Unexpected exception is NOT silenced and gets raised
    with patch("app.core.security._pwd_hasher") as mock_pwd:
        mock_pwd.verify.side_effect = RuntimeError("disk failure")
        with pytest.raises(RuntimeError):
            verify_password("secret_123", hashed)


def test_appointment_negative_final_price_returns_422(client: TestClient, test_user):
    _login(client, test_user)

    # POST with negative final_price
    res = client.post(
        "/api/appointments",
        json={
            "starts_at": "2026-11-20T10:00:00Z",
            "service_ids": [1],
            "client": {"name": "Клиент", "phone": "79001112233"},
            "final_price": -500,
        },
    )
    assert res.status_code == 422, f"Expected 422, got {res.status_code}: {res.text}"

    # PATCH with negative final_price
    res_patch = client.patch(
        "/api/appointments/1",
        json={"final_price": -1},
    )
    assert res_patch.status_code == 422


def test_appointment_empty_service_ids_returns_422(client: TestClient, test_user):
    _login(client, test_user)

    # POST with empty service_ids
    res = client.post(
        "/api/appointments",
        json={
            "starts_at": "2026-11-20T10:00:00Z",
            "service_ids": [],
            "client": {"name": "Клиент", "phone": "79001112233"},
        },
    )
    assert res.status_code == 422

    # PATCH with empty service_ids
    res_patch = client.patch(
        "/api/appointments/1",
        json={"service_ids": []},
    )
    assert res_patch.status_code == 422


def test_appointment_starts_at_bounds_returns_422(client: TestClient, test_user):
    _login(client, test_user)

    # starts_at before 2000
    res_past = client.post(
        "/api/appointments",
        json={
            "starts_at": "1999-12-31T23:59:59Z",
            "service_ids": [1],
            "client": {"name": "Клиент", "phone": "79001112233"},
        },
    )
    assert res_past.status_code == 422

    # starts_at > 5 years ahead
    far_future = (datetime.now(timezone.utc) + timedelta(days=6 * 365)).isoformat()
    res_future = client.post(
        "/api/appointments",
        json={
            "starts_at": far_future,
            "service_ids": [1],
            "client": {"name": "Клиент", "phone": "79001112233"},
        },
    )
    assert res_future.status_code == 422


def test_inline_client_validation_returns_422(client: TestClient, test_user):
    _login(client, test_user)

    # Empty name after strip
    res = client.post(
        "/api/appointments",
        json={
            "starts_at": "2026-11-20T10:00:00Z",
            "service_ids": [1],
            "client": {"name": "   ", "phone": "79001112233"},
        },
    )
    assert res.status_code == 422


def test_financial_validation_returns_422(client: TestClient, test_user):
    _login(client, test_user)

    # Income amount <= 0
    res1 = client.post(
        "/api/incomes",
        json={"amount": 0, "source": "Продажа", "occurred_on": "2026-11-10"},
    )
    assert res1.status_code == 422

    # Income amount > 100_000_000
    res2 = client.post(
        "/api/incomes",
        json={"amount": 100_000_001, "source": "Продажа", "occurred_on": "2026-11-10"},
    )
    assert res2.status_code == 422

    # Expense occurred_on before 2000-01-01
    res3 = client.post(
        "/api/expenses",
        json={"amount": 1000, "description": "Расход", "occurred_on": "1999-12-31"},
    )
    assert res3.status_code == 422

    # Expense occurred_on > 1 year in future
    res4 = client.post(
        "/api/expenses",
        json={"amount": 1000, "description": "Расход", "occurred_on": "2030-01-01"},
    )
    assert res4.status_code == 422


def test_work_windows_bulk_validation(client: TestClient, test_user):
    _login(client, test_user)

    # More than 62 dates -> 422
    dates = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(63)]
    res_too_many = client.post(
        "/api/work-windows/bulk",
        json={"dates": dates, "start_time": "10:00:00", "end_time": "18:00:00"},
    )
    assert res_too_many.status_code == 422

    # Duplicate dates collapsed without error
    res_dups = client.post(
        "/api/work-windows/bulk",
        json={
            "dates": ["2026-12-01", "2026-12-01"],
            "start_time": "10:00:00",
            "end_time": "18:00:00",
        },
    )
    assert res_dups.status_code == 201
    assert len(res_dups.json()) == 1


@pytest.mark.anyio
async def test_client_integrity_error_returns_409():
    """Проверяет перехват IntegrityError на уникальном индексе телефона в services/clients.py."""
    from unittest.mock import MagicMock

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    # Имитируем, что предварительный поиск не нашёл дубликат (синхронный first())
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_db.execute.return_value = mock_result
    # При db.commit() база выбрасывает IntegrityError (гонка/уникальный индекс)
    mock_db.commit.side_effect = IntegrityError(
        "uq_clients_phone_active", params=None, orig=Exception()
    )

    # create_client
    with pytest.raises(ValueError) as exc_info:
        await create_client(
            mock_db,
            ClientCreate(name="Анна", phone="79991112233"),
        )
    assert "уже существует" in str(exc_info.value)
    mock_db.rollback.assert_awaited()

    # update_client
    mock_db.rollback.reset_mock()
    with patch("app.services.clients.get_client_by_id") as mock_get:
        mock_client = MagicMock()
        mock_client.phone = "79990000000"
        mock_get.return_value = mock_client
        with pytest.raises(ValueError) as exc_info2:
            await update_client(
                mock_db,
                1,
                ClientUpdate(phone="79991112233"),
            )
        assert "уже существует" in str(exc_info2.value)
        mock_db.rollback.assert_awaited()


def test_client_phone_conflict_api_returns_409(client: TestClient, test_user):
    _login(client, test_user)

    # Создаём первого клиента
    res1 = client.post(
        "/api/clients",
        json={"name": "Клиент 1", "phone": "79887776655"},
    )
    assert res1.status_code == 201

    # Попытка создать второго с тем же номером -> 409
    res2 = client.post(
        "/api/clients",
        json={"name": "Клиент 2", "phone": "79887776655"},
    )
    assert res2.status_code == 409
    assert "уже существует" in res2.json()["detail"]
