import zoneinfo
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.phone import normalize_phone
from app.core.time_utils import (
    appointment_fits_in_windows,
    check_appointment_overlap,
    compute_ends_at,
    local_date_of,
    local_time_of,
    to_utc,
)
from app.models.appointment import Appointment, AppointmentSource, AppointmentStatus
from app.models.appointment_service import AppointmentService
from app.models.client import Client
from app.models.service import Service
from app.models.work_window import WorkWindow
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate
from app.services.settings import get_or_create_settings


class NeedsConfirmationError(Exception):
    def __init__(self, warnings: list[str], overlapping_ids: list[int] | None = None):
        self.warnings = warnings
        self.overlapping_ids = overlapping_ids or []
        super().__init__(str(warnings))


def _build_appointment_dict(
    appointment: Appointment,
    tz_name: str,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    client = appointment.client
    services = sorted(appointment.appointment_services, key=lambda s: s.position)

    return {
        "id": appointment.id,
        "client": {
            "id": client.id,
            "name": client.name,
            "phone": client.phone,
        },
        "starts_at": appointment.starts_at,
        "ends_at": appointment.ends_at,
        "local_date": local_date_of(appointment.starts_at, tz_name),
        "local_start_time": local_time_of(appointment.starts_at, tz_name),
        "local_end_time": local_time_of(appointment.ends_at, tz_name),
        "status": appointment.status,
        "source": appointment.source,
        "note": appointment.note,
        "list_price": appointment.list_price,
        "final_price": appointment.final_price,
        "price_overridden": appointment.price_overridden,
        "services": [
            {
                "service_id": s.service_id,
                "name_snapshot": s.name_snapshot,
                "price_snapshot": s.price_snapshot,
                "duration_snapshot": s.duration_snapshot,
                "position": s.position,
            }
            for s in services
        ],
        "warnings": warnings or [],
        "created_at": appointment.created_at,
        "updated_at": appointment.updated_at,
    }


async def _load_appointment(db: AsyncSession, appointment_id: int) -> Appointment | None:
    stmt = (
        select(Appointment)
        .options(
            selectinload(Appointment.client),
            selectinload(Appointment.appointment_services),
        )
        .where(Appointment.id == appointment_id, Appointment.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _resolve_client(
    db: AsyncSession,
    client_id: int | None,
    inline_client: Any,
) -> Client:
    if client_id is not None:
        stmt = select(Client).where(Client.id == client_id, Client.deleted_at.is_(None))
        result = await db.execute(stmt)
        client = result.scalar_one_or_none()
        if not client:
            raise ValueError(f"Клиент с id={client_id} не найден")
        return client

    # Inline client
    try:
        normalized_phone = normalize_phone(inline_client.phone)
    except ValueError as e:
        raise ValueError(f"Некорректный номер телефона: {e}") from e

    stmt = select(Client).where(
        Client.phone == normalized_phone,
        Client.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    new_client = Client(name=inline_client.name, phone=normalized_phone)
    db.add(new_client)
    await db.flush()
    return new_client


async def _load_services_ordered(
    db: AsyncSession, service_ids: list[int]
) -> list[Service]:
    if not service_ids:
        raise ValueError("Необходимо указать хотя бы одну услугу")

    unique_ids = list(dict.fromkeys(service_ids))
    stmt = select(Service).where(Service.id.in_(unique_ids))
    result = await db.execute(stmt)
    services_map = {s.id: s for s in result.scalars().all()}

    ordered: list[Service] = []
    for sid in service_ids:
        svc = services_map.get(sid)
        if svc is None:
            raise ValueError(f"Услуга с id={sid} не найдена")
        if not svc.is_active:
            raise ValueError(f"Услуга '{svc.name}' (id={sid}) неактивна")
        ordered.append(svc)

    return ordered


async def _run_warnings(
    db: AsyncSession,
    starts_at_utc: datetime,
    ends_at_utc: datetime,
    tz_name: str,
    exclude_appointment_id: int | None = None,
) -> tuple[list[str], list[int]]:
    warnings: list[str] = []
    overlapping_ids: list[int] = []

    local_dt_date = local_date_of(starts_at_utc, tz_name)
    local_start = local_time_of(starts_at_utc, tz_name)
    local_end = local_time_of(ends_at_utc, tz_name)

    ww_stmt = select(WorkWindow).where(WorkWindow.date == local_dt_date)
    ww_result = await db.execute(ww_stmt)
    windows = [(w.start_time, w.end_time) for w in ww_result.scalars().all()]

    if not appointment_fits_in_windows(local_start, local_end, windows):
        warnings.append("outside_work_window")

    appt_stmt = select(Appointment).where(
        Appointment.deleted_at.is_(None),
        Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.COMPLETED]),
    )
    if exclude_appointment_id is not None:
        appt_stmt = appt_stmt.where(Appointment.id != exclude_appointment_id)
    appt_result = await db.execute(appt_stmt)
    existing_appts = list(appt_result.scalars().all())

    existing_pairs = [(a.starts_at, a.ends_at) for a in existing_appts]
    overlap_indices = check_appointment_overlap(starts_at_utc, ends_at_utc, existing_pairs)

    if overlap_indices:
        warnings.append("overlaps_existing")
        overlapping_ids = [existing_appts[i].id for i in overlap_indices]

    return warnings, overlapping_ids


async def create_appointment(
    db: AsyncSession, data: AppointmentCreate
) -> dict[str, Any]:
    settings_obj = await get_or_create_settings(db)
    tz_name = settings_obj.timezone

    client = await _resolve_client(db, data.client_id, data.client)
    services = await _load_services_ordered(db, data.service_ids)

    starts_at_utc = to_utc(data.starts_at, tz_name)
    total_duration = sum(s.duration_minutes for s in services)

    if data.ends_at is not None:
        ends_at_utc = to_utc(data.ends_at, tz_name)
    else:
        ends_at_utc = compute_ends_at(starts_at_utc, total_duration)

    list_price = sum(s.price for s in services)

    if data.final_price is not None:
        final_price = data.final_price
        price_overridden = final_price != list_price
    else:
        final_price = list_price
        price_overridden = False

    warnings, overlapping_ids = await _run_warnings(db, starts_at_utc, ends_at_utc, tz_name)

    if warnings and not data.force:
        raise NeedsConfirmationError(warnings, overlapping_ids)

    appointment = Appointment(
        client_id=client.id,
        starts_at=starts_at_utc,
        ends_at=ends_at_utc,
        status=AppointmentStatus.SCHEDULED,
        source=AppointmentSource.MANUAL,
        note=data.note,
        list_price=list_price,
        final_price=final_price,
        price_overridden=price_overridden,
    )
    db.add(appointment)
    await db.flush()

    for position, svc in enumerate(services):
        appt_svc = AppointmentService(
            appointment_id=appointment.id,
            service_id=svc.id,
            name_snapshot=svc.name,
            price_snapshot=svc.price,
            duration_snapshot=svc.duration_minutes,
            position=position,
        )
        db.add(appt_svc)

    await db.commit()

    loaded = await _load_appointment(db, appointment.id)
    return _build_appointment_dict(loaded, tz_name, warnings)


async def get_appointment(db: AsyncSession, appointment_id: int) -> dict[str, Any] | None:
    appointment = await _load_appointment(db, appointment_id)
    if not appointment:
        return None

    settings_obj = await get_or_create_settings(db)
    return _build_appointment_dict(appointment, settings_obj.timezone)


async def list_appointments(
    db: AsyncSession,
    date_filter: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    status: AppointmentStatus | None = None,
    client_id: int | None = None,
) -> list[dict[str, Any]]:
    settings_obj = await get_or_create_settings(db)
    tz_name = settings_obj.timezone
    tz = zoneinfo.ZoneInfo(tz_name)

    stmt = (
        select(Appointment)
        .options(
            selectinload(Appointment.client),
            selectinload(Appointment.appointment_services),
        )
        .where(Appointment.deleted_at.is_(None))
        .order_by(Appointment.starts_at.asc())
    )

    if date_filter is not None:
        local_start = datetime(
            date_filter.year, date_filter.month, date_filter.day, 0, 0, 0, tzinfo=tz
        )
        local_end = datetime(
            date_filter.year, date_filter.month, date_filter.day, 23, 59, 59, 999999, tzinfo=tz
        )
        utc_start = local_start.astimezone(timezone.utc)
        utc_end = local_end.astimezone(timezone.utc)
        stmt = stmt.where(
            Appointment.starts_at >= utc_start, Appointment.starts_at <= utc_end
        )
    else:
        if date_from is not None:
            local_start = datetime(
                date_from.year, date_from.month, date_from.day, 0, 0, 0, tzinfo=tz
            )
            utc_start = local_start.astimezone(timezone.utc)
            stmt = stmt.where(Appointment.starts_at >= utc_start)
        if date_to is not None:
            local_end = datetime(
                date_to.year, date_to.month, date_to.day, 23, 59, 59, 999999, tzinfo=tz
            )
            utc_end = local_end.astimezone(timezone.utc)
            stmt = stmt.where(Appointment.starts_at <= utc_end)

    if status is not None:
        stmt = stmt.where(Appointment.status == status)

    if client_id is not None:
        stmt = stmt.where(Appointment.client_id == client_id)

    result = await db.execute(stmt)
    appointments = list(result.scalars().all())

    return [_build_appointment_dict(a, tz_name) for a in appointments]


async def update_appointment(
    db: AsyncSession,
    appointment_id: int,
    data: AppointmentUpdate,
) -> dict[str, Any] | None:
    appointment = await _load_appointment(db, appointment_id)
    if not appointment:
        return None

    settings_obj = await get_or_create_settings(db)
    tz_name = settings_obj.timezone

    if data.client_id is not None:
        stmt = select(Client).where(
            Client.id == data.client_id, Client.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        client = result.scalar_one_or_none()
        if not client:
            raise ValueError(f"Клиент с id={data.client_id} не найден")
        appointment.client_id = data.client_id

    if data.note is not None:
        appointment.note = data.note

    if data.status is not None:
        appointment.status = data.status

    if data.service_ids is not None:
        existing_svcs = {s.service_id: s for s in appointment.appointment_services}

        unique_ids = list(dict.fromkeys(data.service_ids))
        stmt = select(Service).where(Service.id.in_(unique_ids))
        result = await db.execute(stmt)
        services_map = {s.id: s for s in result.scalars().all()}

        new_snapshots: list[dict] = []
        for position, sid in enumerate(data.service_ids):
            svc = services_map.get(sid)
            if svc is None:
                raise ValueError(f"Услуга с id={sid} не найдена")
            if not svc.is_active:
                raise ValueError(f"Услуга '{svc.name}' (id={sid}) неактивна")

            if sid in existing_svcs:
                old = existing_svcs[sid]
                new_snapshots.append({
                    "service_id": sid,
                    "name_snapshot": old.name_snapshot,
                    "price_snapshot": old.price_snapshot,
                    "duration_snapshot": old.duration_snapshot,
                    "position": position,
                })
            else:
                new_snapshots.append({
                    "service_id": sid,
                    "name_snapshot": svc.name,
                    "price_snapshot": svc.price,
                    "duration_snapshot": svc.duration_minutes,
                    "position": position,
                })

        for old_svc in list(appointment.appointment_services):
            await db.delete(old_svc)
        await db.flush()

        for snap in new_snapshots:
            appt_svc = AppointmentService(
                appointment_id=appointment.id,
                **snap,
            )
            db.add(appt_svc)
        await db.flush()

        new_list_price = sum(s["price_snapshot"] for s in new_snapshots)
        appointment.list_price = new_list_price

        if data.reset_price:
            appointment.final_price = new_list_price
            appointment.price_overridden = False
        elif data.final_price is not None:
            appointment.final_price = data.final_price
            appointment.price_overridden = data.final_price != new_list_price
        elif not appointment.price_overridden:
            appointment.final_price = new_list_price
    else:
        if data.reset_price:
            appointment.final_price = appointment.list_price
            appointment.price_overridden = False
        elif data.final_price is not None:
            appointment.final_price = data.final_price
            appointment.price_overridden = data.final_price != appointment.list_price

    if data.starts_at is not None:
        appointment.starts_at = to_utc(data.starts_at, tz_name)

    if data.ends_at is not None:
        appointment.ends_at = to_utc(data.ends_at, tz_name)

    warnings: list[str] = []
    overlapping_ids: list[int] = []
    if data.starts_at is not None or data.service_ids is not None:
        warnings, overlapping_ids = await _run_warnings(
            db,
            appointment.starts_at,
            appointment.ends_at,
            tz_name,
            exclude_appointment_id=appointment_id,
        )
        if warnings and not data.force:
            raise NeedsConfirmationError(warnings, overlapping_ids)

    await db.commit()

    loaded = await _load_appointment(db, appointment_id)
    return _build_appointment_dict(loaded, tz_name, warnings)


async def delete_appointment(db: AsyncSession, appointment_id: int) -> bool:
    stmt = select(Appointment).where(
        Appointment.id == appointment_id, Appointment.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    appointment = result.scalar_one_or_none()
    if not appointment:
        return False

    appointment.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return True
