
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class FinancialProfileCreate(BaseModel):
    # Existing financial fields
    monthly_income: Decimal = Field(default=Decimal("0"), ge=0)
    monthly_expenses: Decimal = Field(default=Decimal("0"), ge=0)
    monthly_emi: Decimal = Field(default=Decimal("0"), ge=0)
    total_savings: Decimal = Field(default=Decimal("0"), ge=0)
    emergency_fund: Decimal = Field(default=Decimal("0"), ge=0)
    investments: Decimal = Field(default=Decimal("0"), ge=0)
    total_debt: Decimal = Field(default=Decimal("0"), ge=0)

    # Extended ML profile fields
    age: int | None = Field(default=None, ge=18, le=100)
    employment_type: str | None = None
    employment_years: Decimal | None = Field(default=None, ge=0)
    monthly_savings: Decimal | None = Field(default=None, ge=0)
    dependents: int | None = Field(default=None, ge=0, le=30)
    insurance: str | None = None
    health_insurance: str | None = None
    income_stability_score: Decimal | None = Field(
        default=None, ge=0, le=100
    )
    financial_goal: str | None = None
    investment_experience: str | None = None
    expected_salary_growth_pct: Decimal | None = Field(
        default=None, ge=-100, le=500
    )
    expected_expense_inflation_pct: Decimal | None = Field(
        default=None, ge=-100, le=500
    )
    planned_major_expense: str | None = None
    
    planned_expense_month: int | None = Field(
        default=None,
        ge=0,
        le=36,
    )



class FinancialProfileResponse(FinancialProfileCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
