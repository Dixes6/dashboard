from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.dashboard import CalendarDayResponse
from app.services.dashboard import get_calendar_month

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[CalendarDayResponse])
async def get_calendar(
    month: str = Query(
        ...,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="Месяц в формате YYYY-MM",
    ),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    try:
        return await get_calendar_month(db, month)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
