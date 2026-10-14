from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.schemas.financial_profile import (
    FinancialProfileCreate,
    missing_monthly_baseline_fields,
)


@pytest.mark.parametrize(
    "value",
    [Decimal("NaN"), Decimal("Infinity"), Decimal("-0.01"),
     Decimal("1000000000000.00"), Decimal("1.001")],
)
def test_profile_rejects_amounts_not_storable_as_numeric_14_2(value):
    with pytest.raises(ValidationError):
        FinancialProfileCreate(monthly_income=value)


def test_profile_accepts_maximum_numeric_14_2_amount():
    profile = FinancialProfileCreate(
        monthly_income=Decimal("999999999999.99")
    )

    assert profile.monthly_income == Decimal("999999999999.99")


def test_optional_reported_savings_remains_missing():
    profile = FinancialProfileCreate(monthly_savings=None)

    assert profile.monthly_savings is None


def test_new_profile_requires_explicit_monthly_baseline_but_allows_zero():
    missing = FinancialProfileCreate()
    assert missing_monthly_baseline_fields(missing) == [
        "monthly_income",
        "monthly_expenses",
        "monthly_emi",
    ]

    explicit_zero = FinancialProfileCreate(
        monthly_income=0,
        monthly_expenses=0,
        monthly_emi=0,
    )
    assert missing_monthly_baseline_fields(explicit_zero) == []


def test_balance_amount_does_not_confirm_legacy_or_new_profile_value():
    profile = FinancialProfileCreate(
        monthly_income=1,
        monthly_expenses=0,
        monthly_emi=0,
        total_savings=Decimal("125.00"),
    )

    assert profile.total_savings == Decimal("125.00")
    assert profile.total_savings_reported is None


def test_explicit_reported_zero_is_valid():
    profile = FinancialProfileCreate(
        monthly_income=1,
        monthly_expenses=0,
        monthly_emi=0,
        total_savings=Decimal("0.00"),
        total_savings_reported=True,
    )

    assert profile.total_savings_reported is True


def test_reported_balance_requires_explicit_amount_and_boolean_status():
    with pytest.raises(ValidationError, match="Provide total_savings"):
        FinancialProfileCreate(total_savings_reported=True)
    with pytest.raises(ValidationError, match="must be true or false"):
        FinancialProfileCreate(total_savings_reported=None)


def test_unreported_positive_legacy_amount_is_allowed_but_unconfirmed():
    profile = FinancialProfileCreate(
        total_savings=Decimal("125.00"),
        total_savings_reported=False,
    )
    assert profile.total_savings == Decimal("125.00")
    assert profile.total_savings_reported is False
