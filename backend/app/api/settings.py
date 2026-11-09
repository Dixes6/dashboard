from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.setting import SettingResponse, SettingUpdate
from app.services.settings import get_or_create_settings, update_settings

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=SettingResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    settings_obj = await get_or_create_settings(db)
    return settings_obj


@router.put("", response_model=SettingResponse)
async def put_settings(
    payload: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    settings_obj = await update_settings(db, payload)
    return settings_obj
