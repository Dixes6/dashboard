"""Tests for appointments API."""
from datetime import datetime, timedelta, timezone

import psycopg
from fastapi.testclient import TestClient

from tests.conftest import _login, _real_login, sync_test_url


def _create_service(
    client: TestClient,
    name: str = "Маникюр",
    price: int = 1500,
    duration: int = 60,
) -> dict:
    res = client.post(
        "/api/services",
        json={"name": name, "price": price, "duration_minutes": duration},
    )
    assert res.status_code == 201, res.text
    return res.json()


def _create_work_window(
    client: TestClient,
    target_date: str = "2024-06-15",
    start_time: str = "09:00:00",
    end_time: str = "18:00:00",
) -> dict:
    res = client.post(
        "/api/work-windows",
        json={"date": target_date, "start_time": start_time, "end_time": end_time},
    )
    assert res.status_code == 201, res.text
    return res.json()


def _create_client_via_api(
    client: TestClient,
    name: str = "Анна",
    phone: str = "79001112233",
) -> dict:
    res = client.post(
        "/api/clients",
        json={"name": name, "phone": phone},
    )
    assert res.status_code == 201, res.text
    return res.json()


def test_appt_unauthorized(client: TestClient):
    client.cookies.clear()
    res = client.get("/api/appointments")
    assert res.status_code == 401


def test_create_appointment_basic(client: TestClient, test_user):
    _real_login(client, test_user)

    svc = _create_service(client, name="Маникюр", price=1500, duration=60)
    _create_work_window(client, "2024-06-15", "09:00:00", "18:00:00")
    cl = _create_client_via_api(client)

    # starts_at as Moscow time (naive → treated as local)
    # 2024-06-15 10:00 Moscow = 2024-06-15 07:00 UTC
    res = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-06-15T10:00:00",
            "service_ids": [svc["id"]],
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["list_price"] == 1500
    assert data["final_price"] == 1500
    assert data["price_overridden"] is False
    assert len(data["services"]) == 1
    assert data["services"][0]["name_snapshot"] == "Маникюр"
    assert data["services"][0]["price_snapshot"] == 1500
    assert data["services"][0]["duration_snapshot"] == 60

    assert data["local_date"] == "2024-06-15"
    assert data["local_start_time"] == "10:00:00"
    assert data["local_end_time"] == "11:00:00"  # +60 min

    assert data["status"] == "scheduled"
    assert data["warnings"] == []


