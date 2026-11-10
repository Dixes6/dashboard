from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="Europe/Moscow",
        server_default="Europe/Moscow",
    )
    slot_step_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=15,
        server_default="15",
    )

    __table_args__ = (
        CheckConstraint(
            "id = 1",
            name="chk_settings_singleton_id",
        ),
        CheckConstraint(
            "slot_step_minutes > 0",
            name="chk_settings_slot_step_minutes_positive",
        ),
    )
