from datetime import date
from typing import List

from pydantic import BaseModel

from app.schemas.appointment import AppointmentResponse
from app.schemas.work_window import WorkWindowResponse


class CalendarDayResponse(BaseModel):
    date: date
    has_work_window: bool
    appointments_count: int
    completed_income: int


class DayDetailsResponse(BaseModel):
    work_windows: List[WorkWindowResponse]
    appointments: List[AppointmentResponse]
    visits_income: int
    expected_income: int
    other_income: int
    total_income: int
