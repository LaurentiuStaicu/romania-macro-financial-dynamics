# Scientific status

## Release status

Romanian Monetary Dynamics (RMD) v0.1.0 is the initial public scientific-core baseline. The version identifies a frozen software/model artifact. It does not imply that the behavioural closure of the model is empirically validated or ready for policy forecasting.

The current scientific stage is **Validation Recovery / Empirical Basis Expansion**.

## Canonical modeling paradigm

**Romanian Monetary Dynamics (RMD) is an accounting-constrained, stock-flow-consistent dynamic model with a developing System Dynamics feedback architecture; behavioural closure remains inactive pending empirical identification and validation.**

The accounting/stock-flow core and its conservation rules are canonical constraints. Candidate feedback loops, delays, nonlinear behavioural equations, and reaction functions may become part of the endogenous System Dynamics structure only after their explicit evidence, units, parameterization, identifiability, extreme-condition, sensitivity, and validation gates are satisfied.

This paradigm statement is canonical for the project. RMD must not activate behavioural closure merely to appear to be a complete System Dynamics model, and it must not replace unresolved empirical structure with convenient synthetic coefficients or allocations. Any proposed paradigm-level change must be explicit, scientifically justified, documented in this file before integration, and must preserve accounting consistency unless a formally justified boundary change is approved.

## Current validation boundary

The canonical validation disposition records **0 validated reference behavioural mechanisms**.

The household housing-lending pass-through form remains a candidate. Structural-selection evidence supports a parsimonious response form, but the fresh final holdout contains no policy-rate movement and therefore cannot independently distinguish the candidate from persistence.

The NFC short-fixation lending pass-through candidates fail the preregistered structural-selection improvement gate before the final holdout is opened.

The government refinancing/effective-rate mechanism is deferred. At the present aggregation and public-data boundary, the required repricing parameter is not point-identifiable. The government repricing ledger fails the completeness gate before estimation, and no synthetic allocation is permitted to fill the missing instrument-level structure.

## Accounting empirical recovery

The frozen `v0.1.0` release retains its original incomplete Accounting Spine. In the current post-`v0.1.0` development state, the first-priority F3 debt-securities matrices have completed Accounting Empirical Recovery for the 2025 benchmark.

F3 stock at 2025-Q4 contains 24 direct `OBSERVED` cells, 11 exact `DERIVED` cells required by the RMD financial-sector identity `F = S12 - S121`, and one `NOT_APPLICABLE` X→X cell outside the Romanian national financial-accounts boundary. The 2025 F3 flow matrix contains 35 `DERIVED` cells because annual flows are exact sums of the four published quarterly transactions, plus one `NOT_APPLICABLE` X→X cell.

The F3 source vintage is retained immutably. Twenty out of twenty published QSA aggregate asset/liability controls and both preregistered X→G maturity controls reconcile within the 0.1 million RON tolerance. The unavailable W2 liability-side counterpart mirrors are recorded as unavailable publication coverage and are not treated as zeros.

The deposits-only **F2M component** has now also completed a separate materialization gate for the 2025 benchmark. The retained source vintage is the exact Phase A2 GitHub Actions artifact, stored losslessly for offline regeneration and checked against SHA-256 `efc2704388911d79c182d1ad0cffce32bc7728b1c9f7669714ec3a518ef2f227`. The materialized F2M stock matrix contains 10 direct `OBSERVED` cells, 13 exact `DERIVED` cells and 13 `NOT_APPLICABLE` cells; the 2025 flow matrix contains 23 exact `DERIVED` cells and 13 `NOT_APPLICABLE` cells. All available holder/issuer controls pass within the preregistered 0.1 million RON tolerance, and the independently controlled resident-holder→rest-of-world complements pass the Phase A2 W0/W1 identity gates.

This does **not** complete total F2. The F21 coverage audit finds published sector/total aggregates but no direct bilateral F21 cells for the tested RMD pairs in either QSA W2 asset-side or liability-side orientation. F21 therefore remains an unresolved holder-by-issuer allocation problem. The exact QSA instrument bridge `W1 F21(holder) = W1 F2(holder) − W1 F2M(holder)` has also been tested. QSA publishes Romania's total-economy W1 F2 and W1 F21 controls, but not the holder-specific W1 F2 series required for H/C/F/G/BNR, so the bridge remains blocked and no aggregate external-currency total may be distributed by shares or residual balancing. The ECB BPS / BOP-IIP sector-structure audit has now been completed. For Romania's external Other-Investment F2, BPS publishes S121, S12T, S13 and S1P and also the intermediate split `S1P = S12M + S1V`; this permits a structurally exact candidate external financial-sector grouping `F = S12T + S12M`. However, the remaining `S1V = S11 + S1M` split is not published for the tested Romania F2 series, so non-financial corporations and households/NPISH cannot be separated without invention. The independent Eurostat `bop_iip6_q` audit has now recovered direct 2025-Q4 observations for both `S11` non-financial corporations and `S1M` households/NPISH for Romania's external Other-Investment F2. In national currency, S11 is 8,898 million RON and S1M is 10,701 million RON; their 19,599 million RON sum differs from published S1V (19,598 million RON) by 1 million RON, within the source-precision envelope implied by integer-million national-currency transmission. The H/C sector-detail blocker is therefore resolved at publication precision. The subsequent BPM6-to-ESA concept bridge identifies the exact remaining public-data boundary. Reserve-assets currency and deposits (`FA__R__F2`) are directly published for BNR at 90,278 million RON, but Eurostat `bop_iip6_q` does not disseminate a Direct-Investment currency-and-deposits subinstrument (`FA__D__F2`): the requested item has zero members in the dataset constraint. The broader Direct-Investment debt item (`FA__D__FL`) is composite and cannot substitute for F2. Consequently, Other-Investment F2 plus Reserve-Assets F2 is only a known-components subtotal (169,405 million RON), 2,996.07 million RON below QSA W1 total F2. That gap is left unresolved rather than allocated. F21 and total F2 remain incomplete; Accounting Empirical Recovery now advances to F4 while preserving an explicit reopen condition for F21 if a definitionally comparable Direct-Investment F2 breakdown becomes available. F2M must not be relabelled as F2, and the canonical total-F2 matrix in `benchmark_2025.json` remains unchanged. F4 recovery has now entered a separate source-coverage stage: exact QSA probing resolves 12 of 35 in-boundary stock cells and 12 of 35 2025-flow cells, with zero maturity conflicts and complete W0 row/column aggregate controls but 23 unresolved bilateral cells per measure. The missing structure is concentrated around the composite financial sector F, BNR and rest-of-world holders. BNR's aggregate F4 stock is 6.1 million RON in assets and zero in liabilities throughout 2025, with zero aggregate F4 transactions; this is retained as a candidate stock-only structural constraint, not converted into bilateral flow zeros. The next gate is an exact aggregate-complement/rank audit before any F4 materialization. F8, F5, F6 and F7 remain unresolved or only partially controlled, so the full multi-instrument empirical state is still not ready for canonical system simulation.

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
