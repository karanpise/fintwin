from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


CENT = Decimal("0.01")
MAX_MONEY = Decimal("999999999999.99")


def parse_money(value: Any, field: str) -> Decimal:
    """Validate a non-negative amount representable by Numeric(14, 2)."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{field} must be a valid monetary amount.") from exc

    if not amount.is_finite():
        raise ValueError(f"{field} must be finite.")
    if amount < 0:
        raise ValueError(f"{field} cannot be negative.")
    if amount > MAX_MONEY:
        raise ValueError(
            f"{field} exceeds the maximum supported amount "
            "of 999999999999.99."
        )
    if amount.quantize(CENT) != amount:
        raise ValueError(f"{field} supports at most two decimal places.")

    return amount


def round_money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def round_percent(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)
