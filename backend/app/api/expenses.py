from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.financial import ExpenseCreate, ExpenseResponse, ExpenseUpdate
from app.services.expenses import create_expense, delete_expense, list_expenses, update_expense

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[ExpenseResponse])
async def get_expenses(
    date_from: date | None = Query(default=None, description="Начало периода (включительно)"),
    date_to: date | None = Query(default=None, description="Конец периода (включительно)"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return await list_expenses(db, date_from=date_from, date_to=date_to)


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_new_expense(
    payload: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return await create_expense(db, payload)


@router.patch("/{expense_id}", response_model=ExpenseResponse)
async def patch_expense(
    expense_id: int,
    payload: ExpenseUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    expense = await update_expense(db, expense_id, payload)
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись расхода не найдена",
        )
    return expense


@router.delete("/{expense_id}")
async def delete_expense_endpoint(
    expense_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    success = await delete_expense(db, expense_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись расхода не найдена",
        )
    return {"status": "ok"}
