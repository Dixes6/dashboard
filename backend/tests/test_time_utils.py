"""Unit tests for pure functions in app.core.time_utils (no DB needed)."""
import zoneinfo
from datetime import date, datetime, time, timezone

from app.core.time_utils import (
    appointment_fits_in_windows,
    check_appointment_overlap,
    check_work_window_overlap,
    compute_ends_at,
    from_utc,
    local_date_of,
    local_time_of,
    to_utc,
)

MOSCOW_TZ = "Europe/Moscow"


def test_to_utc_naive():
    """Naive Moscow datetime (UTC+3) should be converted to UTC by subtracting 3 hours."""
    naive = datetime(2024, 6, 15, 12, 0, 0)
    result = to_utc(naive, MOSCOW_TZ)
    assert result.tzinfo == timezone.utc
    assert result == datetime(2024, 6, 15, 9, 0, 0, tzinfo=timezone.utc)


def test_to_utc_aware():
    """Aware datetime should be converted to UTC correctly."""
    tz = zoneinfo.ZoneInfo(MOSCOW_TZ)
    aware = datetime(2024, 6, 15, 12, 0, 0, tzinfo=tz)
    result = to_utc(aware, MOSCOW_TZ)
    assert result.tzinfo == timezone.utc
    assert result == datetime(2024, 6, 15, 9, 0, 0, tzinfo=timezone.utc)


def test_to_utc_already_utc():
    """UTC aware datetime should remain unchanged."""
    utc_dt = datetime(2024, 6, 15, 9, 0, 0, tzinfo=timezone.utc)
    result = to_utc(utc_dt, MOSCOW_TZ)
    assert result == utc_dt


def test_local_date_midnight_boundary():
    """UTC 21:00 on Jan 15 is Moscow midnight Jan 16 (UTC+3)."""
    utc_dt = datetime(2024, 1, 15, 21, 0, 0, tzinfo=timezone.utc)
    result = local_date_of(utc_dt, MOSCOW_TZ)
    assert result == date(2024, 1, 16)


def test_local_date_same_day():
    """UTC 10:00 is Moscow 13:00, same day."""
    utc_dt = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
    result = local_date_of(utc_dt, MOSCOW_TZ)
    assert result == date(2024, 6, 15)


def test_local_time_of():
    """UTC 09:00 → Moscow 12:00."""
    utc_dt = datetime(2024, 6, 15, 9, 0, 0, tzinfo=timezone.utc)
    result = local_time_of(utc_dt, MOSCOW_TZ)
    assert result == time(12, 0, 0)


def test_from_utc():
    """from_utc converts UTC to Moscow time."""
    utc_dt = datetime(2024, 6, 15, 9, 0, 0, tzinfo=timezone.utc)
    result = from_utc(utc_dt, MOSCOW_TZ)
    assert result.hour == 12
    assert result.date() == date(2024, 6, 15)


def test_compute_ends_at():
    """compute_ends_at adds duration in minutes."""
    starts = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
    result = compute_ends_at(starts, 90)
    assert result == datetime(2024, 6, 15, 11, 30, 0, tzinfo=timezone.utc)


def test_appointment_fits_in_windows_true():
    """10:00–11:00 fits in window 09:00–18:00."""
    windows = [(time(9, 0), time(18, 0))]
    assert appointment_fits_in_windows(time(10, 0), time(11, 0), windows) is True


def test_appointment_fits_in_windows_false():
    """08:00–10:00 doesn't fit in window 09:00–18:00 (starts before window)."""
    windows = [(time(9, 0), time(18, 0))]
    assert appointment_fits_in_windows(time(8, 0), time(10, 0), windows) is False


def test_appointment_fits_exact_window():
    """09:00–18:00 exactly matches window 09:00–18:00."""
    windows = [(time(9, 0), time(18, 0))]
    assert appointment_fits_in_windows(time(9, 0), time(18, 0), windows) is True


def test_appointment_fits_in_chained_windows():
    """10:00–14:00 fits in union of [09:00–12:00] + [12:00–16:00]."""
    windows = [(time(9, 0), time(12, 0)), (time(12, 0), time(16, 0))]
    assert appointment_fits_in_windows(time(10, 0), time(14, 0), windows) is True


def test_appointment_does_not_fit_gap():
    """10:00–14:00 does NOT fit in [09:00–12:00] and [13:00–16:00] with gap."""
    windows = [(time(9, 0), time(12, 0)), (time(13, 0), time(16, 0))]
    assert appointment_fits_in_windows(time(10, 0), time(14, 0), windows) is False


def test_appointment_fits_no_windows():
    """No windows → always False."""
    assert appointment_fits_in_windows(time(10, 0), time(11, 0), []) is False


def test_appointment_overlap():
    """Two overlapping UTC datetime pairs → returns index 0."""
    starts = datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc)
    ends = datetime(2024, 6, 15, 11, 0, tzinfo=timezone.utc)
    existing = [
        (datetime(2024, 6, 15, 10, 30, tzinfo=timezone.utc),
         datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc)),
    ]
    result = check_appointment_overlap(starts, ends, existing)
    assert result == [0]


def test_appointment_no_overlap():
    """Non-overlapping appointments → empty list."""
    starts = datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc)
    ends = datetime(2024, 6, 15, 11, 0, tzinfo=timezone.utc)
    existing = [
        (datetime(2024, 6, 15, 11, 0, tzinfo=timezone.utc),
         datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc)),
    ]
    result = check_appointment_overlap(starts, ends, existing)
    assert result == []


def test_appointment_adjacent_no_overlap():
    """Adjacent appointments (end == start of next) don't overlap."""
    starts = datetime(2024, 6, 15, 11, 0, tzinfo=timezone.utc)
    ends = datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc)
    existing = [
        (datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc),
         datetime(2024, 6, 15, 11, 0, tzinfo=timezone.utc)),
    ]
    result = check_appointment_overlap(starts, ends, existing)
    assert result == []


def test_work_window_overlap_true():
    """10:00–14:00 overlaps with existing 12:00–16:00."""
    existing = [(time(12, 0), time(16, 0))]
    assert check_work_window_overlap(time(10, 0), time(14, 0), existing) is True


def test_work_window_overlap_false():
    """10:00–12:00 does NOT overlap with 12:00–14:00 (adjacent)."""
    existing = [(time(12, 0), time(14, 0))]
    assert check_work_window_overlap(time(10, 0), time(12, 0), existing) is False


def test_work_window_overlap_no_existing():
    """No existing windows → no overlap."""
    assert check_work_window_overlap(time(10, 0), time(12, 0), []) is False
