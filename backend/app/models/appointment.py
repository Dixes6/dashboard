from datetime import datetime
import enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class AppointmentSource(str, enum.Enum):
    MANUAL = "manual"
    ONLINE = "online"


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        SAEnum(
            AppointmentStatus,
            name="appointment_status",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=AppointmentStatus.SCHEDULED,
        server_default=AppointmentStatus.SCHEDULED.value,
        nullable=False,
    )
    source: Mapped[AppointmentSource] = mapped_column(
        SAEnum(
            AppointmentSource,
            name="appointment_source",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=AppointmentSource.MANUAL,
        server_default=AppointmentSource.MANUAL.value,
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    list_price: Mapped[int] = mapped_column(Integer, nullable=False)
    final_price: Mapped[int] = mapped_column(Integer, nullable=False)
    price_overridden: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    client = relationship("Client", backref="appointments")
    appointment_services = relationship(
        "AppointmentService",
        back_populates="appointment",
    )

    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="chk_appointments_ends_after_starts"),
        CheckConstraint("list_price >= 0", name="chk_appointments_list_price_non_negative"),
        CheckConstraint("final_price >= 0", name="chk_appointments_final_price_non_negative"),
        Index("ix_appointments_starts_at", "starts_at"),
        Index("ix_appointments_client_id", "client_id"),
        Index("ix_appointments_status_starts_at", "status", "starts_at"),
    )
