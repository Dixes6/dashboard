from datetime import date, datetime, time
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.appointment import AppointmentSource, AppointmentStatus


class InlineClientCreate(BaseModel):
    name: str
    phone: str


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
    service_ids: List[int]
    note: Optional[str] = None
    final_price: Optional[int] = None
    force: bool = False

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
    note: Optional[str] = None
    status: Optional[AppointmentStatus] = None
    client_id: Optional[int] = None
    final_price: Optional[int] = None
    service_ids: Optional[List[int]] = None
    reset_price: bool = False
    force: bool = False


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
