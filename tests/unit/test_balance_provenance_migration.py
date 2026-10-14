"""Structural tests for the provenance migration; no database is connected."""
from importlib import import_module
from types import SimpleNamespace

import sqlalchemy as sa


migration = import_module(
    "database.migrations.versions.b4f7c2d91a60_add_balance_reporting_provenance"
)


def test_migration_adds_false_non_null_reporting_flags_and_preserves_values(monkeypatch):
    added = []
    monkeypatch.setattr(
        migration,
        "op",
        SimpleNamespace(add_column=lambda table, column: added.append((table, column))),
    )

    migration.upgrade()

    assert [table for table, _ in added] == ["financial_profiles"] * 4
    for (table, column), expected_name in zip(
        added,
        (
            "total_savings_reported",
            "emergency_fund_reported",
            "investments_reported",
            "total_debt_reported",
        ),
    ):
        assert column.name == expected_name
        assert isinstance(column.type, sa.Boolean)
        assert column.nullable is False
        assert str(column.server_default.arg).lower() == "false"
    # Upgrade only adds status columns; the four numeric balance columns are
    # not altered, so their stored values are preserved.
    assert migration.down_revision == "a81d9f43c201"


def test_documented_downgrade_drops_only_reporting_status_columns(monkeypatch):
    dropped = []
    monkeypatch.setattr(
        migration,
        "op",
        SimpleNamespace(drop_column=lambda table, column: dropped.append((table, column))),
    )

    migration.downgrade()

    assert dropped == [
        ("financial_profiles", "total_debt_reported"),
        ("financial_profiles", "investments_reported"),
        ("financial_profiles", "emergency_fund_reported"),
        ("financial_profiles", "total_savings_reported"),
    ]
