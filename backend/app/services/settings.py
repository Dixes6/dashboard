import zoneinfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting
from app.schemas.setting import ALLOWED_SLOT_STEPS, SettingUpdate


async def get_or_create_settings(db: AsyncSession) -> Setting:
    result = await db.execute(select(Setting).limit(1))
    settings_obj = result.scalar_one_or_none()
    if not settings_obj:
        settings_obj = Setting(
            business_name="Студия маникюра",
            timezone="Europe/Moscow",
            slot_step_minutes=15,
        )
        db.add(settings_obj)
        await db.commit()
        await db.refresh(settings_obj)
    return settings_obj


async def update_settings(db: AsyncSession, data: SettingUpdate) -> Setting:
    settings_obj = await get_or_create_settings(db)

    if data.business_name is not None:
        settings_obj.business_name = data.business_name.strip()

    if data.timezone is not None:
        try:
            zoneinfo.ZoneInfo(data.timezone)
        except Exception:
            raise ValueError(f"Недопустимый часовой пояс: '{data.timezone}'")
        settings_obj.timezone = data.timezone

    if data.slot_step_minutes is not None:
        if data.slot_step_minutes not in ALLOWED_SLOT_STEPS:
            allowed = ", ".join(map(str, sorted(ALLOWED_SLOT_STEPS)))
            raise ValueError(f"Недопустимый шаг слота ({data.slot_step_minutes}). Разрешены: {allowed}")
        settings_obj.slot_step_minutes = data.slot_step_minutes

    await db.commit()
    await db.refresh(settings_obj)
    return settings_obj