def test_snapshots_not_changed_on_price_change(client: TestClient, test_user):
    """Changing service price must NOT affect existing appointment snapshots."""
    _login(client, test_user)

    svc = _create_service(client, name="Педикюр", price=2000, duration=90)
    _create_work_window(client, "2024-06-15", "09:00:00", "18:00:00")
    cl = _create_client_via_api(client)

    res = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-06-15T10:00:00",
            "service_ids": [svc["id"]],
        },
    )
    assert res.status_code == 201
    appt_id = res.json()["id"]

    # Update service price
    client.patch(f"/api/services/{svc['id']}", json={"price": 3000})

    # Check appointment snapshot unchanged
    get_res = client.get(f"/api/appointments/{appt_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["services"][0]["price_snapshot"] == 2000
    assert data["list_price"] == 2000


def test_service_ids_patch_keeps_old_snapshots(client: TestClient, test_user):
    """PATCH with service_ids: existing services keep old snapshots, new ones get current price.
    Сценарий (а): price_overridden = false, final_price пересчитывается в list_price."""
    _login(client, test_user)

    svc_a = _create_service(client, name="Услуга А", price=1000, duration=30)
    svc_b = _create_service(client, name="Услуга Б", price=800, duration=30)
    _create_work_window(client, "2024-06-15", "09:00:00", "18:00:00")
    cl = _create_client_via_api(client)

    # Create appointment with service A only (price_overridden = false)
    res = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-06-15T10:00:00",
            "service_ids": [svc_a["id"]],
        },
    )
    assert res.status_code == 201
    appt_id = res.json()["id"]
    assert res.json()["price_overridden"] is False
    assert res.json()["final_price"] == 1000

    # Update service A price in catalog
    client.patch(f"/api/services/{svc_a['id']}", json={"price": 9999})

    # PATCH appointment to include A and B
    patch_res = client.patch(
        f"/api/appointments/{appt_id}",
        json={"service_ids": [svc_a["id"], svc_b["id"]]},
    )
    assert patch_res.status_code == 200, patch_res.text
    data = patch_res.json()

    # Find snapshots by service_id
    snap_a = next(s for s in data["services"] if s["service_id"] == svc_a["id"])
    snap_b = next(s for s in data["services"] if s["service_id"] == svc_b["id"])

    # A keeps OLD snapshot (1000, not 9999)
    assert snap_a["price_snapshot"] == 1000
    # B gets current price (800)
    assert snap_b["price_snapshot"] == 800

    # list_price = 1000 + 800 = 1800
    assert data["list_price"] == 1800
    # (а) price_overridden = false -> final_price пересчитывается
    assert data["price_overridden"] is False
    assert data["final_price"] == 1800

    # Свежее чтение через GET /api/appointments/{id}
    get_res = client.get(f"/api/appointments/{appt_id}")
    assert get_res.status_code == 200
    fresh = get_res.json()
    assert fresh["list_price"] == 1800
    assert fresh["final_price"] == 1800
    assert fresh["price_overridden"] is False
    assert len(fresh["services"]) == 2
    fresh_snap_a = next(s for s in fresh["services"] if s["service_id"] == svc_a["id"])
    fresh_snap_b = next(s for s in fresh["services"] if s["service_id"] == svc_b["id"])
    assert fresh_snap_a["price_snapshot"] == 1000
    assert fresh_snap_b["price_snapshot"] == 800

    # Проверка на уровне БД напрямую
    with psycopg.connect(sync_test_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT list_price, final_price, price_overridden FROM appointments WHERE id = %s",
                (appt_id,),
            )
            row = cur.fetchone()
            assert row == (1800, 1800, False)

            cur.execute(
                "SELECT service_id, price_snapshot FROM appointment_services "
                "WHERE appointment_id = %s ORDER BY position",
                (appt_id,),
            )
            svc_rows = cur.fetchall()
            assert svc_rows == [(svc_a["id"], 1000), (svc_b["id"], 800)]


def test_final_price_and_price_overridden(client: TestClient, test_user):
    _login(client, test_user)
    svc = _create_service(client, price=1500, duration=60)
    _create_work_window(client, "2024-06-15")
    cl = _create_client_via_api(client)

    # Without final_price: price_overridden=false, final_price=list_price
    res1 = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-06-15T10:00:00",
            "service_ids": [svc["id"]],
        },
    )
    assert res1.status_code == 201
    d1 = res1.json()
    assert d1["price_overridden"] is False
    assert d1["final_price"] == d1["list_price"]

    # With different final_price: price_overridden=true
    cl2 = _create_client_via_api(client, name="Клиент 2", phone="79009998877")
    res2 = client.post(
        "/api/appointments",
        json={
            "client_id": cl2["id"],
            "starts_at": "2024-06-15T13:00:00",
            "service_ids": [svc["id"]],
            "final_price": 1000,
        },
    )
    assert res2.status_code == 201
    d2 = res2.json()
    assert d2["price_overridden"] is True
    assert d2["final_price"] == 1000
    assert d2["list_price"] == 1500


