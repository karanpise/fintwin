# Minimum-intervention optimizer (Phase 3)

The optimizer targets a user's stated monthly cash-flow surplus. It does not
modify the saved profile. Its candidate projections use the deterministic
monthly simulator and the definitions in `financial_definitions.md` and
`simulation.md`.

## Goal, objective, and feasibility

Let `I` be saved take-home income, `E` saved non-EMI expenses, `M` saved EMI,
`A` user-proposed additional expenses, and `L` user-proposed additional EMI.
The proposed scenario's pre-intervention cash flow is:

```
F0 = I - E - M - A - L
R  = max(0, target_monthly_surplus - F0)
```

Candidate variables are non-negative recurring monthly amounts:

- `x`: reduction in non-EMI expenses;
- `y`: reduction in the proposed additional EMI only;
- `z`: user-stated feasible increase in monthly take-home income.

The objective is to minimize the absolute monthly rupee amount:

```
minimize x + y + z
```

One rupee in each intervention has equal objective cost. This is an explicit
neutral unit-cost convention, not a claim that the interventions have equal
personal burden. The user supplies the upper bounds. Expense reductions are
available only when the user supplies both essential and discretionary
expenses and they sum exactly to saved expenses; `x` cannot exceed either the
user's maximum or the supplied discretionary amount. `y` cannot exceed the
user's maximum or proposed EMI. `z` cannot exceed the user-stated feasible
income increase. No categories or feasible income increase are inferred.

A candidate is feasible only if the Phase 2 simulator reports the target
surplus in every month of the requested horizon, all inputs and projected
balances pass the simulator's validation, and any configured emergency-fund
runway floor is satisfied in every projected month where runway is defined.
Runway is emergency-fund balance divided by non-EMI expenses plus EMI. If the
emergency-fund balance is missing or projected outflow is zero, the optional
runway constraint is reported as unassessed instead of treating unknown as
zero. The saved schema also defaults balances to zero and cannot distinguish
an explicitly reported zero emergency fund from an unreported/defaulted
balance. A stored zero is therefore reported as unassessed for this optional
constraint rather than treated as known.

## Search and deterministic tie handling

The target surplus is a linear lower bound on `x + y + z`. When an emergency
runway floor is configured and inputs are available, the optimizer also
calculates the minimum reduction in total outflow needed to meet that floor.
The search fixes the smallest total intervention implied by these constraints,
then enumerates the vertices of the bounded allocation polygon for `x`, `y`,
and `z`. Each candidate vertex is run through `simulate_financial_scenario`;
the candidate is retained only when the simulated goal and constraints pass.

The response lists all feasible minimum-cost vertices found as
`tied_minimum_options`. The continuous set of interior mixtures is not
enumerated. For compatibility with existing clients that expect one result,
the legacy recommendation fields select the lexicographically smallest
feasible vertex ordered by `(x, y, z)` ascending. The response states the
search strategy and does not claim global optimality under future constraints
or search spaces beyond the implemented bounded allocation polygon.

When there are no feasible candidates, the response retains the legacy
`feasible`, `remaining_shortfall`, and recommendation fields, and adds concise
rejection reasons. The projection shown for an infeasible result is the
configured maximum candidate when that candidate was simulated.

## Supported inputs and limits

- User-provided discretionary expense reductions.
- User-stated feasible income increases, subject to the entered maximum.
- Reductions to a proposed additional EMI, capped at that proposed EMI.
- Proposed recurring monthly expenses and EMI used as the scenario baseline.
- Projection horizons of 3, 6, 12, 24, or 60 months.
- Optional user-specified minimum emergency-fund runway in months.

The existing profile stores a planned-expense label and month but no planned
purchase amount, financing/down-payment details, or purchase valuation.
Therefore purchase delay, budget, and down-payment optimization are not
available. Loan-term comparisons are also unavailable in this optimizer; the
simulation's explicitly specified new-loan inputs are not treated as
intervention preferences. Existing debt amortization, salary growth, inflation,
investment return, taxes, and real-world feasibility are not invented.

The simulator applies positive cash-flow surplus to liquid savings by default
and has no growth/return assumptions. It does not turn EMI reduction into a
change to outstanding debt unless a loan schedule exists; current optimizer
EMI reduction applies only to the proposed scenario payment. Tracked net worth
is shown only when its Phase 1 balance inputs support it.

## Example

Saved profile: income ₹50,000, expenses ₹30,000, EMI ₹5,000. Proposed costs:
additional expenses ₹1,000 and additional EMI ₹2,000. Target surplus: ₹15,000.

```
F0 = 50,000 - 30,000 - 5,000 - 1,000 - 2,000 = 12,000
R  = 15,000 - 12,000 = 3,000
```

If the user supplies ₹1,000 of discretionary expenses, proposes no EMI
reduction, and states a feasible income increase of at least ₹3,000, the minimum
cost is ₹3,000/month. Equal-cost vertices include (expense cut ₹0, EMI cut ₹0,
income increase ₹3,000) and (expense cut ₹1,000, EMI cut ₹0, income increase
₹2,000), provided both pass any configured runway constraint. The profile is
not saved or modified.

## API and disclaimer

`POST /me/optimize` preserves existing top-level response fields and adds
`goal`, baseline/scenario projections, monthly differences, equal-cost options,
search/constraint information, assumptions, and limitations. New optional
request values are `horizon_months` and
`minimum_emergency_fund_runway_months`; both default to behavior that does not
impose a new runway requirement. Existing UI pages expose these options and
present the projection details.

Results depend on user inputs and explicit modeling assumptions. Mathematical
feasibility does not establish that an income increase, spending reduction, or
financing alternative is achievable or advisable. This is not financial
advice.
