from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.client import ClientCreate, ClientListResponse, ClientResponse, ClientUpdate
from app.services.clients import (
    create_client,
    delete_client,
    get_client_with_stats,
    list_clients_with_stats,
    update_client,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=ClientListResponse)
async def get_clients(
    q: str | None = Query(default=None, description="Поиск по имени (без учёта регистра)"),
    phone: str | None = Query(default=None, description="Поиск по началу номера"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    items, total = await list_clients_with_stats(db, q=q, phone=phone, limit=limit, offset=offset)
    return ClientListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    client = await get_client_with_stats(db, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден",
        )
    return client


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_new_client(
    payload: ClientCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    try:
        client = await create_client(db, payload)
        return client
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.patch("/{client_id}", response_model=ClientResponse)
async def patch_client(
    client_id: int,
    payload: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    try:
        client = await update_client(db, client_id, payload)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент не найден",
            )
        return client
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.delete("/{client_id}")
async def delete_client_endpoint(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    success = await delete_client(db, client_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден",
        )
    return {"status": "ok"}
