# Alpha 0.3.0a0 — Dynamic Core

Date: 2026-09-17

## Purpose

Alpha 0.3 converts the validated Accounting Spine into an executable **structural** System Dynamics core. It implements stock accumulation, double-entry conservation, time-base semantics, a reusable first-order delay primitive, dimensional contracts and structural/extreme-condition tests.

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

- the complete 6×6 address space is present;
- every relevant cell is `OBSERVED`, `DERIVED` or `NOT_APPLICABLE`;
- every observed/derived value is finite;
- `NOT_APPLICABLE` is an explicit structural zero.

Any `TBD` or `SOURCE_SERIES_IDENTIFIED` cell causes a hard initialization failure. This prevents the common but scientifically invalid shortcut `missing = 0`.

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

## 9. Structural tests

The Dynamic Core test suite checks:

- stock identity;
- rate × time dimensional conversion;
- double-entry conservation;
- zero-flow extreme condition;
- large finite-value extreme condition;
- rejection of incomplete empirical initialization;
- delay steady state;
- invalid delay/time-step rejection;
- integration-error convergence when the Euler step is halved;
- inactive status of behavioural feedback candidates.

This follows established System Dynamics practice in which dimensional consistency, extreme conditions and integration-error tests are part of structural model verification.

## 10. Exit interpretation

Alpha 0.3 is complete when CI verifies these structural contracts. Completion means:

- the model has an executable stock/flow/delay substrate;
- the substrate preserves the Accounting Spine;
- the time base and units are explicit;
- candidate feedbacks are visible but cannot affect results accidentally;
- the project is ready for the next genuinely empirical choice: which behavioural relationships are admitted and how they are estimated/validated.

It does **not** mean the project can yet forecast Romania or evaluate policy interventions.