def test_reset_price(client: TestClient, test_user):
    _login(client, test_user)
    svc = _create_service(client, price=1500, duration=60)
    _create_work_window(client, "2024-06-15")
    cl = _create_client_via_api(client)

    # Create with custom final_price
    res = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-06-15T10:00:00",
            "service_ids": [svc["id"]],
            "final_price": 500,
        },
    )
    assert res.status_code == 201
    appt_id = res.json()["id"]

    # PATCH with reset_price=true
    patch_res = client.patch(
        f"/api/appointments/{appt_id}",
        json={"reset_price": True},
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["price_overridden"] is False
    assert data["final_price"] == 1500


def test_ends_at_computed(client: TestClient, test_user):
    _login(client, test_user)
    svc = _create_service(client, duration=60)
    _create_work_window(client, "2024-06-15")
    cl = _create_client_via_api(client)

    res = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-06-15T10:00:00",
            "service_ids": [svc["id"]],
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["local_end_time"] == "11:00:00"


def test_outside_work_window_warning(client: TestClient, test_user):
    _login(client, test_user)
    svc = _create_service(client, duration=60)
    # Create a work window that doesn't cover appointment time
    _create_work_window(client, "2024-06-15", "13:00:00", "18:00:00")
    cl = _create_client_via_api(client)

    # Appointment at 10:00–11:00, outside work window (13:00–18:00)
    res = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-06-15T10:00:00",
            "service_ids": [svc["id"]],
            "force": False,
        },
    )
    assert res.status_code == 409
    detail = res.json()["detail"]
    assert detail["code"] == "needs_confirmation"
    assert "outside_work_window" in detail["warnings"]

    # With force=True: succeeds, warnings in response
    res2 = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-06-15T10:00:00",
            "service_ids": [svc["id"]],
            "force": True,
        },
    )
    assert res2.status_code == 201
    data = res2.json()
    assert "outside_work_window" in data["warnings"]


def test_overlap_warning(client: TestClient, test_user):
    _login(client, test_user)
    svc = _create_service(client, duration=60)
    _create_work_window(client, "2024-06-15")
    cl = _create_client_via_api(client)

    # Create first appointment
    res1 = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-06-15T10:00:00",
            "service_ids": [svc["id"]],
        },
    )
    assert res1.status_code == 201
    first_id = res1.json()["id"]

    # Second appointment overlapping with the first
    cl2 = _create_client_via_api(client, name="Клиент 2", phone="79009998877")
    res2 = client.post(
        "/api/appointments",
        json={
            "client_id": cl2["id"],
            "starts_at": "2024-06-15T10:30:00",  # overlaps 10:00–11:00
            "service_ids": [svc["id"]],
            "force": False,
        },
    )
    assert res2.status_code == 409
    detail = res2.json()["detail"]
    assert detail["code"] == "needs_confirmation"
    assert "overlaps_existing" in detail["warnings"]
    assert first_id in detail["overlapping_ids"]


def test_midnight_boundary_local_date(client: TestClient, test_user):
    _login(client, test_user)
    svc = _create_service(client, duration=60)
    # 2024-06-16 01:30 Moscow = 2024-06-15 22:30 UTC
    _create_work_window(client, "2024-06-16", "01:00:00", "03:00:00")
    cl = _create_client_via_api(client)

    # Pass UTC-aware datetime
    res = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-06-15T22:30:00+00:00",
            "service_ids": [svc["id"]],
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["local_date"] == "2024-06-16"
    assert data["local_start_time"] == "01:30:00"


