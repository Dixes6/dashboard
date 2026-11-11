"""Tests for stats endpoints: /api/stats/month and /api/stats/months."""
import zoneinfo
from datetime import datetime, timedelta, timezone

import psycopg
from fastapi.testclient import TestClient

from tests.conftest import _login, sync_test_url


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


def _create_appointment_raw(
    client_id: int,
    starts_at: datetime,
    ends_at: datetime | None = None,
    status: str = "completed",
    final_price: int = 2000,
    deleted_at: datetime | None = None,
    service_id: int | None = None,
    service_name: str = "Маникюр",
    service_price_snapshot: int | None = None,
) -> int:
    if ends_at is None or ends_at <= starts_at:
        ends_at = starts_at + timedelta(minutes=60)
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
            if service_id is not None:
                snap_price = (
                    service_price_snapshot
                    if service_price_snapshot is not None
                    else final_price
                )
                cur.execute(
                    """
                    INSERT INTO appointment_services (
                        appointment_id, service_id, name_snapshot,
                        price_snapshot, duration_snapshot, position
                    )
                    VALUES (%s, %s, %s, %s, 60, 0)
                    """,
                    (appt_id, service_id, service_name, snap_price),
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


def test_stats_unauthorized(client: TestClient):
    client.cookies.clear()
    res1 = client.get("/api/stats/month")
    assert res1.status_code == 401
    res2 = client.get("/api/stats/months")
    assert res2.status_code == 401


def test_stats_month_validation_invalid_format(client: TestClient, test_user):
    _login(client, test_user)
    res = client.get("/api/stats/month?month=2026-13")
    assert res.status_code == 422
    res2 = client.get("/api/stats/month?month=invalid")
    assert res2.status_code == 422


def test_stats_empty_month(client: TestClient, test_user):
    _login(client, test_user)
    _setup_settings("Europe/Moscow")

    res = client.get("/api/stats/month?month=2025-01")
    assert res.status_code == 200
    data = res.json()
    assert data["visits_income"] == 0
    assert data["other_income"] == 0
    assert data["income_total"] == 0
    assert data["expenses_total"] == 0
    assert data["net_profit_month"] == 0
    assert data["net_profit_week"] is None  # Прошлый месяц
    assert data["avg_income_per_day"] is None
    assert data["completed_visits_count"] == 0
    assert data["top_service"] is None
    assert data["best_day"] is None


def test_stats_prepared_dataset_and_calculations(client: TestClient, test_user):
    _login(client, test_user)
    _setup_settings("Europe/Moscow")
    tz = zoneinfo.ZoneInfo("Europe/Moscow")

    cl_1 = _create_client_raw("Анна", "79991110001")
    cl_2 = _create_client_raw("Ольга", "79991110002")

    svc_a = _create_service_raw("Маникюр классический", 2000, 60)
    svc_b = _create_service_raw("Покрытие гель-лак", 1500, 45)

    # Запись 1: 5 июня 2026 10:00 (МСК) = 07:00 UTC, completed, 2500 руб, svc_a
    t1_utc = datetime(2026, 6, 5, 10, 0, tzinfo=tz).astimezone(timezone.utc)
    _create_appointment_raw(
        cl_1,
        t1_utc,
        t1_utc,
        status="completed",
        final_price=2500,
        service_id=svc_a,
        service_name="Маникюр классический",
        service_price_snapshot=2000,
    )

    # Запись 2: 5 июня 2026 14:00 (МСК) = 11:00 UTC, completed, 1500 руб, svc_b
    t2_utc = datetime(2026, 6, 5, 14, 0, tzinfo=tz).astimezone(timezone.utc)
    _create_appointment_raw(
        cl_2,
        t2_utc,
        t2_utc,
        status="completed",
        final_price=1500,
        service_id=svc_b,
        service_name="Покрытие гель-лак",
        service_price_snapshot=1500,
    )

    # Прочий доход 5 июня: 500 руб ("Чаевые")
    _create_income_raw(500, "Чаевые", "2026-06-05")

    # Запись 3: 10 июня 2026 12:00 (МСК) = 09:00 UTC, completed, 3000 руб, svc_a
    t3_utc = datetime(2026, 6, 10, 12, 0, tzinfo=tz).astimezone(timezone.utc)
    _create_appointment_raw(
        cl_1,
        t3_utc,
        t3_utc,
        status="completed",
        final_price=3000,
        service_id=svc_a,
        service_name="Маникюр классический",
        service_price_snapshot=2000,
    )

    # Прочий доход 12 июня: 1000 руб ("Продажа масла")
    _create_income_raw(1000, "Продажа масла", "2026-06-12")

    # Расходы: 2000 руб (6 июня) и 1000 руб (15 июня)
    _create_expense_raw(2000, "Материалы", "2026-06-06")
    _create_expense_raw(1000, "Аренда", "2026-06-15")

    res = client.get("/api/stats/month?month=2026-06")
    assert res.status_code == 200
    data = res.json()

    # visits_income = 2500 + 1500 + 3000 = 7000
    assert data["visits_income"] == 7000
    # other_income = 500 + 1000 = 1500
    assert data["other_income"] == 1500
    # income_total = 7000 + 1500 = 8500
    assert data["income_total"] == 8500
    # expenses_total = 2000 + 1000 = 3000
    assert data["expenses_total"] == 3000
    # net_profit_month = 8500 - 3000 = 5500
    assert data["net_profit_month"] == 5500
    # net_profit_week: для месяца не текущего года/месяца -> null
    assert data["net_profit_week"] is None

    # completed_visits_count = 3
    assert data["completed_visits_count"] == 3
    # Дни с визитами: 5 июня и 10 июня -> 2 дня. 7000 // 2 = 3500
    assert data["avg_income_per_day"] == 3500

    # top_service: svc_a (2 оказания, 4000 выручки) против svc_b (1 оказание)
    assert data["top_service"] is not None
    assert data["top_service"]["name"] == "Маникюр классический"
    assert data["top_service"]["count"] == 2
    assert data["top_service"]["revenue"] == 4000

    # best_day: 5 июня (4000 визиты + 500 прочий = 4500 руб)
    assert data["best_day"] is not None
    assert data["best_day"]["date"] == "2026-06-05"
    assert data["best_day"]["income"] == 4500


def test_stats_completed_zero_final_price_counts_as_active_day(
    client: TestClient, test_user
):
    _login(client, test_user)
    _setup_settings("Europe/Moscow")
    tz = zoneinfo.ZoneInfo("Europe/Moscow")

    cl = _create_client_raw("Мама", "79991119999")
    svc = _create_service_raw("Маникюр", 1500, 60)

    # 1. Запись 1 июня: completed, final_price = 0 (родственница)
    t1_utc = datetime(2026, 7, 1, 10, 0, tzinfo=tz).astimezone(timezone.utc)
    _create_appointment_raw(
        cl, t1_utc, t1_utc, status="completed", final_price=0, service_id=svc
    )

    # 2. Запись 2 июня: completed, final_price = 2000
    t2_utc = datetime(2026, 7, 2, 10, 0, tzinfo=tz).astimezone(timezone.utc)
    _create_appointment_raw(
        cl, t2_utc, t2_utc, status="completed", final_price=2000, service_id=svc
    )

    res = client.get("/api/stats/month?month=2026-07")
    assert res.status_code == 200
    data = res.json()

    assert data["visits_income"] == 2000
    assert data["completed_visits_count"] == 2
    # 2 активных дня (1 июля и 2 июля): 2000 // 2 = 1000 руб/день
    assert data["avg_income_per_day"] == 1000


def test_stats_ignored_statuses_and_deleted(client: TestClient, test_user):
    _login(client, test_user)
    _setup_settings("Europe/Moscow")
    tz = zoneinfo.ZoneInfo("Europe/Moscow")

    cl = _create_client_raw("Тест", "79998887766")
    svc = _create_service_raw("Маникюр", 1500, 60)
    t_utc = datetime(2026, 8, 10, 10, 0, tzinfo=tz).astimezone(timezone.utc)

    # scheduled, cancelled, no_show не должны считаться
    _create_appointment_raw(
        cl, t_utc, t_utc, status="scheduled", final_price=1500, service_id=svc
    )
    _create_appointment_raw(
        cl, t_utc, t_utc, status="cancelled", final_price=1500, service_id=svc
    )
    _create_appointment_raw(
        cl, t_utc, t_utc, status="no_show", final_price=1500, service_id=svc
    )
    # completed, но удаленная (deleted_at IS NOT NULL)
    _create_appointment_raw(
        cl,
        t_utc,
        t_utc,
        status="completed",
        final_price=1500,
        deleted_at=datetime.now(timezone.utc),
        service_id=svc,
    )

    # Удаленные доходы и расходы
    _create_income_raw(
        5000,
        occurred_on="2026-08-10",
        deleted_at=datetime.now(timezone.utc),
    )
    _create_expense_raw(
        3000,
        occurred_on="2026-08-10",
        deleted_at=datetime.now(timezone.utc),
    )

    res = client.get("/api/stats/month?month=2026-08")
    assert res.status_code == 200
    data = res.json()
    assert data["visits_income"] == 0
    assert data["other_income"] == 0
    assert data["expenses_total"] == 0
    assert data["completed_visits_count"] == 0
    assert data["avg_income_per_day"] is None
    assert data["top_service"] is None
    assert data["best_day"] is None


def test_stats_midnight_boundary_local_time(client: TestClient, test_user):
    _login(client, test_user)
    _setup_settings("Europe/Moscow")  # UTC+3

    cl = _create_client_raw("Ночная", "79991234567")
    svc = _create_service_raw("Маникюр", 2000, 60)

    # 15 сентября 23:30 МСК = 20:30 UTC 15 сентября
    t1_utc = datetime(2026, 9, 15, 20, 30, tzinfo=timezone.utc)
    # 16 сентября 00:30 МСК = 21:30 UTC 15 сентября
    t2_utc = datetime(2026, 9, 15, 21, 30, tzinfo=timezone.utc)

    _create_appointment_raw(
        cl, t1_utc, t1_utc, status="completed", final_price=2000, service_id=svc
    )
    _create_appointment_raw(
        cl, t2_utc, t2_utc, status="completed", final_price=3000, service_id=svc
    )

    res = client.get("/api/stats/month?month=2026-09")
    assert res.status_code == 200
    data = res.json()

    assert data["visits_income"] == 5000
    # Два разных локальных дня: 15 сентября и 16 сентября
    assert data["completed_visits_count"] == 2
    # 5000 // 2 = 2500
    assert data["avg_income_per_day"] == 2500
    # Лучший день: 16 сентября с 3000 руб
    assert data["best_day"]["date"] == "2026-09-16"
    assert data["best_day"]["income"] == 3000


def test_stats_top_service_tie_breaker_by_revenue(client: TestClient, test_user):
    _login(client, test_user)
    _setup_settings("Europe/Moscow")
    tz = zoneinfo.ZoneInfo("Europe/Moscow")

    cl = _create_client_raw("Тест", "79990001122")
    svc_1 = _create_service_raw("Маникюр дешёвый", 1000, 30)
    svc_2 = _create_service_raw("Маникюр дорогой", 2500, 30)

    # Каждую услугу оказали ровно 2 раза:
    # svc_1: 2 раза по 1000 = 2000 выручки
    # svc_2: 2 раза по 2500 = 5000 выручки
    t_utc = datetime(2026, 10, 5, 12, 0, tzinfo=tz).astimezone(timezone.utc)
    for _ in range(2):
        _create_appointment_raw(
            cl,
            t_utc,
            t_utc,
            status="completed",
            final_price=1000,
            service_id=svc_1,
            service_name="Маникюр дешёвый",
            service_price_snapshot=1000,
        )
        _create_appointment_raw(
            cl,
            t_utc,
            t_utc,
            status="completed",
            final_price=2500,
            service_id=svc_2,
            service_name="Маникюр дорогой",
            service_price_snapshot=2500,
        )

    res = client.get("/api/stats/month?month=2026-10")
    assert res.status_code == 200
    data = res.json()
    assert data["top_service"] is not None
    # При равном count=2 побеждает svc_2 из-за revenue=5000 > 2000
    assert data["top_service"]["name"] == "Маникюр дорогой"
    assert data["top_service"]["count"] == 2
    assert data["top_service"]["revenue"] == 5000


def test_stats_net_profit_week_current_month(client: TestClient, test_user):
    _login(client, test_user)
    _setup_settings("Europe/Moscow")
    tz = zoneinfo.ZoneInfo("Europe/Moscow")

    now_local = datetime.now(tz)
    cur_month_str = now_local.strftime("%Y-%m")

    # Без параметров month -> берется текущий месяц
    res = client.get("/api/stats/month")
    assert res.status_code == 200
    data = res.json()
    # Для текущего месяца net_profit_week должен быть целым числом (int, даже 0), не null!
    assert isinstance(data["net_profit_week"], int)

    # Явный запрос текущего месяца
    res_cur = client.get(f"/api/stats/month?month={cur_month_str}")
    assert res_cur.status_code == 200
    assert isinstance(res_cur.json()["net_profit_week"], int)


def test_stats_months_list_excludes_empty_months(client: TestClient, test_user):
    _login(client, test_user)
    _setup_settings("Europe/Moscow")
    tz = zoneinfo.ZoneInfo("Europe/Moscow")

    cl = _create_client_raw("Анна", "79991113355")
    svc = _create_service_raw("Маникюр", 2000, 60)

    # Месяц 1: 2026-03 - completed запись (1500 руб)
    t1_utc = datetime(2026, 3, 10, 10, 0, tzinfo=tz).astimezone(timezone.utc)
    _create_appointment_raw(
        cl, t1_utc, t1_utc, status="completed", final_price=1500, service_id=svc
    )

    # Месяц 2: 2026-04 - только прочий доход (800 руб)
    _create_income_raw(800, "Продажа", "2026-04-15")

    # Месяц 3: 2026-05 - только расход (500 руб)
    _create_expense_raw(500, "Расходники", "2026-05-20")

    # Месяц 4: 2026-06 - только scheduled запись (НЕ должна попасть в months!)
    t4_utc = datetime(2026, 6, 1, 10, 0, tzinfo=tz).astimezone(timezone.utc)
    _create_appointment_raw(
        cl, t4_utc, t4_utc, status="scheduled", final_price=2000, service_id=svc
    )

    res = client.get("/api/stats/months")
    assert res.status_code == 200
    months_data = res.json()

    # Должны быть 2026-05, 2026-04, 2026-03 (от новых к старым)
    months_keys = [m["month"] for m in months_data]
    assert "2026-06" not in months_keys
    assert months_keys == ["2026-05", "2026-04", "2026-03"]

    m_may = next(m for m in months_data if m["month"] == "2026-05")
    assert m_may["income_total"] == 0
    assert m_may["expenses_total"] == 500
    assert m_may["net_profit"] == -500

    m_apr = next(m for m in months_data if m["month"] == "2026-04")
    assert m_apr["income_total"] == 800
    assert m_apr["expenses_total"] == 0
    assert m_apr["net_profit"] == 800

    m_mar = next(m for m in months_data if m["month"] == "2026-03")
    assert m_mar["income_total"] == 1500
    assert m_mar["expenses_total"] == 0
    assert m_mar["net_profit"] == 1500
