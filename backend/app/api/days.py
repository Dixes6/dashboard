from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.dashboard import DayDetailsResponse
from app.services.dashboard import get_day_details

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/{day_date}", response_model=DayDetailsResponse)
async def get_day(
    day_date: date,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return await get_day_details(db, day_date)
