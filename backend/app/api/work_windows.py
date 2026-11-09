from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.work_window import (
    WorkWindowBulkCreate,
    WorkWindowCreate,
    WorkWindowResponse,
    WorkWindowUpdate,
)
from app.services.work_windows import (
    bulk_create_work_windows,
    create_work_window,
    delete_work_window,
    list_work_windows,
    update_work_window,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[WorkWindowResponse])
async def get_work_windows(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    return await list_work_windows(db, date_from=date_from, date_to=date_to)


@router.post("", response_model=WorkWindowResponse, status_code=status.HTTP_201_CREATED)
async def create_work_window_endpoint(
    payload: WorkWindowCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await create_work_window(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post(
    "/bulk",
    response_model=list[WorkWindowResponse],
    status_code=status.HTTP_201_CREATED,
)
async def bulk_create_work_windows_endpoint(
    payload: WorkWindowBulkCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await bulk_create_work_windows(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.patch("/{window_id}", response_model=WorkWindowResponse)
async def patch_work_window(
    window_id: int,
    payload: WorkWindowUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        window = await update_work_window(db, window_id, payload)
        if not window:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Рабочее окно не найдено",
            )
        return window
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete("/{window_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work_window_endpoint(
    window_id: int,
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_work_window(db, window_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Рабочее окно не найдено",
        )
