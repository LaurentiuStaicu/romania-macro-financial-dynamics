# Alpha 0.5.1a0 — Validation Recovery / Empirical Basis Expansion final audit

Date: 2026-09-17

## Exit verdict

**PASS as a completed recovery milestone; Alpha 0.6 behavioural simulator remains NO-GO.**

The empirical basis is materially stronger than in Alpha 0.5, but zero behavioural reference mechanisms satisfy every prospective validation gate. This is an accepted negative result, not a reason to weaken the gates.

## Invariants

Unchanged:

- Alpha 0.2 Accounting Spine and all missing-data semantics;
- Alpha 0.3 Dynamic Core, double-entry conservation, time and dimensional contracts;
- Alpha 0.4 evidence history and mechanism classifications as historical state;
- InfoClar Model Suite Design Standard v1.1;
- Web-first product direction; no native/Flatpak implementation;
- no missing observation is imputed or converted to zero;
- no final holdout is used to select or respecify a model.

## Priority 1 — monetary transmission recovery

### New official-source vintage

A reproducible GitHub Actions fetch captures and hashes the official-source vintage.

- BIS central-bank policy-rate series for Romania (`M.RO`), sourced from the National Bank of Romania: **260 monthly observations, 2005-01..2026-08**.
- ECB MIR household/NPISH RON new-business house-purchase rate (`MIR.M.RO.B.A2C.A.R.A.2250.RON.N`): **108 monthly observations, 2017-08..2026-07**.
- ECB MIR NFC RON new-business rate, variable / initial fixation up to one year (`MIR.M.RO.B.A2A.F.R.A.2240.RON.N`): **108 monthly observations, 2017-08..2026-07**.
- The alternative NFC total series is retained only as available observations because the official series contains many missing months; no interpolation is performed.

Canonical files live in `data/raw/validation_recovery/`; source request metadata, hashes and HTTP metadata are in `fetch_manifest.json`.

### Prospective role split

Frozen before Alpha 0.5.x estimation:

- calibration: **2017-08..2022-12 (65 months)**;
- structural selection: **2023-01..2025-01 (25 months)**;
- fresh final evaluation: **2025-02..2025-11 (10 months)**;
- observations from **2025-12..2026-07** are diagnostic-only because their values were seen during source-coverage inspection;
- observations from **2026-08 onward** are prospectively reserved for future confirmation as they become available for all targets.

The Alpha 0.5 holdout Nov-2024..Jan-2025 is permanently reclassified as structural-selection information and is never described again as independent validation.

### Preregistered parsimonious candidates

Mandatory baselines:

1. persistence;
2. constant policy spread.

Candidates, all with no more than two estimated parameters:

1. contemporaneous change pass-through: `lend[t] = lend[t-1] + beta * Δpolicy[t]`;
2. one-month-lag change pass-through;
3. mean-spread anchored partial adjustment;
4. static affine policy-level comparator.

No inflation, FX, activity, bank-balance-sheet or other control is added to improve fit.

### Structural-selection result — households

The contemporaneous one-parameter change form is the only candidate that passes every preregistered structural-selection gate.

- 20 non-zero policy-rate changes exist before the selection end;
- calibration beta: **0.47647**;
- expanding-origin beta range: **0.47647–0.50145**, domain-consistent in all origins;
- candidate RMSE: **0.16870 pp**;
- persistence RMSE: **0.18352 pp**;
- RMSE improvement vs persistence: **8.08%**;
- 25 expanding-origin observations.

The model form and final-evaluation authorization were frozen before the holdout was opened.

### Fresh final evaluation — households

The first-and-only fresh evaluation contains **10 months (2025-02..2025-11)** but **zero policy-rate changes**.

Frozen beta fitted through 2025-01: **0.49746**.

Because `Δpolicy = 0` for every holdout observation, the candidate is exactly the persistence prediction:

- candidate RMSE: **0.05727 pp**;
- persistence RMSE: **0.05727 pp**;
- improvement vs persistence: **0%**;
- candidate MAE: **0.046 pp**;
- absolute bias: **0.020 pp**.

The candidate therefore fails the preregistered requirement to beat each simple baseline. ±10% beta sensitivity is numerically unchanged in this holdout because the driver is zero; this is non-informative, not evidence of robustness.

