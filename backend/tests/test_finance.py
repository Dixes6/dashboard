"""Tests for finance entries endpoint: /api/finance/entries."""
import zoneinfo
from datetime import datetime, timedelta, timezone

import psycopg
from fastapi.testclient import TestClient

from tests.conftest import sync_test_url


def _login(client: TestClient, test_user):
    res = client.post(
        "/api/auth/login",
        json={"login": "owner", "password": "correct_password"},
    )
    assert res.status_code == 200


def _setup_settings(tz_name: str = "Europe/Moscow"):
    with psycopg.connect(sync_test_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO settings (id, business_name, timezone, slot_step_minutes)
                VALUES (1, 'Студия', %s, 15)
                ON CONFLICT (id) DO UPDATE SET timezone = EXCLUDED.timezone
                """,
                (tz_name,),
            )


def _create_client_raw(name: str = "Анна", phone: str = "79991112233") -> int:
    with psycopg.connect(sync_test_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO clients (name, phone) VALUES (%s, %s) RETURNING id",
                (name, phone),
            )
            return cur.fetchone()[0]


def _create_service_raw(
    name: str = "Маникюр", price: int = 2000, duration: int = 60
) -> int:
    with psycopg.connect(sync_test_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO services (name, price, duration_minutes, is_active, sort_order) "
                "VALUES (%s, %s, %s, true, 0) RETURNING id",
                (name, price, duration),
            )
            return cur.fetchone()[0]


def _create_appointment_with_services(
    client_id: int,
    starts_at: datetime,
    ends_at: datetime | None = None,
    final_price: int = 2000,
    service_tuples: list[tuple[int, str, int]] | None = None,
    status: str = "completed",
    deleted_at: datetime | None = None,
) -> int:
    if ends_at is None or ends_at <= starts_at:
        ends_at = starts_at + timedelta(minutes=60)
    service_tuples = service_tuples or []
    with psycopg.connect(sync_test_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO appointments (
                    client_id, starts_at, ends_at, status, source,
                    list_price, final_price, price_overridden, deleted_at
                )
                VALUES (%s, %s, %s, %s, 'manual', %s, %s, false, %s)
                RETURNING id
                """,
                (
                    client_id,
                    starts_at,
                    ends_at,
                    status,
                    final_price,
                    final_price,
                    deleted_at,
                ),
            )
            appt_id = cur.fetchone()[0]
            for pos, (s_id, s_name, s_price) in enumerate(service_tuples):
                cur.execute(
                    """
                    INSERT INTO appointment_services (
                        appointment_id, service_id, name_snapshot,
                        price_snapshot, duration_snapshot, position
                    )
                    VALUES (%s, %s, %s, %s, 60, %s)
                    """,
                    (appt_id, s_id, s_name, s_price, pos),
                )
            return appt_id


def _create_income_raw(
    amount: int,
    source: str = "Чаевые",
    occurred_on: str = "2026-06-05",
    deleted_at: datetime | None = None,
) -> int:
    with psycopg.connect(sync_test_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO income_entries (amount, source, occurred_on, deleted_at)
                VALUES (%s, %s, %s, %s) RETURNING id
                """,
                (amount, source, occurred_on, deleted_at),
            )
            return cur.fetchone()[0]


def _create_expense_raw(
    amount: int,
    description: str = "Материалы",
    occurred_on: str = "2026-06-06",
    deleted_at: datetime | None = None,
) -> int:
    with psycopg.connect(sync_test_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO expense_entries (amount, description, occurred_on, deleted_at)
                VALUES (%s, %s, %s, %s) RETURNING id
                """,
                (amount, description, occurred_on, deleted_at),
            )
            return cur.fetchone()[0]


def test_finance_unauthorized(client: TestClient):
    client.cookies.clear()
    res = client.get("/api/finance/entries?type=income")
    assert res.status_code == 401


def test_finance_validation_errors(client: TestClient, test_user):
    _login(client, test_user)

    # Missing type param
    res1 = client.get("/api/finance/entries")
    assert res1.status_code == 422

    # Invalid type
    res2 = client.get("/api/finance/entries?type=unknown")
    assert res2.status_code == 422

    # Invalid month format
    res3 = client.get("/api/finance/entries?type=income&month=2026-99")
    assert res3.status_code == 422

    res4 = client.get("/api/finance/entries?type=income&month=abc")
    assert res4.status_code == 422


