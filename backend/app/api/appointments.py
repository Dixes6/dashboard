from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.appointment import AppointmentStatus
from app.models.user import User
from app.schemas.appointment import AppointmentCreate, AppointmentResponse, AppointmentUpdate
from app.services.appointments import (
    NeedsConfirmationError,
    create_appointment,
    delete_appointment,
    get_appointment,
    get_next_appointment,
    list_appointments,
    update_appointment,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[AppointmentResponse])
async def get_appointments(
    date: date | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    status: AppointmentStatus | None = Query(default=None),
    client_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    return await list_appointments(
        db,
        date_filter=date,
        date_from=date_from,
        date_to=date_to,
        status=status,
        client_id=client_id,
    )


@router.get(
    "/next",
    response_model=AppointmentResponse,
    responses={
        200: {"description": "Ближайшая запись"},
        204: {"description": "Нет предстоящих записей"},
    },
)
async def get_next_appointment_endpoint(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    appt = await get_next_appointment(db)
    if not appt:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return appt


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment_endpoint(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
):
    appt = await get_appointment(db, appointment_id)
    if not appt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись не найдена",
        )
    return appt


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment_endpoint(
    payload: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await create_appointment(db, payload)
    except NeedsConfirmationError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "needs_confirmation",
                "warnings": e.warnings,
                "overlapping_ids": e.overlapping_ids,
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
async def patch_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        appt = await update_appointment(db, appointment_id, payload)
        if not appt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Запись не найдена",
            )
        return appt
    except NeedsConfirmationError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "needs_confirmation",
                "warnings": e.warnings,
                "overlapping_ids": e.overlapping_ids,
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.delete("/{appointment_id}")
async def delete_appointment_endpoint(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_appointment(db, appointment_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись не найдена",
        )
    return {"status": "ok"}