**Final mechanism verdict: CANDIDATE.**

The result does not reject the existence of monetary transmission. It rejects a claim that this mechanism has been independently validated for reference predictive simulation by this cycle.

### Structural-selection result — NFC

No preregistered candidate passes every structural-selection gate.

For the strongest direct contemporaneous delta-policy form:

- candidate RMSE: **0.23159 pp**;
- persistence RMSE: **0.21663 pp**;
- candidate is approximately **6.9% worse** than persistence on RMSE.

The NFC final holdout is therefore **not opened**.

**Final mechanism verdict: CANDIDATE.** The tested parsimonious forms fail; monetary transmission as a broader mechanism is not declared rejected.

## Priority 2 — government refinancing → effective debt rate

The official evidence base is materially expanded and reconciled:

- MoF portfolio average interest-rate observations are recorded for 2019–2023;
- MoF explicitly distinguishes **refinancing risk** (debt maturing / ATM) from **interest-rate risk** (debt refixing / ATR);
- December-2024 investor material reports realized 2023 and October-2024 maturity/refixing indicators;
- 2025 public-debt flash reports provide domestic auction yields by residual maturity;
- budget execution provides interest-expenditure flows.

For October 2024, for example, MoF reports approximately:

- debt maturing within one year: **10%**;
- debt refixing within one year: **11%**;
- ATM: **7.0 years**;
- ATR: **6.9 years**.

These are not interchangeable. The aggregate Alpha 0.4 equation requires the fraction of the exact represented debt stock whose effective rate is replaced/reset in the period and a matched new rate for that same principal. The published refixing share combines maturity/refinancing and contractual resets; domestic auction yields apply only to particular issued securities and maturities, while the stock also contains foreign-currency bonds, EU/IFI loans and other instruments.

Consequently:

- redemption/debt is not used as `m`;
- a strategy target is not used as `m`;
- the realized aggregate refixing share is not paired mechanically with one marginal auction yield;
- consolidated budget interest expenditure is not divided by a mismatched stock to manufacture an effective rate.

**Final mechanism verdict: DEFERRED.**

Recovery requires an instrument × currency × fixed/floating repricing ledger with matched principal, reset/maturity date, old rate, new rate and interest-cost definition. The mechanism can be activated only if that ledger reconstructs published portfolio-cost measures within a declared tolerance without synthetic allocation.

## Other Alpha 0.4 mechanisms

No other candidate/deferred mechanism is opened in this cycle. Doing so after observing the priority results would create an opportunistic search for a passing mechanism rather than a prospective validation program. Every future mechanism requires a fresh preregistered data/selection cycle.

## Product result — InfoClar

The existing Web InfoClar application remains the reference product and remains read-only for behavioural simulation. It now exposes:

- the expanded BIS/ECB empirical coverage;
- the household selection signal and failed fresh holdout;
- the NFC pre-holdout failure;
- the government maturity/refixing boundary distinction;
- updated sources, limitations and mechanism verdicts;
- the explicit Alpha 0.6 NO-GO gate.

The stock-flow/sector view, contextual Theory/Learn, empirical Dashboard and Auxiliary surface remain the same product. No Advanced mode, separate application or native/Flatpak implementation is introduced.

## Final scientific disposition

- household monetary pass-through: **CANDIDATE**;
- NFC monetary pass-through: **CANDIDATE**;
- government refinancing → effective rate: **DEFERRED**;
- newly VALIDATED mechanisms: **0**;
- Alpha 0.6 behavioural simulator gate: **NO-GO**.

## Next empirical path

The next justified large stage is still inside the Alpha 0.5.x recovery family rather than Alpha 0.6:

1. **Prospective Monetary Confirmation:** preserve observations from 2026-08 onward and wait for a fresh policy-rate movement/cycle before first formal confirmation of the frozen household delta-policy form. The model must not be revised using those future observations before their confirmation test.
2. **Government Repricing Ledger:** build instrument/currency/fixed-floating matched repricing data and reconcile them to the MoF portfolio average-cost path.

Only a prospectively successful confirmation or a definitionally matched validated debt-repricing mechanism can reopen the Alpha 0.6 simulator decision.
