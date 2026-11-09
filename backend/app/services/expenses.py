from collections.abc import Sequence
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import ExpenseEntry
from app.schemas.financial import ExpenseCreate, ExpenseUpdate


async def list_expenses(
    db: AsyncSession,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Sequence[ExpenseEntry]:
    stmt = select(ExpenseEntry).where(ExpenseEntry.deleted_at.is_(None))

    if date_from:
        stmt = stmt.where(ExpenseEntry.occurred_on >= date_from)
    if date_to:
        stmt = stmt.where(ExpenseEntry.occurred_on <= date_to)

    stmt = stmt.order_by(ExpenseEntry.occurred_on.desc(), ExpenseEntry.id.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_expense(db: AsyncSession, expense_id: int) -> ExpenseEntry | None:
    stmt = select(ExpenseEntry).where(
        ExpenseEntry.id == expense_id,
        ExpenseEntry.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_expense(db: AsyncSession, data: ExpenseCreate) -> ExpenseEntry:
    expense = ExpenseEntry(
        amount=data.amount,
        description=data.description,
        occurred_on=data.occurred_on,
    )
    db.add(expense)
    await db.commit()
    await db.refresh(expense)
    return expense


async def update_expense(
    db: AsyncSession, expense_id: int, data: ExpenseUpdate
) -> ExpenseEntry | None:
    expense = await get_expense(db, expense_id)
    if not expense:
        return None

    if data.amount is not None:
        expense.amount = data.amount
    if data.description is not None:
        expense.description = data.description
    if data.occurred_on is not None:
        expense.occurred_on = data.occurred_on

    await db.commit()
    await db.refresh(expense)
    return expense


async def delete_expense(db: AsyncSession, expense_id: int) -> bool:
    expense = await get_expense(db, expense_id)
    if not expense:
        return False

    expense.deleted_at = func.now()
    await db.commit()
    return True
