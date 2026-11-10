from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.phone import prepare_phone_prefix_search
from app.models.appointment import Appointment, AppointmentStatus
from app.models.client import Client
from app.schemas.client import ClientCreate, ClientUpdate


async def get_client_by_id(db: AsyncSession, client_id: int) -> Client | None:
    stmt = select(Client).where(Client.id == client_id, Client.deleted_at.is_(None))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_client_with_stats(db: AsyncSession, client_id: int) -> dict[str, Any] | None:
    stmt = (
        select(
            Client,
            func.coalesce(func.count(Appointment.id), 0).label("visits_count"),
            func.coalesce(func.sum(Appointment.final_price), 0).label("total_earned"),
        )
        .outerjoin(
            Appointment,
            (Appointment.client_id == Client.id)
            & (Appointment.status == AppointmentStatus.COMPLETED)
            & (Appointment.deleted_at.is_(None)),
        )
        .where(Client.id == client_id, Client.deleted_at.is_(None))
        .group_by(Client.id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        return None

    client, visits_count, total_earned = row
    return {
        "id": client.id,
        "name": client.name,
        "phone": client.phone,
        "notes": client.notes,
        "visits_count": int(visits_count),
        "total_earned": int(total_earned),
        "created_at": client.created_at,
        "updated_at": client.updated_at,
    }


async def list_clients_with_stats(
    db: AsyncSession,
    q: str | None = None,
    phone: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    base_where = [Client.deleted_at.is_(None)]

    if q and q.strip():
        base_where.append(Client.name.ilike(f"%{q.strip()}%"))

    if phone and phone.strip():
        phone_pattern = prepare_phone_prefix_search(phone.strip())
        base_where.append(Client.phone.like(phone_pattern))

    # Подсчёт общего количества
    count_stmt = select(func.count(Client.id)).where(*base_where)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one() or 0

    # Агрегированный запрос клиентов со статистикой
    stmt = (
        select(
            Client,
            func.coalesce(func.count(Appointment.id), 0).label("visits_count"),
            func.coalesce(func.sum(Appointment.final_price), 0).label("total_earned"),
        )
        .outerjoin(
            Appointment,
            (Appointment.client_id == Client.id)
            & (Appointment.status == AppointmentStatus.COMPLETED)
            & (Appointment.deleted_at.is_(None)),
        )
        .where(*base_where)
        .group_by(Client.id)
        .order_by(Client.name.asc(), Client.id.asc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(stmt)
    items = []
    for client, visits_count, total_earned in result.all():
        items.append(
            {
                "id": client.id,
                "name": client.name,
                "phone": client.phone,
                "notes": client.notes,
                "visits_count": int(visits_count),
                "total_earned": int(total_earned),
                "created_at": client.created_at,
                "updated_at": client.updated_at,
            }
        )

    return items, total


async def create_client(db: AsyncSession, data: ClientCreate) -> dict[str, Any]:
    # Проверка на дубликат среди не удалённых клиентов
    dup_stmt = select(Client.id).where(
        Client.phone == data.phone,
        Client.deleted_at.is_(None),
    )
    dup_result = await db.execute(dup_stmt)
    if dup_result.first():
        raise ValueError("Клиент с таким номером телефона уже существует")

    client = Client(
        name=data.name,
        phone=data.phone,
        notes=data.notes,
    )
    db.add(client)
    try:
        await db.commit()
        await db.refresh(client)
    except IntegrityError as exc:
        await db.rollback()
        raise ValueError("Клиент с таким номером телефона уже существует") from exc

    return {
        "id": client.id,
        "name": client.name,
        "phone": client.phone,
        "notes": client.notes,
        "visits_count": 0,
        "total_earned": 0,
        "created_at": client.created_at,
        "updated_at": client.updated_at,
    }


async def update_client(
    db: AsyncSession, client_id: int, data: ClientUpdate
) -> dict[str, Any] | None:
    client = await get_client_by_id(db, client_id)
    if not client:
        return None

    if data.phone is not None and data.phone != client.phone:
        # Проверяем, нет ли другого активного клиента с таким номером
        dup_stmt = select(Client.id).where(
            Client.phone == data.phone,
            Client.id != client_id,
            Client.deleted_at.is_(None),
        )
        dup_result = await db.execute(dup_stmt)
        if dup_result.first():
            raise ValueError("Клиент с таким номером телефона уже существует")
        client.phone = data.phone

    if data.name is not None:
        client.name = data.name
    if data.notes is not None:
        client.notes = data.notes

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ValueError("Клиент с таким номером телефона уже существует") from exc
    return await get_client_with_stats(db, client_id)


async def delete_client(db: AsyncSession, client_id: int) -> bool:
    client = await get_client_by_id(db, client_id)
    if not client:
        return False

    client.deleted_at = func.now()
    await db.commit()
    return True
