<p align="center">
  <img src="web/public/icon.svg" width="96" height="96" alt="Romania Macro-Financial Dynamics icon">
</p>

<h1 align="center">Romania Macro-Financial Dynamics</h1>

<p align="center">Empirical stock-flow-consistent System Dynamics model of Romania's macro-financial system in an evidence-aware InfoClar interface.</p>

<p align="center">
  <img alt="Version 0.5.2a0" src="https://img.shields.io/badge/Version-0.5.2a0-4e9a06">
  <img alt="elementary OS planned" src="https://img.shields.io/badge/elementary_OS-Planned-64baff">
  <a href="LICENSE"><img alt="License MIT" src="https://img.shields.io/badge/License-MIT-blue"></a>
</p>

<p align="center">
  <a href="https://laurentiustaicu.github.io/romania-macro-financial-dynamics/"><img width="220" alt="Open Web App" src="https://img.shields.io/badge/Open_Web_App-Open-087F73?style=for-the-badge"></a>
  <img width="220" alt="Download Flatpak — Planned" src="https://img.shields.io/badge/Download_Flatpak-Planned-9ca3af?style=for-the-badge">
</p>

> **Alpha 0.5.2a0 — Government Repricing Ledger.** The project now contains an audited instrument-level public ledger and a prospectively frozen reconciliation contract for the government refinancing → effective debt-rate mechanism. Public sources identify useful instrument terms, but they still do not provide the full matched opening outstanding principal, realized repriced principal, reset dates and old/new effective rates required by the equation. The completeness gate therefore fails before estimation. **Government repricing remains DEFERRED; validated behavioural reference mechanisms remain 0; Alpha 0.6 remains NO-GO.**

## Web-first InfoClar product

