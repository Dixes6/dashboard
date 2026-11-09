from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AppointmentService(Base):
    __tablename__ = "appointment_services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    appointment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("appointments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    service_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    price_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    appointment = relationship("Appointment", back_populates="appointment_services")
    service = relationship("Service")

    __table_args__ = (
        CheckConstraint(
            "price_snapshot >= 0",
            name="chk_appointment_services_price_snapshot_non_negative",
        ),
        CheckConstraint(
            "duration_snapshot > 0",
            name="chk_appointment_services_duration_snapshot_positive",
        ),
    )
