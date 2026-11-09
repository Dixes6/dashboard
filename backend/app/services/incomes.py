from collections.abc import Sequence
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.income import IncomeEntry
from app.schemas.financial import IncomeCreate, IncomeUpdate


async def list_incomes(
    db: AsyncSession,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Sequence[IncomeEntry]:
    stmt = select(IncomeEntry).where(IncomeEntry.deleted_at.is_(None))

    if date_from:
        stmt = stmt.where(IncomeEntry.occurred_on >= date_from)
    if date_to:
        stmt = stmt.where(IncomeEntry.occurred_on <= date_to)

    stmt = stmt.order_by(IncomeEntry.occurred_on.desc(), IncomeEntry.id.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_income(db: AsyncSession, income_id: int) -> IncomeEntry | None:
    stmt = select(IncomeEntry).where(
        IncomeEntry.id == income_id,
        IncomeEntry.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_income(db: AsyncSession, data: IncomeCreate) -> IncomeEntry:
    income = IncomeEntry(
        amount=data.amount,
        source=data.source,
        occurred_on=data.occurred_on,
    )
    db.add(income)
    await db.commit()
    await db.refresh(income)
    return income


async def update_income(
    db: AsyncSession, income_id: int, data: IncomeUpdate
) -> IncomeEntry | None:
    income = await get_income(db, income_id)
    if not income:
        return None

    if data.amount is not None:
        income.amount = data.amount
    if data.source is not None:
        income.source = data.source
    if data.occurred_on is not None:
        income.occurred_on = data.occurred_on

    await db.commit()
    await db.refresh(income)
    return income


async def delete_income(db: AsyncSession, income_id: int) -> bool:
    income = await get_income(db, income_id)
    if not income:
        return False

    income.deleted_at = func.now()
    await db.commit()
    return True
