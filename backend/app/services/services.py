from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service import Service
from app.schemas.service import ServiceCreate, ServiceUpdate


async def list_services(db: AsyncSession, include_archived: bool = False) -> Sequence[Service]:
    stmt = select(Service)
    if not include_archived:
        stmt = stmt.where(Service.is_active.is_(True))
    stmt = stmt.order_by(Service.sort_order.asc(), Service.id.asc())
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_service(db: AsyncSession, service_id: int) -> Service | None:
    result = await db.execute(select(Service).where(Service.id == service_id))
    return result.scalar_one_or_none()


async def create_service(db: AsyncSession, data: ServiceCreate) -> Service:
    service = Service(
        name=data.name,
        price=data.price,
        duration_minutes=data.duration_minutes,
        sort_order=data.sort_order,
        is_active=data.is_active,
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service


async def update_service(
    db: AsyncSession, service_id: int, data: ServiceUpdate
) -> Service | None:
    service = await get_service(db, service_id)
    if not service:
        return None

    if data.name is not None:
        service.name = data.name
    if data.price is not None:
        service.price = data.price
    if data.duration_minutes is not None:
        service.duration_minutes = data.duration_minutes
    if data.sort_order is not None:
        service.sort_order = data.sort_order
    if data.is_active is not None:
        service.is_active = data.is_active

    await db.commit()
    await db.refresh(service)
    return service