def test_inline_client_create(client: TestClient, test_user):
    _login(client, test_user)
    svc = _create_service(client, duration=60)
    _create_work_window(client, "2024-06-15")

    res = client.post(
        "/api/appointments",
        json={
            "client": {"name": "Новый Клиент", "phone": "79111234567"},
            "starts_at": "2024-06-15T10:00:00",
            "service_ids": [svc["id"]],
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["client"]["name"] == "Новый Клиент"
    assert data["client"]["phone"] == "79111234567"

    # Verify client was actually created in DB
    clients_res = client.get("/api/clients")
    assert any(c["phone"] == "79111234567" for c in clients_res.json()["items"])


def test_inline_client_find_existing(client: TestClient, test_user):
    _login(client, test_user)
    svc = _create_service(client, duration=60)
    _create_work_window(client, "2024-06-15")

    # Pre-create a client
    existing_cl = _create_client_via_api(client, name="Существующий", phone="79222333444")
    existing_id = existing_cl["id"]

    # Create appointment with same phone via inline client
    res = client.post(
        "/api/appointments",
        json={
            "client": {"name": "Другое Имя", "phone": "79222333444"},
            "starts_at": "2024-06-15T10:00:00",
            "service_ids": [svc["id"]],
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    # Should link to existing client
    assert data["client"]["id"] == existing_id
    assert data["client"]["name"] == "Существующий"


def test_soft_delete(client: TestClient, test_user):
    _login(client, test_user)
    svc = _create_service(client, duration=60)
    _create_work_window(client, "2024-06-15")
    cl = _create_client_via_api(client)

    res = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-06-15T10:00:00",
            "service_ids": [svc["id"]],
        },
    )
    assert res.status_code == 201
    appt_id = res.json()["id"]

    del_res = client.delete(f"/api/appointments/{appt_id}")
    assert del_res.status_code == 200
    assert del_res.json() == {"status": "ok"}

    get_res = client.get(f"/api/appointments/{appt_id}")
    assert get_res.status_code == 404


def test_patch_service_ids_add_new_service(client: TestClient, test_user):
    """PATCH appt with [A, B] where B is new: A keeps old snapshot, B gets current price.
    Сценарий (б): price_overridden = true, final_price остаётся прежним."""
    _login(client, test_user)

    svc_a = _create_service(client, name="Услуга А", price=1000, duration=30)
    svc_b = _create_service(client, name="Услуга Б", price=800, duration=30)
    _create_work_window(client, "2024-06-15")
    cl = _create_client_via_api(client)

    # Create appointment with A only and custom final_price (ручная цена: price_overridden = true)
    res = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-06-15T10:00:00",
            "service_ids": [svc_a["id"]],
            "final_price": 600,
        },
    )
    assert res.status_code == 201
    appt_id = res.json()["id"]
    old_snap_a_price = res.json()["services"][0]["price_snapshot"]
    assert res.json()["price_overridden"] is True
    assert res.json()["final_price"] == 600
    assert res.json()["list_price"] == 1000

    # Update A's price in the catalog
    client.patch(f"/api/services/{svc_a['id']}", json={"price": 5000})

    # PATCH with [A, B]
    patch_res = client.patch(
        f"/api/appointments/{appt_id}",
        json={"service_ids": [svc_a["id"], svc_b["id"]]},
    )
    assert patch_res.status_code == 200, patch_res.text
    data = patch_res.json()

    snap_a = next(s for s in data["services"] if s["service_id"] == svc_a["id"])
    snap_b = next(s for s in data["services"] if s["service_id"] == svc_b["id"])

    assert snap_a["price_snapshot"] == old_snap_a_price  # 1000, not 5000
    assert snap_b["price_snapshot"] == 800  # current price of B
    assert data["list_price"] == 1800  # 1000 + 800
    # (б) price_overridden = true -> final_price остаётся прежним (600)
    assert data["price_overridden"] is True
    assert data["final_price"] == 600

    # Свежее чтение через GET /api/appointments/{id}
    get_res = client.get(f"/api/appointments/{appt_id}")
    assert get_res.status_code == 200
    fresh = get_res.json()
    assert fresh["list_price"] == 1800
    assert fresh["final_price"] == 600
    assert fresh["price_overridden"] is True
    assert len(fresh["services"]) == 2
    fresh_snap_a = next(s for s in fresh["services"] if s["service_id"] == svc_a["id"])
    fresh_snap_b = next(s for s in fresh["services"] if s["service_id"] == svc_b["id"])
    assert fresh_snap_a["price_snapshot"] == 1000
    assert fresh_snap_b["price_snapshot"] == 800

    # Проверка на уровне БД напрямую
    with psycopg.connect(sync_test_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT list_price, final_price, price_overridden FROM appointments WHERE id = %s",
                (appt_id,),
            )
            row = cur.fetchone()
            assert row == (1800, 600, True)

            cur.execute(
                "SELECT service_id, price_snapshot FROM appointment_services "
                "WHERE appointment_id = %s ORDER BY position",
                (appt_id,),
            )
            svc_rows = cur.fetchall()
            assert svc_rows == [(svc_a["id"], 1000), (svc_b["id"], 800)]


