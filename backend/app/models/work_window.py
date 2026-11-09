from datetime import date, time

from sqlalchemy import CheckConstraint, Date, Index, Integer, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WorkWindow(Base):
    __tablename__ = "work_windows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="chk_work_windows_end_after_start"),
        Index("ix_work_windows_date", "date"),
    )
