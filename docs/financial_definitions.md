# FinTwin financial definitions (Phase 1)

These definitions apply to profile inputs, deterministic calculations, risk
screening, and dashboard labels. FinTwin currently assumes the user's reported
currency is INR. It does not reconcile bank or lender statements.

## Monthly cash flow

| Term | Definition |
|---|---|
| Monthly income | Net monthly take-home income after income tax and payroll deductions. |
| Monthly expenses | Recurring living and other non-loan outflows. EMI payments are excluded. |
| Monthly EMI | Total required monthly loan instalments, entered separately from expenses. It is a payment flow, not an outstanding debt balance. |
| Cash-flow surplus | Monthly income − monthly expenses − monthly EMI. Negative values indicate a modeled monthly deficit. |
| Cash-flow surplus rate | Cash-flow surplus ÷ monthly income × 100. Undefined when income is zero; may be negative. |
| Actual savings | The user's reported monthly savings after non-EMI expenses and EMI. It is not inferred from cash-flow surplus. |
| Actual savings rate | Reported monthly savings ÷ monthly income × 100. Unknown if monthly savings is not reported; undefined if income is zero. |
| EMI-to-income ratio | Monthly EMI ÷ monthly take-home income × 100. It is not a total debt-to-income ratio. |

The legacy API field `savings_rate_percent` continues to mean cash-flow
surplus rate for compatibility. New clients should use
`cash_flow_surplus_rate_percent` or `actual_savings_rate_percent`.
`debt_to_income_percent` remains as a legacy alias for the EMI-to-income
ratio; new clients should use `emi_to_income_percent`.

## Emergency fund and expense categories

`emergency_fund_months` is emergency-fund balance divided by monthly expenses
plus EMI. It is a total-outflow runway proxy, **not** coverage of essential
expenses. Essential and discretionary expenses are not fields in the saved
financial-profile schema. The optimizer request can accept a user-supplied
split, but that split is not persisted and must not be inferred from total
expenses.

## Balance taxonomy

| Term | Definition and treatment |
|---|---|
| Liquid savings | The `total_savings` profile field, including cash and cash-equivalent savings. The API also exposes it as `liquid_savings`. |
| Emergency fund | A subset of liquid savings. Never add it to liquid savings a second time. |
| Investments | A separately reported investment balance, excluded from liquid savings. Market liquidity and valuation are not assessed. |
| Outstanding debt / liabilities | `total_debt` is the outstanding debt balance, not monthly EMI. Other non-debt liabilities are not recorded. |
| Tracked financial assets | Liquid savings + separately reported investments, when both are available. Emergency funds are already included in liquid savings. |
| Tracked financial liabilities | The reported outstanding debt balance. Other non-debt liabilities are not recorded. |
| Tracked net worth | Tracked financial assets − outstanding debt, only when all three inputs are available. It is explicitly partial: property and other unreported assets and non-debt liabilities are excluded. It is not complete household net worth. |

### Balance reporting provenance

The four persisted balances (`total_savings`, `emergency_fund`,
`investments`, and `total_debt`) each have a corresponding
`*_reported` boolean. A true flag means the user explicitly confirmed the
amount, including an amount of zero. A false flag means the amount is
unknown/unconfirmed, even if the legacy numeric column contains a nonzero
value. Calculations must use only confirmed balances.

For compatibility, the profile API continues to return the original numeric
keys and their stored values. New clients should use each `*_reported` flag
with its nullable canonical value (`reported_total_savings`,
`reported_emergency_fund`, `reported_investments`, or `reported_total_debt`).
Financial-health responses also retain legacy numeric keys; `liquid_savings`
and tracked balance calculations are canonical and therefore null when the
balance is unconfirmed.

The provenance migration preserves the numeric amounts and sets all four
flags false for every pre-existing profile. Users must reconfirm balances
before those values participate in runway, simulation, risk, or net-worth
calculations. New profiles default to false. Partial updates preserve a
status unless that status is explicitly included. Confirming a balance
requires the amount to be included in the same request. The emergency fund is
validated as a subset of liquid savings only when both balances are confirmed.

No total-assets field exists, and the current liability field covers debt only.
The API therefore calls the result `tracked_net_worth` and reports
`net_worth_completeness: "partial"` plus the missing components. It does not
claim a complete net-worth calculation.

## Validation, precision, and missing data

Financial amounts must be finite, non-negative decimal values representable
by SQLAlchemy `Numeric(14, 2)`: at most 999,999,999,999.99 and at most two
decimal places. Cash flow may be negative because it is a calculated result.
The engine raises a validation error for missing required monthly income,
expenses, or EMI. At the calculation layer, optional reported savings and
balance-sheet components stay unknown (`null`) if absent; they are not
converted to zero. Ratios that divide by zero are `null`. Monetary outputs
and percentages are rounded to two decimal places using decimal half-up
rounding.

The profile API requires explicit income, non-EMI expenses, and EMI values
when creating a new profile. Existing-profile updates may omit fields to leave
them unchanged. An explicitly supplied zero is valid.

The profile's legacy numeric balance columns remain non-null for API and
backward compatibility. Corresponding `*_reported` booleans preserve whether a
balance, including zero, was explicitly confirmed. New profiles and
pre-migration profiles default to unconfirmed. Calculations expose unconfirmed
canonical balances as unknown, while legacy numeric response keys retain their
stored values.

## Risk-screening assumptions

The deterministic screen uses these rules, not a statistical probability:

- Zero income: 2 points.
- Negative cash flow: 3 points.
- EMI-to-income greater than 40%: 2 points.
- Emergency-fund runway below 3 months: 2 points.
- Outstanding debt greater than 12 months of take-home income: 1 point.
- Scores 0–1 are Low, 2–4 Medium, and 5 or more High.

The thresholds are indicative project rules, not universal financial advice.
When optional emergency-fund or debt inputs are missing, the assessment lists
the corresponding factor as unassessed and does not treat it as zero.
