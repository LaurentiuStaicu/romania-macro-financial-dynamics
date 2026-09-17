<p align="center">
  <img src="web/public/icon.svg" width="96" height="96" alt="Romania Macro-Financial Dynamics icon">
</p>

<h1 align="center">Romania Macro-Financial Dynamics</h1>

<p align="center"><img alt="Version 0.5.1a0" src="https://img.shields.io/badge/version-0.5.1a0-4e9a06"></p>

<p align="center">
  Empirical stock-flow-consistent <strong>System Dynamics</strong> model of Romania's macro-financial system with an implemented <strong>InfoClar EN/RO web reference interface</strong>.
</p>

<p align="center">
  <img alt="Development stage: alpha" src="https://img.shields.io/badge/stage-alpha-e5a50a">
  <img alt="InfoClar web: reference interface" src="https://img.shields.io/badge/InfoClar_Web-reference_interface-4a90d9">
  <img alt="Behavioural simulator: NO-GO" src="https://img.shields.io/badge/behavioural_simulator-NO--GO-e5a50a">
  <img alt="Languages: EN and RO" src="https://img.shields.io/badge/languages-EN_%2F_RO-0e9a83">
  <img alt="elementary OS Flatpak: deferred near v1" src="https://img.shields.io/badge/Flatpak-deferred_near_v1-64baff">
  <a href="LICENSE"><img alt="Code license: MIT" src="https://img.shields.io/badge/code_license-MIT-blue"></a>
</p>

> **Alpha 0.5.1a0 — Validation Recovery / Empirical Basis Expansion.** The empirical basis is now much longer and prospectively partitioned. One parsimonious household monetary-pass-through form passed structural selection, but its fresh holdout contained no policy-rate changes and therefore could not outperform persistence. NFC forms failed before holdout. Government repricing remains boundary-unidentified at the aggregate level. **Validated behavioural reference mechanisms remain 0; Alpha 0.6 remains NO-GO.**

## Web-first InfoClar product

InfoClar is the primary product surface through scientific maturation to v1. The same browser application under [`web/`](web/) continues to accumulate the defensible model, Theory/Learn, empirical Dashboard and Auxiliary evidence/limitations surface.

The central view remains specific to the Romanian macro-financial stock-flow system (`H / C / F / G / X / BNR`). The current interface is deliberately read-only for behavioural simulation. It now exposes the longer BIS/ECB monetary vintage, prospective data roles, structural-selection and holdout outcomes, government debt maturity-vs-refixing distinctions and the explicit Alpha 0.6 gate.

Native GTK/Granite/Flatpak development remains deferred until the web application is mature at or near v1. No separate application or Advanced mode is introduced.

## Alpha 0.5.x validation recovery

### Monetary transmission — longer official data

The reproducible recovery workflow captures a frozen official-source vintage:

- BIS central-bank policy rate for Romania (`M.RO`), source origin National Bank of Romania: **260 monthly observations, 2005-01..2026-08**;
- ECB MIR household/NPISH RON new-business house-purchase rate: **108 observations, 2017-08..2026-07**;
- ECB MIR NFC RON new-business rate with variable / initial fixation up to one year: **108 observations, 2017-08..2026-07**.

The alternative NFC total series contains official missing observations and is not imputed.

Roles were frozen before recovery estimation: calibration **2017-08..2022-12**, structural selection **2023-01..2025-01**, fresh final evaluation **2025-02..2025-11**. The previously inspected Nov-2024..Jan-2025 Alpha 0.5 holdout is permanently reclassified as structural-selection information. Observations from 2026-08 onward are reserved prospectively for later confirmation as they become available for all targets.

### Household lending-rate pass-through

The only form that passes every preregistered structural-selection gate is the one-parameter contemporaneous change relation:

`lend[t] = lend[t-1] + beta × (policy[t] - policy[t-1])`

Across 25 expanding origins, beta remains approximately **0.476–0.501**. Structural-selection RMSE is **0.1687 pp**, versus **0.1835 pp** for persistence, an improvement of about **8.1%**.

