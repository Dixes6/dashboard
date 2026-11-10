import zoneinfo
from collections.abc import Sequence
from datetime import date, datetime, time, timedelta, timezone
from typing import Any


def to_utc(dt: datetime, tz_name: str) -> datetime:
    """
    Convert naive datetime to UTC using given timezone name.
    If dt is already timezone-aware, convert it to UTC.
    """
    tz = zoneinfo.ZoneInfo(tz_name)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(timezone.utc)


def from_utc(dt: datetime, tz_name: str) -> datetime:
    """Convert UTC-aware datetime to local timezone-aware datetime."""
    tz = zoneinfo.ZoneInfo(tz_name)
    return dt.astimezone(tz)


def local_date_of(utc_dt: datetime, tz_name: str) -> date:
    """Get local date from UTC datetime."""
    return from_utc(utc_dt, tz_name).date()


def local_time_of(utc_dt: datetime, tz_name: str) -> time:
    """Get local time from UTC datetime."""
    return from_utc(utc_dt, tz_name).time()


def compute_ends_at(starts_at_utc: datetime, total_duration_minutes: int) -> datetime:
    """Add total_duration_minutes to starts_at_utc."""
    return starts_at_utc + timedelta(minutes=total_duration_minutes)


def check_work_window_overlap(
    new_start: time,
    new_end: time,
    existing_windows: list[tuple[time, time]],
    exclude_id: int | None = None,
    existing_ids: list[int] | None = None,
) -> bool:
    """
    Return True if new_start..new_end overlaps any of existing_windows.
    Two intervals overlap if one starts before the other ends (exclusive boundaries allowed).
    """
    for idx, (ws, we) in enumerate(existing_windows):
        if exclude_id is not None and existing_ids is not None:
            if idx < len(existing_ids) and existing_ids[idx] == exclude_id:
                continue
        # Overlap: new_start < we AND new_end > ws
        if new_start < we and new_end > ws:
            return True
    return False


def appointment_fits_in_windows(
    local_start: Any,
    local_end: Any,
    windows: Sequence[tuple[Any, Any]],
) -> bool:
    """Return True if the appointment's local range fits entirely within

    at least one continuous chain of work windows.
    Supports either (time, time) or (datetime, datetime) tuples.
    """
    if not windows:
        return False

    sorted_w = sorted(windows, key=lambda x: x[0])

    covered_until = None
    started = False

    for ws, we in sorted_w:
        if not started and ws <= local_start:
            covered_until = we
            started = True
        elif started:
            if covered_until is not None and ws <= covered_until:
                covered_until = max(covered_until, we)
            else:
                break

    return started and covered_until is not None and covered_until >= local_end


def check_appointment_overlap(
    starts_at: datetime,
    ends_at: datetime,
    existing_appointments: list[tuple[datetime, datetime]],
) -> list[int]:
    """
    Return indices of existing_appointments that overlap with [starts_at, ends_at).
    Two appointments overlap if starts_at < other.ends_at AND ends_at > other.starts_at.
    """
    overlapping = []
    for idx, (other_start, other_end) in enumerate(existing_appointments):
        if starts_at < other_end and ends_at > other_start:
            overlapping.append(idx)
    return overlapping
