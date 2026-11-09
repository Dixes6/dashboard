from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Название услуги")
    price: int = Field(..., ge=0, description="Цена в рублях")
    duration_minutes: int = Field(..., gt=0, description="Длительность в минутах")
    sort_order: int = Field(default=0, description="Порядок сортировки")
    is_active: bool = Field(default=True, description="Флаг активности")

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Название услуги не может быть пустым")
        return trimmed


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    price: int | None = Field(default=None, ge=0)
    duration_minutes: int | None = Field(default=None, gt=0)
    sort_order: int | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, value: str | None) -> str | None:
        if value is not None:
            trimmed = value.strip()
            if not trimmed:
                raise ValueError("Название услуги не может быть пустым")
            return trimmed
        return value


class ServiceResponse(BaseModel):
    id: int
    name: str
    price: int
    duration_minutes: int
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
