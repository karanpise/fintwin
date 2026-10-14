
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base

if TYPE_CHECKING:
    from database.models.financial_profile import FinancialProfile


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("uq_users_email_lower", text("lower(email)"), unique=True),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    financial_profile: Mapped["FinancialProfile | None"] = relationship(
        "FinancialProfile",
        back_populates="user",
        uselist=False,
    )
