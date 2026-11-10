import zoneinfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting
from app.schemas.setting import ALLOWED_SLOT_STEPS, SettingUpdate


async def get_or_create_settings(db: AsyncSession) -> Setting:
    stmt = (
        pg_insert(Setting)
        .values(
            id=1,
            business_name="Студия маникюра",
            timezone="Europe/Moscow",
            slot_step_minutes=15,
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await db.execute(stmt)
    await db.commit()

    result = await db.execute(select(Setting).where(Setting.id == 1))
    settings_obj = result.scalar_one()
    return settings_obj


async def update_settings(db: AsyncSession, data: SettingUpdate) -> Setting:
    settings_obj = await get_or_create_settings(db)

    if data.business_name is not None:
        settings_obj.business_name = data.business_name.strip()

    if data.timezone is not None:
        try:
            zoneinfo.ZoneInfo(data.timezone)
        except Exception:
            raise ValueError(f"Недопустимый часовой пояс: '{data.timezone}'") from None
        settings_obj.timezone = data.timezone

    if data.slot_step_minutes is not None:
        if data.slot_step_minutes not in ALLOWED_SLOT_STEPS:
            allowed = ", ".join(map(str, sorted(ALLOWED_SLOT_STEPS)))
            raise ValueError(
                f"Недопустимый шаг слота ({data.slot_step_minutes}). Разрешены: {allowed}"
            )
        settings_obj.slot_step_minutes = data.slot_step_minutes

    await db.commit()
    await db.refresh(settings_obj)
    return settings_obj