def test_patch_ends_at_recalculation_cases(client: TestClient, test_user):
    _login(client, test_user)
    svc_1 = _create_service(client, name="Услуга 1", price=1000, duration=30)
    svc_2 = _create_service(client, name="Услуга 2", price=1500, duration=45)
    _create_work_window(client, "2024-06-15", "08:00:00", "20:00:00")
    cl = _create_client_via_api(client)

    # Создаём исходную запись: starts_at = 10:00, svc_1 (30 минут) -> ends_at = 10:30
    res = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-06-15T10:00:00",
            "service_ids": [svc_1["id"]],
        },
    )
    assert res.status_code == 201
    appt_id = res.json()["id"]
    assert res.json()["local_end_time"] == "10:30:00"

    # Случай 1: PATCH с service_ids без ends_at ->
    # пересчёт ends_at = starts_at + сумма duration (30 + 45 = 75 мин -> 11:15)
    p1 = client.patch(
        f"/api/appointments/{appt_id}",
        json={"service_ids": [svc_1["id"], svc_2["id"]]},
    )
    assert p1.status_code == 200, p1.text
    assert p1.json()["local_end_time"] == "11:15:00"

    # Случай 2: PATCH со starts_at без ends_at -> пересчёт ends_at = 12:00 + 75 мин = 13:15
    p2 = client.patch(
        f"/api/appointments/{appt_id}",
        json={"starts_at": "2024-06-15T12:00:00"},
    )
    assert p2.status_code == 200, p2.text
    assert p2.json()["local_start_time"] == "12:00:00"
    assert p2.json()["local_end_time"] == "13:15:00"

    # Случай 3: PATCH с явным ends_at -> используется именно он
    p3 = client.patch(
        f"/api/appointments/{appt_id}",
        json={"ends_at": "2024-06-15T14:30:00"},
    )
    assert p3.status_code == 200, p3.text
    assert p3.json()["local_end_time"] == "14:30:00"

    # Случай 4: ни одно из трёх полей не передано (например, обновление note) -> ends_at не трогаем
    p4 = client.patch(
        f"/api/appointments/{appt_id}",
        json={"note": "Обновлённая заметка"},
    )
    assert p4.status_code == 200, p4.text
    assert p4.json()["note"] == "Обновлённая заметка"
    assert p4.json()["local_end_time"] == "14:30:00"


def test_work_window_midnight_boundary_warning(client: TestClient, test_user):
    _login(client, test_user)
    svc = _create_service(client, duration=60)
    # Рабочие окна на оба дня: конец 15 июня и начало 16 июня
    _create_work_window(client, "2024-06-15", "20:00:00", "23:59:59")
    _create_work_window(client, "2024-06-16", "00:00:00", "04:00:00")
    cl = _create_client_via_api(client)

    # Запись 23:30 - 00:30 (через полночь): локальная дата конца (16 июня) != дата начала (15 июня)
    res = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-06-15T23:30:00",
            "service_ids": [svc["id"]],
            "force": False,
        },
    )
    assert res.status_code == 409
    detail = res.json()["detail"]
    assert detail["code"] == "needs_confirmation"
    assert "outside_work_window" in detail["warnings"]

    # С force=True запись создаётся, но предупреждение возвращается
    res_forced = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-06-15T23:30:00",
            "service_ids": [svc["id"]],
            "force": True,
        },
    )
    assert res_forced.status_code == 201
    assert "outside_work_window" in res_forced.json()["warnings"]


