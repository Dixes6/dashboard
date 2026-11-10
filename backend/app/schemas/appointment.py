from datetime import date, datetime, time, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.appointment import AppointmentSource, AppointmentStatus


def _validate_starts_at_bounds(v: datetime | None) -> datetime | None:
    if v is None:
        return v
    if v.year < 2000:
        raise ValueError("starts_at не может быть раньше 2000 года")
    now = datetime.now(timezone.utc) if v.tzinfo else datetime.now()
    today = now.date()
    try:
        max_date = today.replace(year=today.year + 5)
    except ValueError:
        max_date = today.replace(year=today.year + 5, day=28)
    if v.date() > max_date:
        raise ValueError("starts_at не может быть позже чем через 5 лет")
    return v


class InlineClientCreate(BaseModel):
    name: str = Field(..., max_length=200)
    phone: str = Field(..., max_length=32)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Имя клиента не может быть пустым")
        return stripped


class AppointmentServiceSnapshot(BaseModel):
    service_id: int
    name_snapshot: str
    price_snapshot: int
    duration_snapshot: int
    position: int


class AppointmentCreate(BaseModel):
    client_id: Optional[int] = None
    client: Optional[InlineClientCreate] = None

    starts_at: datetime
    ends_at: Optional[datetime] = None
    service_ids: List[int] = Field(..., min_length=1, max_length=20)
    note: Optional[str] = Field(default=None, max_length=2000)
    final_price: Optional[int] = Field(default=None, ge=0, le=10_000_000)
    force: bool = False

    @field_validator("starts_at")
    @classmethod
    def validate_starts_at(cls, v: datetime) -> datetime:
        res = _validate_starts_at_bounds(v)
        assert res is not None
        return res

    @model_validator(mode="after")
    def validate_client_field(self) -> "AppointmentCreate":
        if self.client_id is None and self.client is None:
            raise ValueError("Необходимо указать client_id или client")
        if self.client_id is not None and self.client is not None:
            raise ValueError("Нельзя указывать одновременно client_id и client")
        return self


class AppointmentUpdate(BaseModel):
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    note: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[AppointmentStatus] = None
    client_id: Optional[int] = None
    final_price: Optional[int] = Field(default=None, ge=0, le=10_000_000)
    service_ids: Optional[List[int]] = Field(default=None, min_length=1, max_length=20)
    reset_price: bool = False
    force: bool = False

    @field_validator("starts_at")
    @classmethod
    def validate_starts_at(cls, v: Optional[datetime]) -> Optional[datetime]:
        return _validate_starts_at_bounds(v)


class AppointmentClientInfo(BaseModel):
    id: int
    name: str
    phone: str


class AppointmentServiceInfo(BaseModel):
    service_id: int
    name_snapshot: str
    price_snapshot: int
    duration_snapshot: int
    position: int


class AppointmentResponse(BaseModel):
    id: int
    client: AppointmentClientInfo
    starts_at: datetime
    ends_at: datetime
    local_date: date
    local_start_time: time
    local_end_time: time
    status: AppointmentStatus
    source: AppointmentSource
    note: Optional[str]
    list_price: int
    final_price: int
    price_overridden: bool
    services: List[AppointmentServiceInfo]
    warnings: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=False)
