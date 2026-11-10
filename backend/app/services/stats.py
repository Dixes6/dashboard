import zoneinfo
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.settings import get_or_create_settings


def parse_month_and_range(
    month_str: str | None, tz: zoneinfo.ZoneInfo
) -> tuple[int, int, str, date, date, datetime, datetime]:
    if month_str is None:
        now_local = datetime.now(tz)
        year, month = now_local.year, now_local.month
        norm_month_str = f"{year:04d}-{month:02d}"
    else:
        parts = month_str.split("-")
        if len(parts) != 2:
            raise ValueError("Параметр month должен быть в формате YYYY-MM")
        try:
            year, month = int(parts[0]), int(parts[1])
            if not (1 <= month <= 12):
                raise ValueError()
            norm_month_str = f"{year:04d}-{month:02d}"
        except (ValueError, TypeError):
            raise ValueError("Параметр month должен быть в формате YYYY-MM") from None

    start_date = date(year, month, 1)
    if month == 12:
        next_month_date = date(year + 1, 1, 1)
        next_month_local = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=tz)
    else:
        next_month_date = date(year, month + 1, 1)
        next_month_local = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=tz)

    month_start_local = datetime(year, month, 1, 0, 0, 0, tzinfo=tz)
    month_start_utc = month_start_local.astimezone(timezone.utc)
    next_month_start_utc = next_month_local.astimezone(timezone.utc)

    return (
        year,
        month,
        norm_month_str,
        start_date,
        next_month_date,
        month_start_utc,
        next_month_start_utc,
    )


