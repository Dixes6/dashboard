from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.stats import MonthStatsResponse, MonthSummaryResponse
from app.services.stats import get_month_stats, get_months_summary

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/month", response_model=MonthStatsResponse)
async def get_stats_month(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    month: Annotated[
        str | None,
        Query(
            pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
            description="Месяц в формате YYYY-MM",
        ),
    ] = None,
):
    try:
        return await get_month_stats(db, month)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from None


@router.get("/months", response_model=list[MonthSummaryResponse])
async def get_stats_months(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
):
    return await get_months_summary(db)

