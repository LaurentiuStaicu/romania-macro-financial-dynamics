# Alpha 0.3.0a0 — Dynamic Core exit audit

Date: 2026-09-17

## Audit question

Can the project now execute a structurally valid stock/flow/delay substrate that is constrained by the integrated Accounting Spine and presented through the unchanged InfoClar Model Suite v1.1 architecture, without prematurely activating empirical behavioural closure?

## Result

**Candidate PASS pending CI.**

## 1. Foundation preservation

### Accounting Spine — PASS

The Alpha 0.3 branch does not modify files under `model/accounting/`. Dynamic initialization treats the Accounting Spine as a hard constraint. `TBD` and source-only cells remain non-numeric and cannot initialize simulation state.

### InfoClar Model Suite v1.1 — PASS

The Alpha 0.3 branch does not modify the shared `workspace_contract.json` or `design_tokens.json`. Stage-specific bindings are added in `model/dynamics/presentation_contract.json`, which inherits the v1.1 contract rather than redefining it.

### User draft/schema — PASS

The user's exploratory schema/draft is not included as a repository artifact. The stage contract records this explicitly.

## 2. Dynamic state representation — PASS

Canonical dynamic financial state is indexed by:

`holder × issuer × instrument`

A represented position is simultaneously a holder asset and equal issuer liability. Balance-sheet aggregates are derived from this one representation. This structurally enforces double-entry conservation instead of correcting it after simulation.

## 3. Stock-flow identity — PASS

Both period-amount and rate-based update forms implement:

`closing = opening + transactions + revaluations + other changes`

with explicit time conversion for rates.

## 4. Time and dimensional contract — PASS

- canonical time unit: year;
- default reference step: 0.25 year;
- stocks/period changes: million RON;
- rates: million RON/year;
- delays: years;
- ratios: dimensionless.

`model/dynamics/unit_registry.json` records the dimensional signatures and equation checks.

## 5. Empirical initialization safety — PASS

Numeric initialization requires exactly one complete 6×6 stock matrix for one instrument with only finite `OBSERVED`, `DERIVED` or explicit `NOT_APPLICABLE` cells.

The bridge rejects:

- unresolved cells;
- source-series-only cells;
- missing addresses;
- duplicate addresses;
- mixed instruments;
- non-stock cells;
- non-finite values.

## 6. Delay primitive — PASS

A first-order delay primitive is executable and dimensionally explicit. Concrete economic delay parameters remain `TBD` and inactive.

## 7. Behavioural closure separation — PASS

Sovereign, credit, monetary and external candidate loops are documented as `BEHAVIOURAL_CANDIDATE` and `quantitatively_active = false`.

Alpha 0.3 does not activate consumption, investment, credit, fiscal, monetary-policy, default/risk, FX or refinancing response equations.

## 8. Central diagram contract — PASS

The primary scientific view is explicitly `macro_financial_stock_flow_network`, not a generic graph.

It contains:

- institutional-sector nodes H/C/F/G/X/BNR;
- financial-position stock edges by instrument;
- transaction-flow overlays;
- revaluation/other-change overlays;
- optional candidate-feedback overlay.

Feedback candidates are off by default, visually status-labelled and prohibited from looking empirically confirmed.

## 9. InfoClar panel binding — PASS

### Theory / Learn

Selection contexts map sectors, positions, transactions, delays and feedback candidates to definitions, accounting/dynamic roles, equations, units, provenance, scientific status and limitations.

### Dashboard

Priority order is:

1. empirical benchmark and unresolved coverage;
2. accounting/reconciliation status;
3. Dynamic Core structural status.

This preserves empirical evidence as the primary dashboard layer.

### Auxiliary

The panel contains selection details, exact source identifiers, structural-verification results and limitations, without duplicating Theory/Learn prose.

## 10. Scientific-core/UI separation — PASS

`src/romania_macro_financial_dynamics/presentation.py` provides canonical graph and balance-sheet dashboard payload builders. A future browser/native UI therefore consumes scientific outputs instead of independently reconstructing accounting identities.

## 11. Structural verification suite — PASS AS TEST COVERAGE, PENDING CI EXECUTION

Tests cover:

- financial stock identities;
- rate × time conversion;
- double-entry conservation;
- boundary equivalence with Accounting Spine;
- zero-flow extreme condition;
- very large finite values;
- incomplete empirical initialization;
- duplicate empirical addresses;
- delay steady state;
- invalid delay/time parameters;
- integration-error convergence when halving dt;
- dimensional-registry consistency;
- behavioural-candidate inactivity;
- macro-financial central-diagram semantics;
- Theory/Dashboard/Auxiliary bindings;
- InfoClar/Accounting foundation inheritance.

## 12. Methodological consistency — PASS

The Dynamic Core follows two relevant methodological principles:

1. empirical SFC structures should be grounded in the country-specific sectoral balance sheets and Flow-of-Funds structure rather than imposed from a generic model topology;
2. System Dynamics structural verification should include dimensional consistency, conservation/structure checks, extreme conditions and integration-error tests before behavioural reproduction or forecasting claims.

## Exit gate

Alpha 0.3 may be merged when CI is green and the post-merge CI remains green.

The next stage, Alpha 0.4 Empirical Dynamics, is qualitatively different: choosing and activating behavioural equations changes substantive model behaviour. That is the next gate where a real scientific-direction decision is appropriate.