async def get_month_stats(
    db: AsyncSession, month_str: str | None = None
) -> dict[str, Any]:
    settings_obj = await get_or_create_settings(db)
    tz_name = settings_obj.timezone
    tz = zoneinfo.ZoneInfo(tz_name)

    (
        _year,
        _month,
        norm_month_str,
        start_date,
        next_month_date,
        month_start_utc,
        next_month_start_utc,
    ) = parse_month_and_range(month_str, tz)

    # 1. Записи (визиты) за месяц
    visits_stmt = text(
        """
        SELECT
            COALESCE(SUM(final_price), 0)::bigint AS visits_income,
            COUNT(id)::bigint AS completed_visits_count,
            COUNT(DISTINCT (timezone(:tz_name, starts_at))::date)::bigint AS active_days_count
        FROM appointments
        WHERE deleted_at IS NULL
          AND status = 'completed'
          AND starts_at >= :month_start_utc
          AND starts_at < :next_month_start_utc
        """
    )
    v_res = await db.execute(
        visits_stmt,
        {
            "tz_name": tz_name,
            "month_start_utc": month_start_utc,
            "next_month_start_utc": next_month_start_utc,
        },
    )
    v_row = v_res.one()
    visits_income = int(v_row.visits_income)
    completed_visits_count = int(v_row.completed_visits_count)
    active_days_count = int(v_row.active_days_count)

    # 2. Прочие доходы за месяц
    income_stmt = text(
        """
        SELECT COALESCE(SUM(amount), 0)::bigint AS other_income
        FROM income_entries
        WHERE deleted_at IS NULL
          AND occurred_on >= :start_date
          AND occurred_on < :next_month_date
        """
    )
    i_res = await db.execute(
        income_stmt,
        {"start_date": start_date, "next_month_date": next_month_date},
    )
    other_income = int(i_res.scalar_one())

    income_total = visits_income + other_income

    # 3. Расходы за месяц
    expense_stmt = text(
        """
        SELECT COALESCE(SUM(amount), 0)::bigint AS expenses_total
        FROM expense_entries
        WHERE deleted_at IS NULL
          AND occurred_on >= :start_date
          AND occurred_on < :next_month_date
        """
    )
    e_res = await db.execute(
        expense_stmt,
        {"start_date": start_date, "next_month_date": next_month_date},
    )
    expenses_total = int(e_res.scalar_one())
    net_profit_month = income_total - expenses_total

    # 4. Чистая прибыль текущей недели (только если запрошен текущий месяц, иначе null)
    current_month_str = datetime.now(tz).strftime("%Y-%m")
    if norm_month_str != current_month_str:
        net_profit_week = None
    else:
        today_local = datetime.now(tz).date()
        week_monday = today_local - timedelta(days=today_local.weekday())
        next_week_monday = week_monday + timedelta(days=7)
        week_start_local = datetime(
            week_monday.year, week_monday.month, week_monday.day, 0, 0, 0, tzinfo=tz
        )
        next_week_start_local = datetime(
            next_week_monday.year,
            next_week_monday.month,
            next_week_monday.day,
            0,
            0,
            0,
            tzinfo=tz,
        )
        week_start_utc = week_start_local.astimezone(timezone.utc)
        week_end_utc = next_week_start_local.astimezone(timezone.utc)

        week_stmt = text(
            """
            SELECT
                (SELECT COALESCE(SUM(final_price), 0)::bigint
                 FROM appointments
                 WHERE deleted_at IS NULL
                   AND status = 'completed'
                   AND starts_at >= :week_start_utc
                   AND starts_at < :week_end_utc) AS week_visits_income,
                (SELECT COALESCE(SUM(amount), 0)::bigint
                 FROM income_entries
                 WHERE deleted_at IS NULL
                   AND occurred_on >= :week_monday
                   AND occurred_on < :next_week_monday) AS week_other_income,
                (SELECT COALESCE(SUM(amount), 0)::bigint
                 FROM expense_entries
                 WHERE deleted_at IS NULL
                   AND occurred_on >= :week_monday
                   AND occurred_on < :next_week_monday) AS week_expenses
            """
        )
        w_res = await db.execute(
            week_stmt,
            {
                "week_start_utc": week_start_utc,
                "week_end_utc": week_end_utc,
                "week_monday": week_monday,
                "next_week_monday": next_week_monday,
            },
        )
        w_row = w_res.one()
        week_income = int(w_row.week_visits_income) + int(w_row.week_other_income)
        net_profit_week = week_income - int(w_row.week_expenses)

    # 5. Средний доход за день (visits_income / дни с визитами, округление вниз)
    if active_days_count > 0:
        avg_income_per_day = visits_income // active_days_count
    else:
        avg_income_per_day = None

    # 6. Популярная услуга (больше всего оказаний, при равенстве по выручке snapshot)
    top_svc_stmt = text(
        """
        SELECT
            s.name AS name,
            COUNT(aps.id)::bigint AS count,
            COALESCE(SUM(aps.price_snapshot), 0)::bigint AS revenue
        FROM appointment_services aps
        JOIN appointments a ON aps.appointment_id = a.id
        JOIN services s ON aps.service_id = s.id
        WHERE a.deleted_at IS NULL
          AND a.status = 'completed'
          AND a.starts_at >= :month_start_utc
          AND a.starts_at < :next_month_start_utc
        GROUP BY aps.service_id, s.name
        ORDER BY count DESC, revenue DESC, aps.service_id ASC
        LIMIT 1
        """
    )
    top_res = await db.execute(
        top_svc_stmt,
        {
            "month_start_utc": month_start_utc,
            "next_month_start_utc": next_month_start_utc,
        },
    )
    top_row = top_res.one_or_none()
    if top_row:
        top_service = {
            "name": top_row.name,
            "count": int(top_row.count),
            "revenue": int(top_row.revenue),
        }
    else:
        top_service = None

    # 7. Самый прибыльный день (максимум дохода: визиты + прочие доходы)
    best_day_stmt = text(
        """
        WITH daily_visits AS (
            SELECT
                (timezone(:tz_name, starts_at))::date AS day_date,
                SUM(final_price)::bigint AS day_income
            FROM appointments
            WHERE deleted_at IS NULL
              AND status = 'completed'
              AND starts_at >= :month_start_utc
              AND starts_at < :next_month_start_utc
            GROUP BY (timezone(:tz_name, starts_at))::date
        ),
        daily_other AS (
            SELECT
                occurred_on AS day_date,
                SUM(amount)::bigint AS day_income
            FROM income_entries
            WHERE deleted_at IS NULL
              AND occurred_on >= :start_date
              AND occurred_on < :next_month_date
            GROUP BY occurred_on
        ),
        combined AS (
            SELECT day_date, day_income FROM daily_visits
            UNION ALL
            SELECT day_date, day_income FROM daily_other
        ),
        daily_total AS (
            SELECT
                day_date,
                SUM(day_income)::bigint AS total_income
            FROM combined
            GROUP BY day_date
        )
        SELECT day_date, total_income
        FROM daily_total
        ORDER BY total_income DESC, day_date ASC
        LIMIT 1
        """
    )
    b_res = await db.execute(
        best_day_stmt,
        {
            "tz_name": tz_name,
            "month_start_utc": month_start_utc,
            "next_month_start_utc": next_month_start_utc,
            "start_date": start_date,
            "next_month_date": next_month_date,
        },
    )
    b_row = b_res.one_or_none()
    if b_row:
        best_day = {
            "date": b_row.day_date,
            "income": int(b_row.total_income),
        }
    else:
        best_day = None

    return {
        "visits_income": visits_income,
        "other_income": other_income,
        "income_total": income_total,
        "expenses_total": expenses_total,
        "net_profit_month": net_profit_month,
        "net_profit_week": net_profit_week,
        "avg_income_per_day": avg_income_per_day,
        "completed_visits_count": completed_visits_count,
        "top_service": top_service,
        "best_day": best_day,
    }


