
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base

if TYPE_CHECKING:
    from database.models.user import User


class FinancialProfile(Base):
    __tablename__ = "financial_profiles"

    # Primary key and user relationship
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="financial_profile",
    )

    # Core financial fields
    monthly_income: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )

    monthly_expenses: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )

    monthly_emi: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )

    total_savings: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )

    total_savings_reported: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default=false()
    )

    emergency_fund: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )

    emergency_fund_reported: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default=false()
    )

    investments: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )

    investments_reported: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default=false()
    )

    total_debt: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )

    total_debt_reported: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default=false()
    )

    # Extended ML profile fields
    age: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    employment_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    employment_years: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 2),
        nullable=True,
    )

    monthly_savings: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    dependents: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    insurance: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    health_insurance: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    income_stability_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    financial_goal: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    investment_experience: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    expected_salary_growth_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 2),
        nullable=True,
    )

    expected_expense_inflation_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 2),
        nullable=True,
    )

    planned_major_expense: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    planned_expense_month: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Timestamp
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
