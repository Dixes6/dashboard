import zoneinfo
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.settings import get_or_create_settings
from app.services.stats import parse_month_and_range


async def get_finance_entries(
    db: AsyncSession,
    entry_type: str,
    month_str: str | None = None,
) -> dict[str, Any]:
    if entry_type not in ("income", "expense"):
        raise ValueError("Параметр type должен быть 'income' или 'expense'")

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

    if entry_type == "income":
        stmt = text(
            """
            WITH visit_entries AS (
                SELECT
                    'visit' AS kind,
                    (timezone(:tz_name, a.starts_at))::date AS date,
                    a.final_price::bigint AS amount,
                    CASE
                        WHEN string_agg(aps.name_snapshot, ', ' ORDER BY aps.position) IS NOT NULL
                             AND string_agg(aps.name_snapshot, ', ' ORDER BY aps.position) <> ''
                        THEN c.name || ', ' ||
                             string_agg(aps.name_snapshot, ', ' ORDER BY aps.position)
                        ELSE c.name
                    END AS label,
                    a.id AS ref_id,
                    a.starts_at AS sort_ts
                FROM appointments a
                JOIN clients c ON a.client_id = c.id
                LEFT JOIN appointment_services aps ON a.id = aps.appointment_id
                WHERE a.deleted_at IS NULL
                  AND a.status = 'completed'
                  AND a.starts_at >= :month_start_utc
                  AND a.starts_at < :next_month_start_utc
                GROUP BY a.id, c.name, a.starts_at, a.final_price
            ),
            manual_entries AS (
                SELECT
                    'manual' AS kind,
                    occurred_on AS date,
                    amount::bigint AS amount,
                    source AS label,
                    id AS ref_id,
                    created_at AS sort_ts
                FROM income_entries
                WHERE deleted_at IS NULL
                  AND occurred_on >= :start_date
                  AND occurred_on < :next_month_date
            ),
            all_entries AS (
                SELECT kind, date, amount, label, ref_id, sort_ts FROM visit_entries
                UNION ALL
                SELECT kind, date, amount, label, ref_id, sort_ts FROM manual_entries
            )
            SELECT kind, date, amount, label, ref_id
            FROM all_entries
            ORDER BY date DESC, sort_ts DESC, ref_id DESC
            """
        )
        params = {
            "tz_name": tz_name,
            "month_start_utc": month_start_utc,
            "next_month_start_utc": next_month_start_utc,
            "start_date": start_date,
            "next_month_date": next_month_date,
        }
    else:
        stmt = text(
            """
            SELECT
                'manual' AS kind,
                occurred_on AS date,
                amount::bigint AS amount,
                description AS label,
                id AS ref_id
            FROM expense_entries
            WHERE deleted_at IS NULL
              AND occurred_on >= :start_date
              AND occurred_on < :next_month_date
            ORDER BY occurred_on DESC, created_at DESC, id DESC
            """
        )
        params = {
            "start_date": start_date,
            "next_month_date": next_month_date,
        }

    result = await db.execute(stmt, params)
    rows = result.all()

    total = sum(int(r.amount) for r in rows)
    items = [
        {
            "kind": r.kind,
            "date": r.date,
            "amount": int(r.amount),
            "label": r.label,
            "ref_id": int(r.ref_id),
        }
        for r in rows
    ]

    return {
        "month": norm_month_str,
        "type": entry_type,
        "total": total,
        "items": items,
        "entries": items,
    }