def test_finance_income_entries_combined(client: TestClient, test_user):
    _login(client, test_user)
    _setup_settings("Europe/Moscow")
    tz = zoneinfo.ZoneInfo("Europe/Moscow")

    cl_1 = _create_client_raw("Анна", "79991112233")
    cl_2 = _create_client_raw("Елена", "79992223344")

    s1 = _create_service_raw("Маникюр", 1500, 60)
    s2 = _create_service_raw("Покрытие гель-лак", 1000, 30)

    # Запись 1: 5 июня 2026, 12:00 МСК (09:00 UTC). Две услуги
    t1_utc = datetime(2026, 6, 5, 12, 0, tzinfo=tz).astimezone(timezone.utc)
    appt1_id = _create_appointment_with_services(
        cl_1,
        t1_utc,
        t1_utc,
        final_price=2500,
        service_tuples=[(s1, "Маникюр", 1500), (s2, "Покрытие гель-лак", 1000)],
    )

    # Ручной доход: 8 июня 2026 (700 руб, Чаевые)
    inc1_id = _create_income_raw(700, "Чаевые", "2026-06-08")

    # Запись 2: 15 июня 2026, 15:00 МСК (12:00 UTC). Одна услуга
    t2_utc = datetime(2026, 6, 15, 15, 0, tzinfo=tz).astimezone(timezone.utc)
    appt2_id = _create_appointment_with_services(
        cl_2,
        t2_utc,
        t2_utc,
        final_price=1500,
        service_tuples=[(s1, "Маникюр", 1500)],
    )

    # Неподходящие записи:
    # (а) Запись другого месяца (май)
    t_may = datetime(2026, 5, 25, 12, 0, tzinfo=tz).astimezone(timezone.utc)
    _create_appointment_with_services(
        cl_1,
        t_may,
        t_may,
        final_price=9999,
        service_tuples=[(s1, "Маникюр", 1500)],
    )
    # (б) Scheduled запись
    _create_appointment_with_services(
        cl_1,
        t1_utc,
        t1_utc,
        final_price=8888,
        service_tuples=[(s1, "Маникюр", 1500)],
        status="scheduled",
    )
    # (в) Удаленная запись
    _create_appointment_with_services(
        cl_1,
        t1_utc,
        t1_utc,
        final_price=7777,
        service_tuples=[(s1, "Маникюр", 1500)],
        deleted_at=datetime.now(timezone.utc),
    )
    # (г) Удаленный доход
    _create_income_raw(
        6666,
        "Удаленный доход",
        "2026-06-08",
        deleted_at=datetime.now(timezone.utc),
    )

    res = client.get("/api/finance/entries?type=income&month=2026-06")
    assert res.status_code == 200
    data = res.json()

    assert data["month"] == "2026-06"
    assert data["type"] == "income"
    # total = 2500 + 700 + 1500 = 4700
    assert data["total"] == 4700

    items = data["items"]
    assert len(items) == 3

    # Проверка порядка: от новых к старым (15 июня -> 8 июня -> 5 июня)
    assert items[0]["date"] == "2026-06-15"
    assert items[0]["kind"] == "visit"
    assert items[0]["amount"] == 1500
    assert items[0]["label"] == "Елена, Маникюр"
    assert items[0]["ref_id"] == appt2_id

    assert items[1]["date"] == "2026-06-08"
    assert items[1]["kind"] == "manual"
    assert items[1]["amount"] == 700
    assert items[1]["label"] == "Чаевые"
    assert items[1]["ref_id"] == inc1_id

    assert items[2]["date"] == "2026-06-05"
    assert items[2]["kind"] == "visit"
    assert items[2]["amount"] == 2500
    assert items[2]["label"] == "Анна, Маникюр, Покрытие гель-лак"
    assert items[2]["ref_id"] == appt1_id

    # Проверка синонима entries
    assert data["entries"] == items


def test_finance_expense_entries(client: TestClient, test_user):
    _login(client, test_user)
    _setup_settings("Europe/Moscow")

    # Расход 1: 10 июня
    exp1_id = _create_expense_raw(1200, "Пилочки и салфетки", "2026-06-10")
    # Расход 2: 20 июня
    exp2_id = _create_expense_raw(3500, "Аренда помещения", "2026-06-20")
    # Расход 3: удаленный (не должен попасть)
    _create_expense_raw(
        9999,
        "Удаленный",
        "2026-06-15",
        deleted_at=datetime.now(timezone.utc),
    )

    res = client.get("/api/finance/entries?type=expense&month=2026-06")
    assert res.status_code == 200
    data = res.json()

    assert data["month"] == "2026-06"
    assert data["type"] == "expense"
    assert data["total"] == 4700

    items = data["items"]
    assert len(items) == 2
    # 20 июня перед 10 июня (от новых к старым)
    assert items[0]["date"] == "2026-06-20"
    assert items[0]["kind"] == "manual"
    assert items[0]["amount"] == 3500
    assert items[0]["label"] == "Аренда помещения"
    assert items[0]["ref_id"] == exp2_id

    assert items[1]["date"] == "2026-06-10"
    assert items[1]["kind"] == "manual"
    assert items[1]["amount"] == 1200
    assert items[1]["label"] == "Пилочки и салфетки"
    assert items[1]["ref_id"] == exp1_id


def test_finance_default_month(client: TestClient, test_user):
    _login(client, test_user)
    _setup_settings("Europe/Moscow")
    tz = zoneinfo.ZoneInfo("Europe/Moscow")

    cur_month_str = datetime.now(tz).strftime("%Y-%m")

    res = client.get("/api/finance/entries?type=income")
    assert res.status_code == 200
    assert res.json()["month"] == cur_month_str
    assert isinstance(res.json()["total"], int)
    assert isinstance(res.json()["items"], list)
