"""Tests for work windows API."""

from fastapi.testclient import TestClient

from tests.conftest import _login


def test_ww_unauthorized(client: TestClient):
    client.cookies.clear()
    res = client.get("/api/work-windows")
    assert res.status_code == 401


def test_ww_create_and_list(client: TestClient, test_user):
    _login(client, test_user)

    res = client.post(
        "/api/work-windows",
        json={"date": "2024-06-15", "start_time": "09:00:00", "end_time": "18:00:00"},
    )
    assert res.status_code == 201
    created = res.json()
    assert created["date"] == "2024-06-15"
    assert created["start_time"] == "09:00:00"
    assert created["end_time"] == "18:00:00"
    assert "id" in created

    # List without filter
    list_res = client.get("/api/work-windows")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # List with date_from / date_to
    res2 = client.get("/api/work-windows?date_from=2024-06-15&date_to=2024-06-15")
    assert res2.status_code == 200
    assert len(res2.json()) == 1

    # Outside range
    res3 = client.get("/api/work-windows?date_from=2024-06-16&date_to=2024-06-16")
    assert res3.status_code == 200
    assert len(res3.json()) == 0


def test_ww_overlap_conflict(client: TestClient, test_user):
    _login(client, test_user)

    res1 = client.post(
        "/api/work-windows",
        json={"date": "2024-06-15", "start_time": "09:00:00", "end_time": "14:00:00"},
    )
    assert res1.status_code == 201

    # Overlapping window on the same date
    res2 = client.post(
        "/api/work-windows",
        json={"date": "2024-06-15", "start_time": "13:00:00", "end_time": "18:00:00"},
    )
    assert res2.status_code == 409


def test_ww_no_overlap_adjacent(client: TestClient, test_user):
    _login(client, test_user)

    res1 = client.post(
        "/api/work-windows",
        json={"date": "2024-06-15", "start_time": "09:00:00", "end_time": "13:00:00"},
    )
    assert res1.status_code == 201

    # Adjacent: starts exactly where the first one ends — no overlap
    res2 = client.post(
        "/api/work-windows",
        json={"date": "2024-06-15", "start_time": "13:00:00", "end_time": "18:00:00"},
    )
    assert res2.status_code == 201


def test_ww_bulk_create(client: TestClient, test_user):
    _login(client, test_user)

    res = client.post(
        "/api/work-windows/bulk",
        json={
            "dates": ["2024-06-16", "2024-06-17", "2024-06-18"],
            "start_time": "09:00:00",
            "end_time": "18:00:00",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert len(data) == 3
    dates = {item["date"] for item in data}
    assert dates == {"2024-06-16", "2024-06-17", "2024-06-18"}


def test_ww_bulk_create_multiple_windows(client: TestClient, test_user):
    """Bulk create work windows with multiple slots per day."""
    _login(client, test_user)

    res = client.post(
        "/api/work-windows/bulk",
        json={
            "dates": ["2024-07-01", "2024-07-02"],
            "windows": [
                {"start_time": "10:00:00", "end_time": "13:00:00"},
                {"start_time": "14:00:00", "end_time": "18:00:00"},
            ],
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert len(data) == 4

    day1 = [w for w in data if w["date"] == "2024-07-01"]
    assert len(day1) == 2
    assert day1[0]["start_time"] == "10:00:00"
    assert day1[0]["end_time"] == "13:00:00"
    assert day1[1]["start_time"] == "14:00:00"
    assert day1[1]["end_time"] == "18:00:00"


def test_ww_bulk_create_overlapping_windows_in_payload(client: TestClient, test_user):
    """Bulk create fails when windows within payload overlap each other."""
    _login(client, test_user)

    res = client.post(
        "/api/work-windows/bulk",
        json={
            "dates": ["2024-07-03"],
            "windows": [
                {"start_time": "10:00:00", "end_time": "14:00:00"},
                {"start_time": "13:00:00", "end_time": "17:00:00"},
            ],
        },
    )
    assert res.status_code == 422


def test_ww_bulk_create_conflicts_with_existing(client: TestClient, test_user):
    """Bulk create fails with 409 when a window overlaps with an existing window."""
    _login(client, test_user)

    create_res = client.post(
        "/api/work-windows",
        json={"date": "2024-07-04", "start_time": "11:00:00", "end_time": "15:00:00"},
    )
    assert create_res.status_code == 201

    res = client.post(
        "/api/work-windows/bulk",
        json={
            "dates": ["2024-07-04"],
            "windows": [
                {"start_time": "10:00:00", "end_time": "12:00:00"},
                {"start_time": "16:00:00", "end_time": "19:00:00"},
            ],
        },
    )
    assert res.status_code == 409


def test_ww_patch(client: TestClient, test_user):
    _login(client, test_user)

    create_res = client.post(
        "/api/work-windows",
        json={"date": "2024-06-15", "start_time": "09:00:00", "end_time": "18:00:00"},
    )
    assert create_res.status_code == 201
    window_id = create_res.json()["id"]

    patch_res = client.patch(
        f"/api/work-windows/{window_id}",
        json={"start_time": "10:00:00"},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["start_time"] == "10:00:00"
    assert updated["end_time"] == "18:00:00"


def test_ww_patch_not_found(client: TestClient, test_user):
    _login(client, test_user)
    res = client.patch("/api/work-windows/9999", json={"start_time": "10:00:00"})
    assert res.status_code == 404


def test_ww_delete(client: TestClient, test_user):
    _login(client, test_user)

    create_res = client.post(
        "/api/work-windows",
        json={"date": "2024-06-15", "start_time": "09:00:00", "end_time": "18:00:00"},
    )
    assert create_res.status_code == 201
    window_id = create_res.json()["id"]

    del_res = client.delete(f"/api/work-windows/{window_id}")
    assert del_res.status_code == 204

    # After delete, list returns empty
    list_res = client.get("/api/work-windows")
    assert list_res.status_code == 200
    assert list_res.json() == []


def test_ww_delete_not_found(client: TestClient, test_user):
    _login(client, test_user)
    res = client.delete("/api/work-windows/9999")
    assert res.status_code == 404
