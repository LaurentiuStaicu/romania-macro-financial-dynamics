# Alpha 0.3.0a0 — Dynamic Core

Date: 2026-09-17

## Purpose

Alpha 0.3 converts the validated Accounting Spine into an executable **structural** System Dynamics core. It implements stock accumulation, double-entry conservation, time-base semantics, a reusable first-order delay primitive, dimensional contracts, a model-specific InfoClar presentation contract and structural/extreme-condition tests.

It deliberately does **not** choose or calibrate behavioural response functions. Those belong to Alpha 0.4 Empirical Dynamics.

## 1. Time base

Canonical simulation time unit: **year**.

Default integration step: **0.25 year (one quarter)**, because quarterly is the preferred empirical frequency when definitions remain compatible.

This convention keeps rates dimensionally explicit:

`million RON/year × years = million RON`

Observed quarterly transaction amounts are not automatically treated as annual rates. A conversion to a rate requires division by the represented period length and must be recorded as a data transformation.

## 2. Canonical dynamic financial stock

A bilateral position is indexed by:

`holder × issuer × instrument`

with sectors:

`H, C, F, G, X, BNR`

and instruments:

`F3, F2, F4, F8, F5, F6, F7`.

The position is represented **once**. The same numeric amount is:

- an asset of the holder;
- an equal liability of the issuer.

This means financial double-entry conservation is structural rather than a post-hoc balancing operation.

For a complete represented boundary:

`Σ sector net financial worth = 0`

up to floating-point tolerance.

## 3. Stock identity

For period amounts:

`Closing = Opening + Transactions + Revaluations + Other changes`

For rate-based simulation:

`Closing = Opening + (transaction_rate + revaluation_rate + other_change_rate) × dt`

All terms must be finite. The engine does not silently repair an invalid or non-finite result.

## 4. Guarded bridge from Accounting Spine to dynamics

Raw Accounting Spine matrices are not automatically numeric simulation states.

A matrix may initialize dynamics only when:

- the complete 6×6 address space is present exactly once;
- every relevant cell is `OBSERVED`, `DERIVED` or `NOT_APPLICABLE`;
- every observed/derived value is finite;
- `NOT_APPLICABLE` is an explicit structural zero.

Any `TBD` or `SOURCE_SERIES_IDENTIFIED` cell causes a hard initialization failure. Duplicate matrix addresses are also rejected so later rows cannot silently overwrite earlier observations. This prevents both `missing = 0` and silent duplicate-resolution shortcuts.

## 5. Sector balance-sheet auxiliaries

From the single bilateral position representation, the engine derives:

- sector financial assets;
- sector financial liabilities;
- sector net financial worth;
- system net financial worth.

These are auxiliaries, not separately updated stocks, so they cannot drift away from the underlying bilateral positions.

## 6. Delay primitive

Alpha 0.3 includes a reusable first-order delay:

`d(delay_state)/dt = (input - delay_state) / tau`

where `tau > 0` and has unit years.

Concrete economic delays — monetary transmission, credit adjustment, maturity/refinancing, portfolio reallocation, risk recognition or FX pass-through — remain disabled until their mechanism, evidence, unit and parameter source are established.

## 7. Feedback skeleton

`model/dynamics/feedback_registry.json` records candidate feedback structures for:

- government refinancing and interest costs;
- government issuance and sovereign yields;
- bank credit and balance-sheet/risk feedback;
- monetary-credit transmission;
- external FX/refinancing pressure.

Every loop is explicitly `BEHAVIOURAL_CANDIDATE` and `quantitatively_active = false`.

A registered loop is therefore a research hypothesis, not a claim that the causal sign is stable, the mechanism is material, or the loop has predictive validity.

## 8. Behavioural closure boundary

Alpha 0.3 forbids silent introduction of functions for:

- consumption;
- investment;
- credit demand/supply;
- fiscal reaction;
- monetary-policy reaction;
- default/risk;
- exchange rate;
- refinancing.

Activation in Alpha 0.4+ requires at least:

- explicit equation;
- dimensional consistency;
- evidence status;
- parameter source or estimation plan;
- extreme-condition test;
- sensitivity plan.

## 9. Dimensional contract

`model/dynamics/unit_registry.json` is the machine-readable dimensional registry for Alpha 0.3. It makes the following distinctions explicit:

