# Scientific status

## Release status

Romanian Monetary Dynamics (RMD) v0.1.0 is the initial public scientific-core baseline. The version identifies a frozen software/model artifact. It does not imply that the behavioural closure of the model is empirically validated or ready for policy forecasting.

The current scientific stage is **Validation Recovery / Empirical Basis Expansion**.

## Current validation boundary

The canonical validation disposition records **0 validated reference behavioural mechanisms**.

The household housing-lending pass-through form remains a candidate. Structural-selection evidence supports a parsimonious response form, but the fresh final holdout contains no policy-rate movement and therefore cannot independently distinguish the candidate from persistence.

The NFC short-fixation lending pass-through candidates fail the preregistered structural-selection improvement gate before the final holdout is opened.

The government refinancing/effective-rate mechanism is deferred. At the present aggregation and public-data boundary, the required repricing parameter is not point-identifiable. The government repricing ledger fails the completeness gate before estimation, and no synthetic allocation is permitted to fill the missing instrument-level structure.

## Accounting empirical recovery

The frozen `v0.1.0` release retains its original incomplete Accounting Spine. In the current post-`v0.1.0` development state, the first-priority F3 debt-securities matrices have completed Accounting Empirical Recovery for the 2025 benchmark.

F3 stock at 2025-Q4 contains 24 direct `OBSERVED` cells, 11 exact `DERIVED` cells required by the RMD financial-sector identity `F = S12 - S121`, and one `NOT_APPLICABLE` X→X cell outside the Romanian national financial-accounts boundary. The 2025 F3 flow matrix contains 35 `DERIVED` cells because annual flows are exact sums of the four published quarterly transactions, plus one `NOT_APPLICABLE` X→X cell.

The F3 source vintage is retained immutably. Twenty out of twenty published QSA aggregate asset/liability controls and both preregistered X→G maturity controls reconcile within the 0.1 million RON tolerance. The unavailable W2 liability-side counterpart mirrors are recorded as unavailable publication coverage and are not treated as zeros.

This is **not** completion of the Accounting Spine. F2, F4, F8, F5, F6 and F7 remain unresolved or only partially controlled, so the full multi-instrument empirical state is still not ready for canonical system simulation.

## Model architecture boundary

The accounting spine is a hard constraint. Behavioural closure is not active in the canonical dynamic core. Candidate behavioural mechanisms may be admitted for calibration/testing only under their explicit contracts and may not drive the central reference simulation without justified parameters and validation.

A fresh prospective confirmation path is reserved from 2026-08 onward. Previously inspected evaluation data cannot later be reported as independent validation.

## What v0.1.0 does not claim

- a validated behavioural reference model;
- a calibrated macroeconomic forecast;
- causal identification from predictive fit alone;
- a validated government refinancing/repricing mechanism;
- a production policy simulator or policy recommendation system;
- an end-user application.

Future releases should update this file whenever a candidate mechanism changes status, a prospective validation gate is opened, or the central behavioural closure changes.

## System Dynamics maturity

RMD is currently an **accounting-constrained stock-flow-consistent dynamic model with a qualitative candidate feedback architecture**, not yet a complete endogenous System Dynamics model.

The Accounting / Stock-Flow Core is structurally implemented and guarded by stock identities, double-entry conservation, dimensional checks, explicit numerical integration and empirical-initialization gates. Empirical completion remains instrument-specific.

The Feedback Architecture contains candidate loops for government refinancing–interest, government issuance–yield, bank credit–balance-sheet, monetary–credit transmission and external FX–refinancing. All remain quantitatively inactive.

Behavioural Closure is inactive. A feedback loop may not be activated merely to make the model appear methodologically complete. Activation requires equation, units, evidence status, parameter source or estimation plan, identifiability assessment, endogenous/exogenous classification, polarity/path, delay specification where relevant, nonlinearity documentation where relevant, extreme-condition testing, sensitivity plan, validation gate, reference-mode linkage and preservation of accounting conservation.

Reference modes are registered in `model/dynamics/reference_modes.json`. Observed modes already exist for the policy rate and household/NFC lending rates; credit, government interest/refinancing/effective-rate and full multi-instrument financial-position modes remain partial or unresolved. Missing reference modes block integrated behavioural-closure validation, not the accounting core.

The executable conformity gate is `scripts/audit_system_dynamics_conformity.py`, backed by `model/dynamics/system_dynamics_conformity_gate.json`. The empirical-dynamics label `ACTIVATED` means admitted to calibration/validation only and must never be interpreted as quantitative feedback activation in the reference simulation.