The model form was frozen before opening the fresh 10-month holdout. That holdout contains **zero policy-rate changes**, so the candidate becomes exactly persistence: both have RMSE **0.05727 pp**. It therefore fails the preregistered independent-evaluation improvement gate.

Disposition: **CANDIDATE — not VALIDATED**.

### NFC lending-rate pass-through

None of the four preregistered parsimonious forms passes structural selection. The direct contemporaneous delta-policy form has RMSE **0.2316 pp**, versus **0.2166 pp** for persistence. The NFC final holdout is intentionally not opened.

Disposition: **CANDIDATE**; the tested forms fail, while the broader existence of monetary transmission is not declared rejected.

### Government refinancing → effective debt rate

Official MoF evidence now distinguishes debt maturity from rate refixing and provides portfolio-average debt costs, ATM/ATR indicators and maturity-specific auction yields. These observables are useful but not interchangeable.

For October 2024, the MoF reports roughly **10%** of debt maturing within one year versus **11%** refixing within one year, with ATM **7.0 years** and ATR **6.9 years**. The published portfolio cost and individual auction yields also refer to different instrument/currency boundaries.

Therefore redemption/debt, a strategic target, an aggregate refixing share or a single auction yield is not substituted for the model's repricing share `m`. Valid estimation requires an instrument × currency × fixed/floating repricing ledger with matched principal and old/new effective rates.

Disposition: **DEFERRED**.

See [Alpha 0.5.x final audit](docs/VALIDATION_RECOVERY_AUDIT_0.5.1a0.md), [`validation_recovery_selection.json`](model/calibration_validation/validation_recovery_selection.json), [`validation_recovery_holdout.json`](model/calibration_validation/validation_recovery_holdout.json), [`validation_recovery_disposition.json`](model/calibration_validation/validation_recovery_disposition.json) and [`government_refinancing_recovery_assessment.json`](model/calibration_validation/government_refinancing_recovery_assessment.json).

## Scientific foundations

- **Alpha 0.2 — Accounting Spine:** auditable 2025 holder-by-issuer accounting, provenance, B9F/reconciliation and explicit unresolved-value semantics.
- **Alpha 0.3 — Dynamic Core:** executable stocks/flows/delays, year-based time semantics, double-entry conservation and structural verification.
- **Alpha 0.4 — Empirical Dynamics:** evidence-linked behavioural candidates with explicit activation/defer/rejection contracts.
- **Alpha 0.5 — Calibration & Validation:** first time-respecting validation cycle, correctly closed with zero validated mechanisms.

These remain unchanged foundations for the recovery work.

## Current gate and next path

Validated behavioural reference mechanisms: **0**.

Therefore **Alpha 0.6 Interactive Web Simulator remains NO-GO**. InfoClar itself remains GO as the primary read-only structural/empirical/theory web product.

The next justified empirical work remains inside the Alpha 0.5.x family:

1. preserve future MIR observations from **2026-08 onward** for a first prospective confirmation of the frozen household change-pass-through form when a new policy-rate movement occurs;
2. build the government instrument/currency/fixed-floating repricing ledger and reconcile it to published MoF portfolio costs.

Only a prospectively successful confirmation or a definitionally matched validated debt-repricing mechanism can reopen the Alpha 0.6 simulator decision.

## Development

```bash
git clone https://github.com/LaurentiuStaicu/romania-macro-financial-dynamics.git
cd romania-macro-financial-dynamics
python -m pip install -e '.[test]'
python -m pytest
```

For the current InfoClar alpha, serve `web/` with a local static HTTP server so `public/model-stage.json` can be fetched by the browser.

## Limitations

- no behavioural mechanism has yet passed all prospective validation gates;
- the fresh household holdout contains no policy-rate event and cannot independently identify pass-through;
- the NFC holdout remains unopened after structural-selection failure;
- MIR new-business rates are flow-contract rates, not effective rates on outstanding loan stocks;
- government maturity, refixing, portfolio cost and issuance yields do not share a single aggregation boundary;
- some Accounting Spine bilateral cells remain unresolved;
- no forecast, causal effect, policy recommendation or behavioural simulation is claimed.

## License

Original software is licensed under the MIT License. Third-party datasets remain subject to their source licences and terms.
