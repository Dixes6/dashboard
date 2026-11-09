from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.phone import normalize_phone


class ClientCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Имя клиента")
    phone: str = Field(..., description="Номер телефона клиента")
    notes: str | None = Field(default=None, description="Заметки о клиенте")

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Имя клиента не может быть пустым")
        return trimmed

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_phone(value)


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    phone: str | None = Field(default=None)
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, value: str | None) -> str | None:
        if value is not None:
            trimmed = value.strip()
            if not trimmed:
                raise ValueError("Имя клиента не может быть пустым")
            return trimmed
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is not None:
            return normalize_phone(value)
        return value


class ClientResponse(BaseModel):
    id: int
    name: str
    phone: str
    notes: str | None
    visits_count: int = 0
    total_earned: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    total: int
    limit: int
    offset: int
