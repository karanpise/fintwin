
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from financial_engine.monetary import parse_money


MAX_MONEY = Decimal("999999999999.99")
MONEY_FIELDS = (
    "monthly_income",
    "monthly_expenses",
    "monthly_emi",
    "total_savings",
    "emergency_fund",
    "investments",
    "total_debt",
    "monthly_savings",
)
REQUIRED_MONTHLY_BASELINE_FIELDS = (
    "monthly_income",
    "monthly_expenses",
    "monthly_emi",
)


def missing_monthly_baseline_fields(payload: "FinancialProfileCreate") -> list[str]:
    """Find required cash-flow values omitted when creating a new profile."""
    return [
        field
        for field in REQUIRED_MONTHLY_BASELINE_FIELDS
        if field not in payload.model_fields_set
    ]


class FinancialProfileCreate(BaseModel):
    # Existing financial fields
    monthly_income: Decimal = Field(
        default=Decimal("0"), ge=0, le=MAX_MONEY,
        description="Net monthly take-home income after tax and payroll deductions.",
    )
    monthly_expenses: Decimal = Field(
        default=Decimal("0"), ge=0, le=MAX_MONEY,
        description="Recurring non-loan expenses; excludes EMI payments.",
    )
    monthly_emi: Decimal = Field(
        default=Decimal("0"), ge=0, le=MAX_MONEY,
        description="Required monthly loan instalments, separate from expenses.",
    )
    total_savings: Decimal = Field(
        default=Decimal("0"), ge=0, le=MAX_MONEY,
        description="Liquid savings including the emergency-fund subset; excludes investments.",
    )
    emergency_fund: Decimal = Field(
        default=Decimal("0"), ge=0, le=MAX_MONEY,
        description="Emergency-fund amount included within total_savings.",
    )
    investments: Decimal = Field(
        default=Decimal("0"), ge=0, le=MAX_MONEY,
        description="Investment balances reported separately from liquid savings.",
    )
    total_debt: Decimal = Field(
        default=Decimal("0"), ge=0, le=MAX_MONEY,
        description="Outstanding debt balance, not monthly EMI payments.",
    )

    # Omitted status means "preserve on update" and "unconfirmed on create".
    # A numeric value alone never confirms a balance.
    total_savings_reported: bool | None = None
    emergency_fund_reported: bool | None = None
    investments_reported: bool | None = None
    total_debt_reported: bool | None = None

    # Extended ML profile fields
    age: int | None = Field(default=None, ge=18, le=100)
    employment_type: str | None = None
    employment_years: Decimal | None = Field(default=None, ge=0)
    monthly_savings: Decimal | None = Field(default=None, ge=0, le=MAX_MONEY)
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

    @field_validator(*MONEY_FIELDS)
    @classmethod
    def validate_money_precision(cls, value, info):
        if value is None:
            return None
        return parse_money(value, info.field_name)

    @model_validator(mode="after")
    def validate_balance_reporting(self):
        for field in (
            "total_savings",
            "emergency_fund",
            "investments",
            "total_debt",
        ):
            status_field = f"{field}_reported"
            if status_field in self.model_fields_set:
                status = getattr(self, status_field)
                if status is None:
                    raise ValueError(f"{status_field} must be true or false, not null.")
                if status and field not in self.model_fields_set:
                    raise ValueError(
                        f"Provide {field} when explicitly confirming it as reported."
                    )
        return self



class FinancialProfileResponse(FinancialProfileCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int

    @computed_field
    @property
    def reported_total_savings(self) -> Decimal | None:
        return self.total_savings if self.total_savings_reported else None

    @computed_field
    @property
    def reported_emergency_fund(self) -> Decimal | None:
        return self.emergency_fund if self.emergency_fund_reported else None

    @computed_field
    @property
    def reported_investments(self) -> Decimal | None:
        return self.investments if self.investments_reported else None

    @computed_field
    @property
    def reported_total_debt(self) -> Decimal | None:
        return self.total_debt if self.total_debt_reported else None
