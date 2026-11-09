from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.service import ServiceCreate, ServiceResponse, ServiceUpdate
from app.services.services import create_service, list_services, update_service

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[ServiceResponse])
async def get_services(
    include_archived: bool = Query(default=False, description="Включать архивированные услуги"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return await list_services(db, include_archived=include_archived)


@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_new_service(
    payload: ServiceCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return await create_service(db, payload)


@router.patch("/{service_id}", response_model=ServiceResponse)
async def patch_service(
    service_id: int,
    payload: ServiceUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    service = await update_service(db, service_id, payload)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Услуга не найдена",
        )
    return service