- stocks and period changes: `million_RON`;
- flow/change rates: `million_RON_per_year`;
- time step and delay constants: `year`;
- ratios: dimensionless.

The period stock identity and rate-based stock identity are recorded as dimensionally consistent. A later behavioural equation cannot be activated unless additive terms share compatible dimensions and every parameter has an explicit unit or dimensionless status.

## 10. InfoClar presentation contract

Alpha 0.3 preserves the InfoClar Model Suite v1.1 four-area workspace **without changing the v1.1 foundation contract**.

The stage-specific binding is in `model/dynamics/presentation_contract.json`.

### Central model panel

The primary view is explicitly:

`macro_financial_stock_flow_network`

It is **not** a generic node-link diagram. Its scientific objects are the six institutional sectors and the bilateral financial positions/flows between them.

Display layers are:

1. financial stock positions by instrument;
2. financial transactions;
3. revaluations and other changes;
4. optional candidate-feedback overlay.

Candidate feedbacks are off by default, dashed/status-labelled when shown, and may never visually resemble confirmed empirical links or alter numerical results in Alpha 0.3.

The future UI consumes canonical graph/dashboard payloads from `src/romania_macro_financial_dynamics/presentation.py` rather than reimplementing the accounting logic in the browser.

### Theory / Learn

Theory remains contextual. Sector, position, transaction, delay and feedback-candidate selection each map to specific definitions, identities, unit explanations, provenance, evidence status and limitations.

### Dashboard

Indicator priority is:

1. empirical benchmark and unresolved bilateral coverage;
2. accounting/reconciliation status;
3. Dynamic Core structural status.

This prevents new model-engine metadata from displacing the still more important empirical/accounting evidence layer.

### Auxiliary panel

The auxiliary surface is reserved for exact selection details, source identifiers, structural-verification results and limitations. It does not duplicate explanatory Theory/Learn prose.

The user's exploratory schema/draft is not a repository artifact and is not included in this stage.

## 11. Structural tests

The Dynamic Core test suite checks:

- stock identity;
- rate × time dimensional conversion;
- double-entry conservation;
- boundary equivalence with the Accounting Spine;
- zero-flow extreme condition;
- large finite-value extreme condition;
- rejection of incomplete empirical initialization;
- rejection of duplicate empirical addresses;
- delay steady state;
- invalid delay/time-step rejection;
- integration-error convergence when the Euler step is halved;
- inactive status of behavioural feedback candidates;
- unit-registry consistency;
- macro-financial central-diagram semantics;
- InfoClar Theory/Dashboard/Auxiliary bindings.

This follows established System Dynamics practice in which dimensional consistency, physical conservation, extreme conditions and integration-error tests are structural verification gates.

## 12. Methodological anchors

The Dynamic Core is intentionally built from the country-specific Accounting Spine rather than from a generic theoretical topology. This follows the empirical SFC design principle that a country model should start from the specific sectoral balance sheets and Flow-of-Funds structure relevant to the research question.

Methodological references used for this gate:

- Gennaro Zezza & Francesco Zezza, *On the Design of Empirical Stock-Flow-Consistent Models*, Levy Economics Institute Working Paper 919 (2019): https://www.levyinstitute.org/publications/on-the-design-of-empirical-stock-flow-consistent-models/
- System Dynamics validation practice summarized from Sterman/Forrester-Senge tests, including dimensional consistency, extreme conditions and integration error: https://proceedings.systemdynamics.org/2005/proceed/papers/WAKEL201.pdf

These references justify structural verification practice; they do not provide or validate the behavioural equations that remain deferred to Alpha 0.4.

## 13. Exit interpretation

Alpha 0.3 is complete when CI verifies these structural and presentation contracts. Completion means:

- the model has an executable stock/flow/delay substrate;
- the substrate preserves the Accounting Spine;
- InfoClar v1.1 remains the unchanged product foundation;
- the central representation remains macro-financial/stock-flow specific;
- the time base and units are explicit;
- candidate feedbacks are visible but cannot affect results accidentally;
- empirical indicators, Theory/Learn and Auxiliary have canonical stage bindings;
- the project is ready for the next genuinely empirical choice: which behavioural relationships are admitted and how they are estimated/validated.

It does **not** mean the project can yet forecast Romania or evaluate policy interventions.