def test_advisory_lock_called_on_create_and_update(client: TestClient, test_user):
    from unittest.mock import patch

    from app.services.appointments import APPOINTMENT_LOCK_KEY, func

    _login(client, test_user)
    svc = _create_service(client, duration=30)
    _create_work_window(client, "2024-06-15", "09:00:00", "18:00:00")
    cl = _create_client_via_api(client)

    with patch(
        "app.services.appointments.func.pg_advisory_xact_lock",
        wraps=func.pg_advisory_xact_lock,
    ) as mock_lock:
        res = client.post(
            "/api/appointments",
            json={
                "client_id": cl["id"],
                "starts_at": "2024-06-15T09:00:00",
                "service_ids": [svc["id"]],
            },
        )
        assert res.status_code == 201
        mock_lock.assert_called_with(APPOINTMENT_LOCK_KEY)

        appt_id = res.json()["id"]
        mock_lock.reset_mock()

        patch_res = client.patch(
            f"/api/appointments/{appt_id}",
            json={"note": "Тест блокировки"},
        )
        assert patch_res.status_code == 200
        mock_lock.assert_called_with(APPOINTMENT_LOCK_KEY)


def test_duplicate_service_ids_double_price_and_duration(client: TestClient, test_user):
    _login(client, test_user)
    svc = _create_service(client, name="Наращивание ногтя", price=2000, duration=45)
    _create_work_window(client, "2024-06-15", "09:00:00", "18:00:00")
    cl = _create_client_via_api(client)

    res = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-06-15T10:00:00",
            "service_ids": [svc["id"], svc["id"]],
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()

    # Двойная цена (2000 * 2 = 4000)
    assert data["list_price"] == 4000
    assert data["final_price"] == 4000
    assert data["price_overridden"] is False

    # Двойная длительность (45 * 2 = 90 мин): с 10:00 до 11:30
    assert data["local_start_time"] == "10:00:00"
    assert data["local_end_time"] == "11:30:00"

    assert len(data["services"]) == 2
    assert data["services"][0]["service_id"] == svc["id"]
    assert data["services"][1]["service_id"] == svc["id"]
    assert data["services"][0]["price_snapshot"] == 2000
    assert data["services"][1]["price_snapshot"] == 2000


def test_create_completed_appointment_in_past(client: TestClient, test_user):
    """Creating completed appointment in past succeeds and computes prices/snapshots."""
    _login(client, test_user)
    svc = _create_service(client, name="Педикюр", price=2500, duration=90)
    cl = _create_client_via_api(client)

    res = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-05-10T11:00:00",
            "service_ids": [svc["id"]],
            "status": "completed",
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["status"] == "completed"
    assert data["list_price"] == 2500
    assert data["final_price"] == 2500
    assert data["price_overridden"] is False
    assert len(data["services"]) == 1
    assert data["services"][0]["name_snapshot"] == "Педикюр"
    assert data["services"][0]["price_snapshot"] == 2500
    assert data["services"][0]["duration_snapshot"] == 90
    assert data["local_date"] == "2024-05-10"
    assert data["local_start_time"] == "11:00:00"
    assert data["local_end_time"] == "12:30:00"


def test_create_non_scheduled_appointment_in_future_forbidden(client: TestClient, test_user):
    """Creating completed or no_show appointment in future returns 422; cancelled is allowed."""
    _login(client, test_user)
    svc = _create_service(client, price=1000, duration=60)
    cl = _create_client_via_api(client)

    future_dt = (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S")

    for forbidden_status in ["completed", "no_show"]:
        res = client.post(
            "/api/appointments",
            json={
                "client_id": cl["id"],
                "starts_at": future_dt,
                "service_ids": [svc["id"]],
                "status": forbidden_status,
            },
        )
        assert res.status_code == 422, f"Expected 422 for {forbidden_status}, got {res.status_code}"
        assert "Статусы 'completed' и 'no_show' запрещены для записей в будущем" in res.text

    res_cancelled = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": future_dt,
            "service_ids": [svc["id"]],
            "status": "cancelled",
        },
    )
    assert res_cancelled.status_code == 201
    assert res_cancelled.json()["status"] == "cancelled"


