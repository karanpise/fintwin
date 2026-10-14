"""Helpers for distinguishing confirmed balances from legacy numeric values."""
from collections.abc import Mapping

from financial_engine.monetary import parse_money


_MISSING = object()
BALANCE_FIELDS = (
    "total_savings",
    "emergency_fund",
    "investments",
    "total_debt",
)


def _read(profile, field):
    if isinstance(profile, Mapping):
        return profile.get(field, _MISSING)
    return getattr(profile, field, _MISSING)


def balance_is_reported(profile, field: str) -> bool:
    """Return whether a balance is confirmed.

    A missing reporting flag is treated as unconfirmed. This keeps legacy
    numeric defaults from becoming confirmed balances in direct/internal
    callers as well as in persisted profiles.
    """
    if field not in BALANCE_FIELDS:
        raise ValueError(f"Unsupported balance field: {field}.")

    status = _read(profile, f"{field}_reported")
    if status is _MISSING:
        return False
    if not isinstance(status, bool):
        raise ValueError(f"{field}_reported must be a boolean.")
    return status


def read_reported_balance(profile, field: str):
    """Return a validated Decimal only when its explicit status is reported."""
    if not balance_is_reported(profile, field):
        return None
    value = _read(profile, field)
    if value is _MISSING or value is None:
        raise ValueError(f"{field} is marked reported but its amount is missing.")
    return parse_money(value, field)

