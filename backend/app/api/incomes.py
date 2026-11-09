from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.financial import IncomeCreate, IncomeResponse, IncomeUpdate
from app.services.incomes import create_income, delete_income, list_incomes, update_income

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[IncomeResponse])
async def get_incomes(
    date_from: date | None = Query(default=None, description="Начало периода (включительно)"),
    date_to: date | None = Query(default=None, description="Конец периода (включительно)"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return await list_incomes(db, date_from=date_from, date_to=date_to)


@router.post("", response_model=IncomeResponse, status_code=status.HTTP_201_CREATED)
async def create_new_income(
    payload: IncomeCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return await create_income(db, payload)


@router.patch("/{income_id}", response_model=IncomeResponse)
async def patch_income(
    income_id: int,
    payload: IncomeUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    income = await update_income(db, income_id, payload)
    if not income:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись дохода не найдена",
        )
    return income


@router.delete("/{income_id}")
async def delete_income_endpoint(
    income_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    success = await delete_income(db, income_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись дохода не найдена",
        )
    return {"status": "ok"}
