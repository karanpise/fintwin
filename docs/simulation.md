# FinTwin monthly simulation (Phase 2)

The simulator compares a baseline and a hypothetical scenario over 3, 6, 12,
24, or 60 months. Both start from copies of the same saved financial profile.
Simulation never writes to that profile. Repeated identical inputs produce
identical results.

## Definitions and formulas

Monthly income is take-home income. Monthly expenses are non-loan expenses and
exclude EMI. EMI is reported separately as a monthly payment flow. For month
`t`:

```
cash_flow_surplus[t] = income[t] - expenses[t] - EMI[t]
cumulative_cash_flow_surplus = sum(cash_flow_surplus[t])
cumulative_net_cash_flow_after_one_time_costs =
    sum(cash_flow_surplus[t] - one_time_cost[t])
emergency_fund_runway[t] = emergency_fund[t] / (expenses[t] + EMI[t])
```

Runway is null when the emergency-fund balance or monthly outflow is unknown or
outflow is zero. It uses total outflow, not essential expenses. The saved
profile has no essential/discretionary expense split, so the simulator does not
invent one.

The balance taxonomy follows `financial_definitions.md`: liquid savings is the
cash and cash-equivalent balance; the emergency fund is a subset of it and is
never added twice; investments are separate; debt is an outstanding balance,
not EMI. Tracked net worth is liquid savings + investments − debt, only when
all three are known. It remains partial because property, other assets, and
non-debt liabilities are not captured.

Persisted balances are usable only when their corresponding reporting status
is true. An unconfirmed stored numeric value is retained under legacy profile
keys but is treated as unknown in projections; liquid funds, emergency
runway, investment value, debt, and tracked net worth are not inferred from
that value. An unknown emergency fund cannot satisfy a configured optimizer
runway constraint.

## State transitions and assumptions

- Income, expenses, existing EMI, and investments stay flat unless scenario
  overrides or recurring deltas change them. A recurring delta begins in the
  configured `changes_start_month` and continues to the end of the horizon.
- One-time costs are charged at the beginning of their configured month.
  `one_time_source` selects liquid savings or the emergency-fund subset. The
  balance never goes below zero; any amount that cannot be funded is reported
  as `unfunded_cost` and also contributes to the negative post-cost cash-flow
  summary. Unfunded monthly deficits are separately shown as
  `unfunded_cash_flow_deficit`. A purchase does not add the purchased item's
  value to tracked assets because no purchase-asset valuation is available.
  Existing legacy `additional_upfront_cost` means a month-1 cost sourced from
  the emergency fund to preserve its former API meaning. New clients should
  provide `one_time_cost` and `one_time_source` explicitly.
- If `apply_surplus_to_savings` is true (default), positive monthly surplus is
  added to liquid savings. A deficit draws non-emergency liquid savings first,
  then the emergency-fund subset. Unfunded deficit remains visible in monthly
  cash flow and is not represented as negative savings. When false, cash flow
  does not change the savings balance.
- Savings or emergency-fund depletion is reported as month `0` when the balance
  starts at zero, the first projected month reaching zero otherwise, or null
  when the relevant balance is unavailable or not depleted. Minimum liquid
  savings includes the starting balance, post-event balance, and month-end
  balances.
- Existing debt is held constant unless a complete new-loan assumption is
  supplied. For a new loan, principal, nominal annual percentage rate, term in
  months, and start month are explicit inputs. Monthly rate is annual rate /
  1200. Fixed payment is `P*r*(1+r)^n / ((1+r)^n - 1)`, or `P/n` when `r=0`;
  payment, interest, and remaining balance are rounded to cents using decimal
  half-up. Each month interest is balance × monthly rate; principal paid is
  payment − interest, capped at amount due in the final payment. The new
  principal is added to known debt on its start month. If starting debt is
  unknown, tracked debt/net worth stay unknown.
- No salary growth, inflation, investment returns, tax changes, refinancing,
  credit draw, or unspecified costs are assumed. Generic EMI changes do not
  amortize debt because their loan terms are unknown.
- Monetary inputs must be finite, non-negative amounts representable to two
  decimal places within `Numeric(14, 2)` limits. Recurring deltas can be
  negative, but resulting income, expenses, and EMI must remain non-negative.
  A new-loan annual rate must be between 0% and 100% with at most two decimal
  places, and its term is limited to 600 months.
  Cash flow can be negative. Zero income yields a null rate where division by
  income would otherwise be required.

## Example

Start with monthly income ₹10,000, non-EMI expenses ₹4,000, EMI ₹1,000,
liquid savings ₹6,000, emergency subset ₹3,000, investments ₹2,000, and debt
₹5,000. A 3-month unchanged baseline has monthly surplus ₹5,000 and liquid
savings of ₹11,000, ₹16,000, and ₹21,000. Ending tracked net worth is
₹21,000 + ₹2,000 − ₹5,000 = ₹18,000. If a recurring expense increase of ₹500
starts in month 1, scenario surplus is ₹4,500 monthly and liquid savings end
at ₹19,500. The saved profile remains unchanged.

## API

`POST /me/simulate` retains all prior request fields and legacy one-month
response keys. It adds `horizon_months`, explicit recurring deltas and start
month, one-time cost timing/source, surplus-to-savings assumption, and optional
new-loan inputs. The response adds `baseline`, `scenario`, and
`monthly_differences`; each projection includes monthly rows and summary safety
indicators. Allowed horizons are 3, 6, 12, 24, and 60. The existing inactive
backup page can continue to consume the legacy keys.
