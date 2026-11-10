from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.finance import FinanceEntriesListResponse
from app.services.finance import get_finance_entries

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/entries", response_model=FinanceEntriesListResponse)
async def get_entries(
    type: Annotated[
        str,
        Query(
            pattern=r"^(income|expense)$",
            description="Тип записи: income или expense",
        ),
    ],
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
        return await get_finance_entries(db, type, month)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from None