InfoClar remains the single reference product surface and is publicly deployed at [https://laurentiustaicu.github.io/romania-macro-financial-dynamics/](https://laurentiustaicu.github.io/romania-macro-financial-dynamics/). The same adaptive Model / Theory-Learn / Dashboard / Auxiliary interface now exposes the government repricing ledger, the maturity-versus-refixing distinction, the frozen acceptance gates, source provenance and the negative identifiability result.

Behavioural simulation remains disabled. Native GTK/Granite/Flatpak development remains deferred until the web application and scientific contracts are mature at or near v1; the Flatpak CTA therefore remains visibly Planned and deliberately has no link.

## Alpha 0.5.2a0 — Government Repricing Ledger

### Prospective contract before assessment

The acceptance contract was committed before the ledger assessment in [`government_repricing_ledger_contract.json`](model/calibration_validation/government_repricing_ledger_contract.json). Its hard rules include:

- no synthetic allocation of missing principal;
- no substitution of redemption or maturity share for repricing share;
- no pairing of an aggregate refixing share with one auction yield;
- no use of issue size as same-date outstanding principal without explicit confirmation;
- no assumption that a new issuance refinances a specific maturity;
- no cross-currency aggregation without a matched valuation basis.

The frozen completeness thresholds require at least **95%** coverage of opening principal on the exact MoF portfolio boundary and at least **90%** coverage of realized repricing-event principal. Before a historical reconstruction may support CANDIDATE status, instrument/block balances must reconcile to published stock within **0.5%**, and published portfolio cost must be reproduced over at least three consecutive snapshots with maximum absolute error **0.10 pp** per snapshot and MAE **0.05 pp**. VALIDATED additionally requires a later prospectively reserved non-zero repricing period to pass without post-observation respecification.

### Public ledger built without synthetic filling

[`government_repricing_ledger_0.5.2a0.csv`](data/processed/government_repricing_ledger_0.5.2a0.csv) records seven auditable public rows from Ministry of Finance issuance terms and BVB-listed Ministry securities. The observed subset contains RON and EUR fixed-rate securities and preserves ISIN, coupon, maturity, issue value or announced amount where actually published, source date and provenance.

The ledger deliberately keeps the following fields missing when they are not publicly matched on the required boundary:

- opening outstanding principal at the reconciliation date;
- realized principal refinanced or contractually refixed;
- contractual refixing/reset dates for floating or indexed debt;
- old effective rate and new/reset effective rate on the same repriced principal.

Five BVB rows provide actual published issue values, totalling RON 923.2642 million across the observed RON examples and EUR 151.6391 million for the observed EUR example. These totals are **diagnostic issue-size sums only**. They are not interpreted as current portfolio stock or as coverage of the MoF debt boundary.

### Maturity is still not refixing

The newer MoF risk snapshot retained in the Alpha 0.5.2 provenance reports, as of 30 December 2024, about **10%** of debt maturing within one year versus **12%** refixing within one year, with ATM **6.9 years** and ATR **6.7 years**. For local-currency debt, the corresponding one-year shares are **17%** maturing and **15%** refixing. These are separate risk concepts and cannot be collapsed into one repricing parameter.

The existing MoF portfolio-average interest-rate reference path remains **3.8% (2019), 3.3% (2020), 3.1% (2021), 3.3% (2022), 4.2% (2023)**. It remains the historical reconstruction target under its own source definition rather than being replaced by a market yield.

Eurostat's 2025 apparent cost for Romania, **5.2%**, and its report that **53%** of Maastricht general-government debt was denominated in foreign currencies are retained only as external diagnostics. Eurostat defines apparent cost as accrual interest expenditure divided by average outstanding Maastricht debt; that general-government boundary is not substituted for the Ministry portfolio-cost boundary.

### Gate result

The public ledger has **0 rows** with same-date opening outstanding principal, **0 rows** with realized principal repriced and **0 rows** with a matched old/new effective-rate pair. Consequently the 95%/90% completeness gate cannot pass. Balance reconciliation, portfolio-cost reconstruction and parameter estimation are therefore **not opened**; running them would require exactly the synthetic allocations prohibited by the preregistration.

Final government mechanism disposition: **DEFERRED**.

See [`government_repricing_ledger_assessment.json`](model/calibration_validation/government_repricing_ledger_assessment.json), [`government_repricing_ledger_contract.json`](model/calibration_validation/government_repricing_ledger_contract.json), the [provenance record](data/provenance/government_repricing_ledger_0.5.2a0.json) and the [Alpha 0.5.2 final audit](docs/GOVERNMENT_REPRICING_LEDGER_AUDIT_0.5.2a0.md).

## Monetary confirmation remains frozen

Alpha 0.5.2 does not respecify the Alpha 0.5.1 household candidate. The selected one-parameter contemporaneous relation remains:

`lend[t] = lend[t-1] + beta × (policy[t] - policy[t-1])`

Observations from **2026-08 onward** remain prospectively reserved. They may not be used to revise the form before the first confirmation test containing genuinely new BNR policy-rate variation. The NFC result and its unopened final holdout are likewise unchanged.

## Scientific foundations

- **Alpha 0.1 — Foundation:** project constitution, registries, bilingual and methodological contracts, CI.
- **Alpha 0.2 — Accounting Spine:** auditable 2025 bilateral accounting and explicit unresolved-value semantics.
- **Alpha 0.2.1 — InfoClar Model Suite Design Standard v1.1:** common adaptive product grammar without forcing model-specific diagrams into one shape.
- **Alpha 0.3 — Dynamic Core:** executable stocks/flows/delays, dimensional consistency and conservation tests.
- **Alpha 0.4 — Empirical Dynamics:** evidence-linked behavioural candidates and explicit mechanism classifications.
- **Alpha 0.5.0 — Calibration & Validation:** first time-respecting cycle, closed with zero validated behavioural mechanisms.
- **Alpha 0.5.1 — Validation Recovery:** expanded official monetary and government-debt evidence without weakening the validation gate.

These foundations remain unchanged by Alpha 0.5.2.

## Current gate and next justified path

Validated behavioural reference mechanisms: **0**. Therefore **Alpha 0.6 Interactive Web Simulator remains NO-GO** and must not be reopened merely because the instrument ledger is richer.

The next prospectively justified behavioural path is **Prospective Monetary Confirmation**, but it becomes executable only when a genuinely new BNR policy-rate movement provides identifying variation for the already frozen household delta-policy form. On the government side, further work is justified only if an official/reproducible source supplies same-date outstanding principal and matched refinancing/reset rates across the material MoF portfolio boundary; repeating aggregate proxy fitting is not justified.

## Development

```bash
git clone https://github.com/LaurentiuStaicu/romania-macro-financial-dynamics.git
cd romania-macro-financial-dynamics
python -m pip install -e '.[test]'
python -m pytest
```

For local inspection, serve `web/` with a static HTTP server so `public/model-stage.json` can be fetched by the browser. Production publication is handled by the verified GitHub Pages workflow from `main`.

## Limitations

- no behavioural mechanism has yet passed all prospective validation gates;
- government instrument issue size is not equivalent to same-date outstanding principal;
- the public ledger does not expose the full floating/indexed reset structure or matched repricing principal/rates;
- Ministry portfolio cost and Eurostat Maastricht apparent cost have different boundaries;
- reserved future monetary observations remain unavailable for respecification before their first prospective confirmation use;
- some Accounting Spine bilateral cells remain unresolved;
- no forecast, causal effect, policy recommendation or behavioural simulation is claimed.

## License

Original software is licensed under the MIT License. Third-party datasets remain subject to their source licences and terms.
