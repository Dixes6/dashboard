from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time_utils import check_work_window_overlap
from app.models.work_window import WorkWindow
from app.schemas.work_window import WorkWindowBulkCreate, WorkWindowCreate, WorkWindowUpdate


async def list_work_windows(
    db: AsyncSession,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[WorkWindow]:
    stmt = select(WorkWindow)
    if date_from is not None:
        stmt = stmt.where(WorkWindow.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(WorkWindow.date <= date_to)
    stmt = stmt.order_by(WorkWindow.date.asc(), WorkWindow.start_time.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_work_window(db: AsyncSession, window_id: int) -> WorkWindow | None:
    result = await db.execute(select(WorkWindow).where(WorkWindow.id == window_id))
    return result.scalar_one_or_none()


async def _get_windows_for_date(
    db: AsyncSession, target_date: date, exclude_id: int | None = None
) -> list[WorkWindow]:
    stmt = select(WorkWindow).where(WorkWindow.date == target_date)
    if exclude_id is not None:
        stmt = stmt.where(WorkWindow.id != exclude_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_work_window(db: AsyncSession, data: WorkWindowCreate) -> WorkWindow:
    existing = await _get_windows_for_date(db, data.date)
    existing_pairs = [(w.start_time, w.end_time) for w in existing]

    if check_work_window_overlap(data.start_time, data.end_time, existing_pairs):
        raise ValueError("Рабочее окно пересекается с существующим на эту дату")

    window = WorkWindow(
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    db.add(window)
    await db.commit()
    await db.refresh(window)
    return window


async def bulk_create_work_windows(
    db: AsyncSession, data: WorkWindowBulkCreate
) -> list[WorkWindow]:
    created: list[WorkWindow] = []

    for target_date in data.dates:
        existing = await _get_windows_for_date(db, target_date)
        existing_pairs = [(w.start_time, w.end_time) for w in existing]

        if check_work_window_overlap(data.start_time, data.end_time, existing_pairs):
            await db.rollback()
            raise ValueError(
                f"Рабочее окно пересекается с существующим на дату {target_date}"
            )

        window = WorkWindow(
            date=target_date,
            start_time=data.start_time,
            end_time=data.end_time,
        )
        db.add(window)
        created.append(window)

    await db.commit()
    for window in created:
        await db.refresh(window)

    return created


async def update_work_window(
    db: AsyncSession, window_id: int, data: WorkWindowUpdate
) -> WorkWindow | None:
    window = await get_work_window(db, window_id)
    if not window:
        return None

    new_date = data.date if data.date is not None else window.date
    new_start = data.start_time if data.start_time is not None else window.start_time
    new_end = data.end_time if data.end_time is not None else window.end_time

    if new_end <= new_start:
        raise ValueError("end_time должен быть позже start_time")

    existing = await _get_windows_for_date(db, new_date, exclude_id=window_id)
    existing_pairs = [(w.start_time, w.end_time) for w in existing]

    if check_work_window_overlap(new_start, new_end, existing_pairs):
        raise ValueError("Рабочее окно пересекается с существующим на эту дату")

    window.date = new_date
    window.start_time = new_start
    window.end_time = new_end

    await db.commit()
    await db.refresh(window)
    return window


async def delete_work_window(db: AsyncSession, window_id: int) -> bool:
    window = await get_work_window(db, window_id)
    if not window:
        return False

    await db.delete(window)
    await db.commit()
    return True
