import zoneinfo

from pydantic import BaseModel, ConfigDict, field_validator

ALLOWED_SLOT_STEPS = {5, 10, 15, 20, 30, 60}


class SettingResponse(BaseModel):
    id: int
    business_name: str
    timezone: str
    slot_step_minutes: int

    model_config = ConfigDict(from_attributes=True)


class SettingUpdate(BaseModel):
    business_name: str | None = None
    timezone: str | None = None
    slot_step_minutes: int | None = None

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                zoneinfo.ZoneInfo(value)
            except Exception:
                raise ValueError(f"Недопустимый часовой пояс: '{value}'")
        return value

    @field_validator("slot_step_minutes")
    @classmethod
    def validate_slot_step_minutes(cls, value: int | None) -> int | None:
        if value is not None and value not in ALLOWED_SLOT_STEPS:
            allowed = ", ".join(map(str, sorted(ALLOWED_SLOT_STEPS)))
            raise ValueError(f"Недопустимый шаг слота ({value}). Разрешены только: {allowed}")
        return value