def test_completed_appointment_past_outside_work_window_no_warning(client: TestClient, test_user):
    """Work window check is skipped for completed status (no warning, no 409)."""
    _login(client, test_user)
    svc = _create_service(client, duration=60)
    # Work window is 14:00-18:00
    _create_work_window(client, "2024-05-12", "14:00:00", "18:00:00")
    cl = _create_client_via_api(client)

    # Appt at 10:00 is outside window, but status=completed -> should succeed with 201
    res = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-05-12T10:00:00",
            "service_ids": [svc["id"]],
            "status": "completed",
            "force": False,
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["status"] == "completed"
    assert "outside_work_window" not in data["warnings"]


def test_scheduled_appointment_outside_work_window_warning(client: TestClient, test_user):
    """Work window check is performed for scheduled status (409 needs_confirmation)."""
    _login(client, test_user)
    svc = _create_service(client, duration=60)
    _create_work_window(client, "2024-05-12", "14:00:00", "18:00:00")
    cl = _create_client_via_api(client)

    # Explicit status=scheduled
    res = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-05-12T10:00:00",
            "service_ids": [svc["id"]],
            "status": "scheduled",
            "force": False,
        },
    )
    assert res.status_code == 409
    detail = res.json()["detail"]
    assert detail["code"] == "needs_confirmation"
    assert "outside_work_window" in detail["warnings"]


def test_cancelled_appointment_ignores_overlap(client: TestClient, test_user):
    """Cancelled status does not perform overlap check."""
    _login(client, test_user)
    svc = _create_service(client, duration=60)
    cl = _create_client_via_api(client)

    # First appointment 10:00-11:00 completed
    res1 = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-05-14T10:00:00",
            "service_ids": [svc["id"]],
            "status": "completed",
            "force": False,
        },
    )
    assert res1.status_code == 201

    # Second appointment 10:30-11:30 with status=cancelled does not warn on overlap
    res2 = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-05-14T10:30:00",
            "service_ids": [svc["id"]],
            "status": "cancelled",
            "force": False,
        },
    )
    assert res2.status_code == 201, res2.text
    assert "overlaps_existing" not in res2.json()["warnings"]


def test_completed_appointment_checks_overlap(client: TestClient, test_user):
    """Completed status DOES perform overlap check."""
    _login(client, test_user)
    svc = _create_service(client, duration=60)
    cl = _create_client_via_api(client)

    # First appointment 10:00-11:00 completed
    res1 = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-05-15T10:00:00",
            "service_ids": [svc["id"]],
            "status": "completed",
            "force": False,
        },
    )
    assert res1.status_code == 201

    # Overlapping completed appointment -> 409
    res2 = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-05-15T10:30:00",
            "service_ids": [svc["id"]],
            "status": "completed",
            "force": False,
        },
    )
    assert res2.status_code == 409
    detail = res2.json()["detail"]
    assert detail["code"] == "needs_confirmation"
    assert "overlaps_existing" in detail["warnings"]


def test_patch_uncancel_to_scheduled_on_occupied_slot_requires_force(client: TestClient, test_user):
    """Uncancelling an appointment on an occupied slot returns 409, passes with force=True."""
    _login(client, test_user)
    svc = _create_service(client, duration=60)
    cl = _create_client_via_api(client)
    _create_work_window(client, "2024-05-18", "10:00:00", "18:00:00")

    # Appt 1: scheduled 10:00-11:00
    res1 = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-05-18T10:00:00",
            "service_ids": [svc["id"]],
            "status": "scheduled",
        },
    )
    assert res1.status_code == 201

    # Appt 2: cancelled 10:00-11:00 (cancelled ignores overlap)
    res2 = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-05-18T10:00:00",
            "service_ids": [svc["id"]],
            "status": "cancelled",
        },
    )
    assert res2.status_code == 201
    appt2_id = res2.json()["id"]

    # PATCH Appt 2 to scheduled without force -> 409 needs_confirmation
    patch_res = client.patch(
        f"/api/appointments/{appt2_id}",
        json={"status": "scheduled"},
    )
    assert patch_res.status_code == 409
    detail = patch_res.json()["detail"]
    assert detail["code"] == "needs_confirmation"
    assert "overlaps_existing" in detail["warnings"]

    # PATCH Appt 2 to scheduled with force=True -> 200
    force_res = client.patch(
        f"/api/appointments/{appt2_id}",
        json={"status": "scheduled", "force": True},
    )
    assert force_res.status_code == 200
    assert force_res.json()["status"] == "scheduled"


