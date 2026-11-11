"""Tests for dashboard endpoints: calendar month, day details, and next appointment."""
import zoneinfo
from datetime import datetime, timedelta, timezone

import psycopg
from fastapi.testclient import TestClient

from tests.conftest import _login, sync_test_url


def _create_client_raw(phone: str = "79991112233", name: str = "Клиентка") -> int:
    with psycopg.connect(sync_test_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO clients (name, phone) VALUES (%s, %s) RETURNING id",
                (name, phone),
            )
            return cur.fetchone()[0]


def _create_service_raw(name: str = "Маникюр", price: int = 2000, duration: int = 60) -> int:
    with psycopg.connect(sync_test_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO services (name, price, duration_minutes, is_active, sort_order) "
                "VALUES (%s, %s, %s, true, 0) RETURNING id",
                (name, price, duration),
            )
            return cur.fetchone()[0]


def _create_appointment_raw(
    client_id: int,
    starts_at: datetime,
    ends_at: datetime,
    status: str = "scheduled",
    final_price: int = 2000,
    deleted_at: datetime | None = None,
    service_id: int | None = None,
) -> int:
    with psycopg.connect(sync_test_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO appointments (client_id, starts_at, ends_at, status, source, list_price, final_price, price_overridden, deleted_at)
                VALUES (%s, %s, %s, %s, 'manual', %s, %s, false, %s)
                RETURNING id
                """,
                (client_id, starts_at, ends_at, status, final_price, final_price, deleted_at),
            )
            appt_id = cur.fetchone()[0]
            if service_id is not None:
                cur.execute(
                    """
                    INSERT INTO appointment_services (appointment_id, service_id, name_snapshot, price_snapshot, duration_snapshot, position)
                    VALUES (%s, %s, 'Маникюр', %s, 60, 0)
                    """,
                    (appt_id, service_id, final_price),
                )
            return appt_id


def test_dashboard_unauthorized(client: TestClient):
    client.cookies.clear()
    assert client.get("/api/calendar?month=2026-11").status_code == 401
    assert client.get("/api/days/2026-11-10").status_code == 401
    assert client.get("/api/appointments/next").status_code == 401


def test_calendar_month_validation(client: TestClient, test_user):
    _login(client, test_user)
    # Отсутствует month
    assert client.get("/api/calendar").status_code == 422
    # Неверный формат
    assert client.get("/api/calendar?month=2026-13").status_code == 422
    assert client.get("/api/calendar?month=invalid").status_code == 422


def test_calendar_empty_month(client: TestClient, test_user):
    _login(client, test_user)
    res = client.get("/api/calendar?month=2026-02")
    assert res.status_code == 200
    days = res.json()
    # В 2026 году февраль имеет 28 дней
    assert len(days) == 28
    for d in days:
        assert d["has_work_window"] is False
        assert d["appointments_count"] == 0
        assert d["completed_income"] == 0
    assert days[0]["date"] == "2026-02-01"
    assert days[-1]["date"] == "2026-02-28"


def test_calendar_local_days_and_midnight_boundary(client: TestClient, test_user):
    """
    Проверяем:
    - Разделение записей по локальным суткам (23:30 и 00:30 по Москве).
    - В UTC оба времени могут быть в один календарный день, но в календаре должны быть в разных!
    - Исключение удалённых и отменённых записей.
    - Флаг has_work_window.
    """
    _login(client, test_user)

    cl_id = _create_client_raw()
    svc_id = _create_service_raw()

    # Дефолтная таймзона — Europe/Moscow (UTC+3)
    tz = zoneinfo.ZoneInfo("Europe/Moscow")

    # День 10 ноября 2026, 23:30 локального времени = 20:30 UTC
    # completed, доход 2500
    t1_local = datetime(2026, 11, 10, 23, 30, tzinfo=tz)
    t1_utc = t1_local.astimezone(timezone.utc)
    _create_appointment_raw(
        cl_id, t1_utc, t1_utc + timedelta(minutes=45),
        status="completed", final_price=2500, service_id=svc_id,
    )

    # День 11 ноября 2026, 00:30 локального времени = 21:30 UTC того же 10 ноября!
    # scheduled, доход 1800 (не completed)
    t2_local = datetime(2026, 11, 11, 0, 30, tzinfo=tz)
    t2_utc = t2_local.astimezone(timezone.utc)
    _create_appointment_raw(
        cl_id, t2_utc, t2_utc + timedelta(minutes=60),
        status="scheduled", final_price=1800, service_id=svc_id,
    )

    # Запись 10 ноября: cancelled (не должна учитываться в appointments_count и completed_income)
    t3_local = datetime(2026, 11, 10, 14, 0, tzinfo=tz)
    t3_utc = t3_local.astimezone(timezone.utc)
    _create_appointment_raw(
        cl_id, t3_utc, t3_utc + timedelta(minutes=60),
        status="cancelled", final_price=3000, service_id=svc_id,
    )

    # Запись 10 ноября: completed, но мягко удалена (не должна учитываться)
    t4_local = datetime(2026, 11, 10, 16, 0, tzinfo=tz)
    t4_utc = t4_local.astimezone(timezone.utc)
    _create_appointment_raw(
        cl_id, t4_utc, t4_utc + timedelta(minutes=60),
        status="completed", final_price=5000, deleted_at=datetime.now(timezone.utc), service_id=svc_id,
    )

    # Добавляем окно только на 10 ноября
    with psycopg.connect(sync_test_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO work_windows (date, start_time, end_time) VALUES ('2026-11-10', '10:00:00', '23:59:00')"
            )

    res = client.get("/api/calendar?month=2026-11")
    assert res.status_code == 200
    days = {d["date"]: d for d in res.json()}

    # Проверяем 10 ноября
    day_10 = days["2026-11-10"]
    assert day_10["has_work_window"] is True
    assert day_10["appointments_count"] == 1  # Только completed t1, без cancelled и deleted
    assert day_10["completed_income"] == 2500

    # Проверяем 11 ноября
    day_11 = days["2026-11-11"]
    assert day_11["has_work_window"] is False
    assert day_11["appointments_count"] == 1  # scheduled t2
    assert day_11["completed_income"] == 0    # scheduled не даёт дохода


def test_day_details_endpoint(client: TestClient, test_user):
    """
    GET /api/days/{date}:
    - Окна дня
    - Записи дня с полной информацией
    - visits_income, expected_income, other_income, total_income
    """
    _login(client, test_user)

    cl_id = _create_client_raw(name="Ольга")
    svc_id = _create_service_raw(name="Педикюр", price=3000)
    tz = zoneinfo.ZoneInfo("Europe/Moscow")

    target_date = "2026-11-15"

    # Создаём 2 окна на этот день
    with psycopg.connect(sync_test_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO work_windows (date, start_time, end_time) VALUES (%s, '09:00:00', '13:00:00')",
                (target_date,),
            )
            cur.execute(
                "INSERT INTO work_windows (date, start_time, end_time) VALUES (%s, '14:00:00', '19:00:00')",
                (target_date,),
            )

    # 1. Запись completed (3000 руб)
    t1 = datetime(2026, 11, 15, 10, 0, tzinfo=tz).astimezone(timezone.utc)
    _create_appointment_raw(
        cl_id, t1, t1 + timedelta(hours=1),
        status="completed", final_price=3000, service_id=svc_id,
    )

    # 2. Запись scheduled (2500 руб)
    t2 = datetime(2026, 11, 15, 15, 0, tzinfo=tz).astimezone(timezone.utc)
    _create_appointment_raw(
        cl_id, t2, t2 + timedelta(hours=1),
        status="scheduled", final_price=2500, service_id=svc_id,
    )

    # 3. Запись cancelled (не идёт в доходы)
    t3 = datetime(2026, 11, 15, 17, 0, tzinfo=tz).astimezone(timezone.utc)
    _create_appointment_raw(
        cl_id, t3, t3 + timedelta(hours=1),
        status="cancelled", final_price=4000, service_id=svc_id,
    )

    # 4. Прочий доход этого дня: активный (700 руб)
    with psycopg.connect(sync_test_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO income_entries (amount, source, occurred_on) VALUES (700, 'Чаевые', %s)",
                (target_date,),
            )
            # Прочий доход: удалённый (не должен считаться)
            cur.execute(
                "INSERT INTO income_entries (amount, source, occurred_on, deleted_at) VALUES (1000, 'Удаленный', %s, %s)",
                (target_date, datetime.now(timezone.utc)),
            )
            # Прочий доход другого дня (не должен считаться)
            cur.execute(
                "INSERT INTO income_entries (amount, source, occurred_on) VALUES (999, 'Другой день', '2026-11-16')",
            )

    res = client.get(f"/api/days/{target_date}")
    assert res.status_code == 200
    data = res.json()

    # Проверяем окна
    assert len(data["work_windows"]) == 2
    assert data["work_windows"][0]["start_time"] == "09:00:00"
    assert data["work_windows"][1]["start_time"] == "14:00:00"

    # Проверяем записи дня (3 записи: completed, scheduled, cancelled)
    assert len(data["appointments"]) == 3
    for appt in data["appointments"]:
        assert appt["local_date"] == target_date
        assert appt["client"]["name"] == "Ольга"

    # Проверяем доходы:
    # visits_income = completed (3000)
    assert data["visits_income"] == 3000
    # expected_income = scheduled (2500)
    assert data["expected_income"] == 2500
    # other_income = 700 (без удалённых и без другого дня)
    assert data["other_income"] == 700
    # total_income = visits_income + other_income = 3000 + 700 = 3700
    assert data["total_income"] == 3700


def test_next_appointment_endpoint(client: TestClient, test_user):
    """
    GET /api/appointments/next:
    - Если нет записей -> 204
    - Если запись в прошлом -> 204
    - Если запись в будущем cancelled/completed/deleted -> 204
    - Если несколько scheduled в будущем -> возвращает ближайшую со статусом 200
    """
    _login(client, test_user)

    # 1. База пустая -> 204
    res = client.get("/api/appointments/next")
    assert res.status_code == 204

    cl_id = _create_client_raw()
    svc_id = _create_service_raw()

    now = datetime.now(timezone.utc)

    # 2. Запись в прошлом -> 204
    past_starts = now - timedelta(hours=2)
    _create_appointment_raw(
        cl_id, past_starts, past_starts + timedelta(hours=1),
        status="scheduled", service_id=svc_id,
    )
    assert client.get("/api/appointments/next").status_code == 204

    # 3. Записи в будущем: cancelled, completed, deleted -> 204
    future_1 = now + timedelta(hours=1)
    _create_appointment_raw(
        cl_id, future_1, future_1 + timedelta(hours=1),
        status="cancelled", service_id=svc_id,
    )
    _create_appointment_raw(
        cl_id, future_1 + timedelta(hours=2), future_1 + timedelta(hours=3),
        status="completed", service_id=svc_id,
    )
    _create_appointment_raw(
        cl_id, future_1 + timedelta(hours=4), future_1 + timedelta(hours=5),
        status="scheduled", deleted_at=now, service_id=svc_id,
    )
    assert client.get("/api/appointments/next").status_code == 204

    # 4. Две валидные scheduled записи в будущем (+3 часа и +6 часов)
    near_starts = now + timedelta(hours=3)
    near_id = _create_appointment_raw(
        cl_id, near_starts, near_starts + timedelta(hours=1),
        status="scheduled", final_price=2200, service_id=svc_id,
    )
    far_starts = now + timedelta(hours=6)
    _create_appointment_raw(
        cl_id, far_starts, far_starts + timedelta(hours=1),
        status="scheduled", final_price=3300, service_id=svc_id,
    )

    res = client.get("/api/appointments/next")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == near_id
    assert data["status"] == "scheduled"
    assert data["final_price"] == 2200
    assert len(data["services"]) == 1
    assert data["client"]["id"] == cl_id