async def get_months_summary(db: AsyncSession) -> list[dict[str, Any]]:
    settings_obj = await get_or_create_settings(db)
    tz_name = settings_obj.timezone

    stmt = text(
        """
        WITH visit_months AS (
            SELECT
                to_char(timezone(:tz_name, starts_at), 'YYYY-MM') AS month_str,
                SUM(final_price)::bigint AS visits_income
            FROM appointments
            WHERE deleted_at IS NULL
              AND status = 'completed'
            GROUP BY to_char(timezone(:tz_name, starts_at), 'YYYY-MM')
        ),
        income_months AS (
            SELECT
                to_char(occurred_on, 'YYYY-MM') AS month_str,
                SUM(amount)::bigint AS other_income
            FROM income_entries
            WHERE deleted_at IS NULL
            GROUP BY to_char(occurred_on, 'YYYY-MM')
        ),
        expense_months AS (
            SELECT
                to_char(occurred_on, 'YYYY-MM') AS month_str,
                SUM(amount)::bigint AS expenses
            FROM expense_entries
            WHERE deleted_at IS NULL
            GROUP BY to_char(occurred_on, 'YYYY-MM')
        ),
        all_months AS (
            SELECT month_str FROM visit_months
            UNION
            SELECT month_str FROM income_months
            UNION
            SELECT month_str FROM expense_months
        )
        SELECT
            m.month_str AS month,
            (COALESCE(v.visits_income, 0) + COALESCE(i.other_income, 0))::bigint AS income_total,
            COALESCE(e.expenses, 0)::bigint AS expenses_total,
            (
                (COALESCE(v.visits_income, 0) + COALESCE(i.other_income, 0)) -
                COALESCE(e.expenses, 0)
            )::bigint AS net_profit
        FROM all_months m
        LEFT JOIN visit_months v ON m.month_str = v.month_str
        LEFT JOIN income_months i ON m.month_str = i.month_str
        LEFT JOIN expense_months e ON m.month_str = e.month_str
        ORDER BY m.month_str DESC
        """
    )
    result = await db.execute(stmt, {"tz_name": tz_name})
    rows = result.all()
    return [
        {
            "month": r.month,
            "income_total": int(r.income_total),
            "expenses_total": int(r.expenses_total),
            "net_profit": int(r.net_profit),
        }
        for r in rows
    ]