def test_patch_scheduled_to_completed_past_appointment_no_warnings(client: TestClient, test_user):
    """scheduled -> completed for past appointment returns 200 without warnings."""
    _login(client, test_user)
    svc = _create_service(client, duration=60)
    cl = _create_client_via_api(client)

    # Past appointment outside work window (no window created)
    # Created with force=True as scheduled
    res = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-05-19T10:00:00",
            "service_ids": [svc["id"]],
            "status": "scheduled",
            "force": True,
        },
    )
    assert res.status_code == 201
    appt_id = res.json()["id"]

    # Change status to completed without force: should succeed with 200 (no warnings run)
    patch_res = client.patch(
        f"/api/appointments/{appt_id}",
        json={"status": "completed"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "completed"


def test_patch_future_appointment_to_completed_returns_422(client: TestClient, test_user):
    """Setting status to completed for future appointment returns 422."""
    _login(client, test_user)
    svc = _create_service(client, duration=60)
    cl = _create_client_via_api(client)

    future_dt = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")
    res = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": future_dt,
            "service_ids": [svc["id"]],
            "status": "scheduled",
            "force": True,
        },
    )
    assert res.status_code == 201
    appt_id = res.json()["id"]

    # PATCH to completed -> 422
    patch_res = client.patch(
        f"/api/appointments/{appt_id}",
        json={"status": "completed"},
    )
    assert patch_res.status_code == 422
    assert "Статусы 'completed' и 'no_show' запрещены для записей в будущем" in patch_res.text


def test_patch_future_appointment_to_cancelled_returns_200(client: TestClient, test_user):
    """Setting status to cancelled for future appointment returns 200."""
    _login(client, test_user)
    svc = _create_service(client, duration=60)
    cl = _create_client_via_api(client)

    future_dt = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S")
    res = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": future_dt,
            "service_ids": [svc["id"]],
            "status": "scheduled",
            "force": True,
        },
    )
    assert res.status_code == 201
    appt_id = res.json()["id"]

    # PATCH to cancelled -> 200
    patch_res = client.patch(
        f"/api/appointments/{appt_id}",
        json={"status": "cancelled"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "cancelled"


def test_patch_reschedule_completed_appointment_to_future_returns_422(
    client: TestClient, test_user
):
    """Rescheduling a completed appointment to a future date returns 422."""
    _login(client, test_user)
    svc = _create_service(client, duration=60)
    cl = _create_client_via_api(client)

    res = client.post(
        "/api/appointments",
        json={
            "client_id": cl["id"],
            "starts_at": "2024-05-20T10:00:00",
            "service_ids": [svc["id"]],
            "status": "completed",
            "force": True,
        },
    )
    assert res.status_code == 201
    appt_id = res.json()["id"]

    future_dt = (datetime.now(timezone.utc) + timedelta(days=4)).strftime("%Y-%m-%dT%H:%M:%S")
    # Reschedule only (starts_at), without changing status
    patch_res = client.patch(
        f"/api/appointments/{appt_id}",
        json={"starts_at": future_dt},
    )
    assert patch_res.status_code == 422
    assert "Статусы 'completed' и 'no_show' запрещены для записей в будущем" in patch_res.text



