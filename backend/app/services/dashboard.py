import calendar
import collections
from datetime import date, datetime, timezone
from typing import Any
import zoneinfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time_utils import local_date_of
from app.models.appointment import Appointment, AppointmentStatus
from app.models.income import IncomeEntry
from app.models.work_window import WorkWindow
from app.services.appointments import list_appointments
from app.services.settings import get_or_create_settings
from app.services.work_windows import list_work_windows


async def get_calendar_month(db: AsyncSession, month_str: str) -> list[dict[str, Any]]:
    parts = month_str.split("-")
    if len(parts) != 2:
        raise ValueError("Параметр month должен быть в формате YYYY-MM")
    try:
        year, month = int(parts[0]), int(parts[1])
        if not (1 <= month <= 12):
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError("Параметр month должен быть в формате YYYY-MM")

    num_days = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date = date(year, month, num_days)

    settings_obj = await get_or_create_settings(db)
    tz_name = settings_obj.timezone
    tz = zoneinfo.ZoneInfo(tz_name)

    month_start_local = datetime(year, month, 1, 0, 0, 0, tzinfo=tz)
    month_end_local = datetime(year, month, num_days, 23, 59, 59, 999999, tzinfo=tz)
    month_start_utc = month_start_local.astimezone(timezone.utc)
    month_end_utc = month_end_local.astimezone(timezone.utc)

    # 1. Рабочие окна за месяц
    ww_stmt = (
        select(WorkWindow.date)
        .where(WorkWindow.date >= start_date, WorkWindow.date <= end_date)
        .distinct()
    )
    ww_result = await db.execute(ww_stmt)
    days_with_windows = set(ww_result.scalars().all())

    # 2. Записи за месяц (только scheduled и completed, не удалённые)
    appt_stmt = (
        select(Appointment.starts_at, Appointment.status, Appointment.final_price)
        .where(
            Appointment.starts_at >= month_start_utc,
            Appointment.starts_at <= month_end_utc,
            Appointment.deleted_at.is_(None),
            Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.COMPLETED]),
        )
    )
    appt_result = await db.execute(appt_stmt)

    counts: dict[date, int] = collections.defaultdict(int)
    incomes: dict[date, int] = collections.defaultdict(int)
    for starts_at, status, final_price in appt_result.all():
        d = local_date_of(starts_at, tz_name)
        if start_date <= d <= end_date:
            counts[d] += 1
            if status == AppointmentStatus.COMPLETED:
                incomes[d] += final_price

    results: list[dict[str, Any]] = []
    for day in range(1, num_days + 1):
        d = date(year, month, day)
        results.append(
            {
                "date": d,
                "has_work_window": d in days_with_windows,
                "appointments_count": counts.get(d, 0),
                "completed_income": incomes.get(d, 0),
            }
        )

    return results


async def get_day_details(db: AsyncSession, day_date: date) -> dict[str, Any]:
    # 1. Окна дня
    windows = await list_work_windows(db, date_from=day_date, date_to=day_date)

    # 2. Записи дня (в том же формате, что и в /api/appointments)
    appointments = await list_appointments(db, date_filter=day_date)

    # 3. Доходы от визитов
    visits_income = sum(
        a["final_price"] for a in appointments if a["status"] == AppointmentStatus.COMPLETED
    )
    expected_income = sum(
        a["final_price"] for a in appointments if a["status"] == AppointmentStatus.SCHEDULED
    )

    # 4. Прочие доходы за этот день
    stmt = select(func.coalesce(func.sum(IncomeEntry.amount), 0)).where(
        IncomeEntry.occurred_on == day_date,
        IncomeEntry.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    other_income = int(result.scalar_one() or 0)

    total_income = visits_income + other_income

    return {
        "work_windows": windows,
        "appointments": appointments,
        "visits_income": visits_income,
        "expected_income": expected_income,
        "other_income": other_income,
        "total_income": total_income,
    }
