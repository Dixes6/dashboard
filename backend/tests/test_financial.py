from datetime import date
from fastapi.testclient import TestClient
import psycopg

from tests.conftest import sync_test_url


def _login(client: TestClient, test_user):
    res = client.post(
        "/api/auth/login",
        json={"login": "owner", "password": "correct_password"},
    )
    assert res.status_code == 200


def test_incomes_and_expenses_unauthorized(client: TestClient):
    client.cookies.clear()
    assert client.get("/api/incomes").status_code == 401
    assert client.get("/api/expenses").status_code == 401


def test_incomes_crud_and_date_filtering(client: TestClient, test_user):
    _login(client, test_user)

    # 1. Создаём несколько доходов
    res1 = client.post(
        "/api/incomes",
        json={"amount": 1000, "source": "Чаевые", "occurred_on": "2026-11-01"},
    )
    assert res1.status_code == 201
    inc1 = res1.json()

    res2 = client.post(
        "/api/incomes",
        json={"amount": 2500, "source": "Продажа масла для кутикулы", "occurred_on": "2026-11-05"},
    )
    assert res2.status_code == 201
    inc2 = res2.json()

    res3 = client.post(
        "/api/incomes",
        json={"amount": 1500, "source": "Обучение", "occurred_on": "2026-11-10"},
    )
    assert res3.status_code == 201
    inc3 = res3.json()

    # GET без фильтров: сортировка по occurred_on по убыванию
    list_res = client.get("/api/incomes")
    assert list_res.status_code == 200
    incomes = list_res.json()
    assert len(incomes) == 3
    assert [i["id"] for i in incomes] == [inc3["id"], inc2["id"], inc1["id"]]

    # Фильтры date_from и date_to
    filter_res = client.get("/api/incomes?date_from=2026-11-02&date_to=2026-11-08")
    assert filter_res.status_code == 200
    filtered = filter_res.json()
    assert len(filtered) == 1
    assert filtered[0]["id"] == inc2["id"]

    # PATCH
    patch_res = client.patch(
        f"/api/incomes/{inc1['id']}",
        json={"amount": 1200, "source": "Щедрые чаевые"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["amount"] == 1200
    assert patch_res.json()["source"] == "Щедрые чаевые"

    # DELETE (мягкое)
    del_res = client.delete(f"/api/incomes/{inc1['id']}")
    assert del_res.status_code == 200

    # Проверяем, что в списке не отображается
    after_del = client.get("/api/incomes").json()
    assert inc1["id"] not in [i["id"] for i in after_del]

    # Физически в БД осталась с deleted_at
    with psycopg.connect(sync_test_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT deleted_at FROM income_entries WHERE id = %s", (inc1["id"],))
            assert cur.fetchone()[0] is not None


def test_expenses_crud_and_validation(client: TestClient, test_user):
    _login(client, test_user)

    # Валидация: amount > 0, description не пустое
    bad_res1 = client.post(
        "/api/expenses",
        json={"amount": 0, "description": "Пилки", "occurred_on": "2026-11-01"},
    )
    assert bad_res1.status_code == 422

    bad_res2 = client.post(
        "/api/expenses",
        json={"amount": 500, "description": "   ", "occurred_on": "2026-11-01"},
    )
    assert bad_res2.status_code == 422

    # Создание корректного расхода
    res = client.post(
        "/api/expenses",
        json={"amount": 3500, "description": "Гель-лаки и базы", "occurred_on": "2026-11-03"},
    )
    assert res.status_code == 201
    expense_id = res.json()["id"]

    # PATCH
    patch_res = client.patch(
        f"/api/expenses/{expense_id}",
        json={"amount": 3700},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["amount"] == 3700

    # DELETE (мягкое)
    del_res = client.delete(f"/api/expenses/{expense_id}")
    assert del_res.status_code == 200

    assert len(client.get("/api/expenses").json()) == 0
