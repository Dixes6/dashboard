from datetime import date, time
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class WorkWindowCreate(BaseModel):
    date: date
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def validate_end_after_start(self) -> "WorkWindowCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time должен быть позже start_time")
        return self


class WorkWindowBulkCreate(BaseModel):
    dates: list[date]
    start_time: time
    end_time: time

    @field_validator("dates")
    @classmethod
    def validate_dates(cls, v: list[date]) -> list[date]:
        unique_dates = list(dict.fromkeys(v))
        if len(unique_dates) > 62 or len(v) > 62:
            raise ValueError("Не больше 62 дат за запрос")
        return unique_dates

    @model_validator(mode="after")
    def validate_end_after_start(self) -> "WorkWindowBulkCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time должен быть позже start_time")
        return self


class WorkWindowUpdate(BaseModel):
    date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None

    @model_validator(mode="after")
    def validate_end_after_start(self) -> "WorkWindowUpdate":
        if self.start_time is not None and self.end_time is not None:
            if self.end_time <= self.start_time:
                raise ValueError("end_time должен быть позже start_time")
        return self


class WorkWindowResponse(BaseModel):
    id: int
    date: date
    start_time: time
    end_time: time

    model_config = ConfigDict(from_attributes=True)
