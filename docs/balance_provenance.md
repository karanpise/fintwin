# Balance reporting provenance

## Meaning of the reporting flags

`total_savings_reported`, `emergency_fund_reported`,
`investments_reported`, and `total_debt_reported` explicitly state whether the
corresponding amount is confirmed by the user. A confirmed amount may be
positive or zero. An unconfirmed balance is unknown to calculations even
though its legacy numeric column remains populated.

The migration adds each flag as `BOOLEAN NOT NULL DEFAULT FALSE`. Existing
numeric amounts are not changed, and all existing profiles become
unconfirmed. ORM-created profiles use the same false default. The profile form
requires a separate confirmation checkbox; checking it with an amount of
`0.00` explicitly reports zero.
Calculation inputs without a corresponding reporting flag are also treated
as unconfirmed; callers must opt in explicitly before a stored amount can
affect balance-derived metrics.

## API compatibility

The profile response retains `total_savings`, `emergency_fund`,
`investments`, and `total_debt` with their prior numeric serialization. It
adds the four boolean reporting flags and nullable canonical values named
`reported_total_savings`, `reported_emergency_fund`, `reported_investments`,
and `reported_total_debt`. New clients must use the canonical value and its
flag. On profile updates, omitted numeric fields and omitted status flags are
preserved. Setting a status true requires submitting its amount in the same
request; a numeric amount without an explicit true status remains
unconfirmed. A false status may be submitted without an amount to mark the
balance unknown while retaining the legacy amount for compatibility.

Financial-health responses retain their numeric legacy balance keys and add
the same statuses and canonical values. Cash-flow and EMI calculations do not
depend on balance provenance. Emergency runway and tracked net worth use only
confirmed balances. Risk analysis reports unconfirmed emergency coverage and
debt as unassessed. Simulation projections retain unknown balances as null.
When an optimizer runway minimum is configured, missing or unconfirmed
emergency-fund data cannot satisfy that constraint.

The emergency fund must not exceed liquid savings when both are confirmed.
If one is unknown, the system does not infer the missing balance or apply
that subset comparison.

## Downgrade strategy and limitation

The downgrade drops only the four status columns, leaving the existing
numeric values untouched. This is structurally reversible but loses all
confirmation state, including confirmations made after the upgrade. Before
downgrading, export the status flags and their associated amounts. Do not
roll back to an older application version after confirmations have begun
unless the rollback plan prevents that version from treating retained numeric
values as confirmed. Reconfirmations cannot be reconstructed after the flags
are dropped.

## Verification boundary

Migration tests inspect the operation definitions without opening a database.
The migration has not been executed against PostgreSQL in this repository
change. A disposable PostgreSQL staging database must be explicitly
configured and confirmed before upgrade/downgrade integration testing. No
production database may be used for that verification.
