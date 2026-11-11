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


class WorkWindowTimeSlot(BaseModel):
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def validate_end_after_start(self) -> "WorkWindowTimeSlot":
        if self.end_time <= self.start_time:
            raise ValueError("end_time должен быть позже start_time")
        return self


class WorkWindowBulkCreate(BaseModel):
    dates: list[date]
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    windows: Optional[list[WorkWindowTimeSlot]] = None

    @field_validator("dates")
    @classmethod
    def validate_dates(cls, v: list[date]) -> list[date]:
        unique_dates = list(dict.fromkeys(v))
        if len(unique_dates) > 62 or len(v) > 62:
            raise ValueError("Не больше 62 дат за запрос")
        return unique_dates

    @model_validator(mode="after")
    def validate_windows(self) -> "WorkWindowBulkCreate":
        if self.windows is not None:
            if len(self.windows) == 0:
                raise ValueError("Список windows не может быть пустым")
            sorted_windows = sorted(self.windows, key=lambda w: w.start_time)
            for i in range(len(sorted_windows) - 1):
                if sorted_windows[i].end_time > sorted_windows[i + 1].start_time:
                    raise ValueError("Рабочие окна не должны пересекаться между собой")
        elif self.start_time is not None and self.end_time is not None:
            if self.end_time <= self.start_time:
                raise ValueError("end_time должен быть позже start_time")
        else:
            raise ValueError("Необходимо указать start_time и end_time или windows")
        return self

    def get_windows(self) -> list[WorkWindowTimeSlot]:
        if self.windows is not None:
            return self.windows
        if self.start_time is not None and self.end_time is not None:
            return [WorkWindowTimeSlot(start_time=self.start_time, end_time=self.end_time)]
        return []


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
