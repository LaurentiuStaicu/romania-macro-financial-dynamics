<p align="center">
  <img src="web/public/icon.svg" width="96" height="96" alt="Romania Macro-Financial Dynamics icon">
</p>

<h1 align="center">Romania Macro-Financial Dynamics</h1>

<p align="center"><img alt="Version 0.5.0a0" src="https://img.shields.io/badge/version-0.5.0a0-4e9a06"></p>

<p align="center">
  Empirical stock-flow-consistent <strong>System Dynamics</strong> model of Romania's macro-financial system with an implemented <strong>InfoClar EN/RO web reference interface</strong>.
</p>

<p align="center">
  <img alt="Development stage: alpha" src="https://img.shields.io/badge/stage-alpha-e5a50a">
  <img alt="InfoClar web: reference interface" src="https://img.shields.io/badge/InfoClar_Web-reference_interface-4a90d9">
  <img alt="Behavioural simulator: validation gated" src="https://img.shields.io/badge/behavioural_simulator-validation_gated-e5a50a">
  <img alt="Languages: EN and RO" src="https://img.shields.io/badge/languages-EN_%2F_RO-0e9a83">
  <img alt="elementary OS Flatpak: deferred near v1" src="https://img.shields.io/badge/Flatpak-deferred_near_v1-64baff">
  <a href="LICENSE"><img alt="Code license: MIT" src="https://img.shields.io/badge/code_license-MIT-blue"></a>
</p>

> **Alpha 0.5.0a0 — Calibration & Validation.** The first admitted behavioural forms were tested under frozen time-respecting data roles. Neither passed the full validation gate. This negative result is preserved rather than hidden by added complexity. InfoClar is now an actual read-only browser interface for the stock-flow model, Theory/Learn, empirical validation dashboard and evidence/limitations surface. Behavioural simulation remains disabled.

## Web-first product

InfoClar is the project's primary product surface through scientific maturation to v1. It is implemented under [`web/`](web/) and follows InfoClar Model Suite Design Standard v1.1.

The current browser surface contains the common adaptive workspace:

- a dominant model-specific H/C/F/G/X/BNR macro-financial stock-flow/sector view;
- contextual **Theory / Learn** linked to the selected scientific object;
- an empirical **Dashboard** where data quality/validation status appears before engine metadata;
- an **Auxiliary** panel for sources, mechanism disposition, validation details and limitations;
- persistent EN/RO switching and keyboard-accessible sector selection.

It is deliberately read-only. Interactive behavioural simulation is not presented as available because Alpha 0.5 found zero validated behavioural reference mechanisms. The web product can continue to mature structurally and empirically without overstating model validity.

Native GTK/Granite/Flatpak development is deferred until the web application is mature at or near v1. There is no parallel native model implementation in the current repository.

## Scientific architecture

The project retains four layers: **L0 Data & Ontology → L1 Accounting/SFC Spine → L2 Dynamic Causal Engine → L3 Empirical/Policy Layer**.

The canonical model boundary remains `H / C / F / G / X / BNR`. Bilateral financial positions are represented once as holder assets and issuer liabilities, preserving double-entry conservation. Missing Accounting Spine values remain explicit and are never converted to simulation zero implicitly.

## Alpha 0.5 validation result

### Monetary-policy → lending-rate pass-through

The Alpha 0.4 three-parameter partial-adjustment mechanism was tested on a frozen 13-month BNR sample with roles declared before estimation:

- calibration: Jan–Jun 2024;
- structural selection: Jul–Oct 2024;
- final holdout: Nov 2024–Jan 2025.

Calibration-only identification fails because the policy rate is constant throughout the six-month calibration slice: design rank is `2/3` for both NFC and household lending rates.

On the common Aug–Oct structural-selection window, the candidate loses to simpler persistence and constant-policy-spread baselines for both NFC and households. Parameters are also poorly conditioned and unstable. The final three-month holdout is retained as a one-time diagnostic but does not reverse the failed structural-selection result.

Disposition: **ACTIVATED → CANDIDATE; not validated**.

### Government refinancing → effective debt rate

Official Ministry of Finance data establish material refinancing needs. A diagnostic 2025 redemption/opening-debt proxy is approximately `7.3241%`, but this is not substituted for the model's repricing share because redemption, refixing, prefunding and debt-stock definitions are not identical.

Disposition: **ACTIVATED → DEFERRED; not point identified** until definitionally matched maturity/refixing, effective-rate, marginal-yield and interest-expenditure data are assembled.

See [Alpha 0.5 final audit](docs/CALIBRATION_VALIDATION_AUDIT_0.5.0a0.md), [`monetary_pass_through_results.json`](model/calibration_validation/monetary_pass_through_results.json), [`government_refinancing_assessment.json`](model/calibration_validation/government_refinancing_assessment.json) and [`mechanism_disposition.json`](model/calibration_validation/mechanism_disposition.json).

## Earlier scientific layers

- **Alpha 0.2 — Accounting Spine:** auditable 2025 6×6 holder-by-issuer structures, provenance, B9F/reconciliation and explicit unresolved-value semantics.
- **Alpha 0.3 — Dynamic Core:** executable stocks/flows/delays, year-based time semantics, double-entry conservation, dimensional/extreme-condition/integration tests.
- **Alpha 0.4 — Empirical Dynamics:** evidence-linked behavioural forms classified `ACTIVATED`, `CANDIDATE`, `DEFERRED` or `REJECTED`, with no convenience empirical parameters.

These remain hard foundations for later work.

## Validation discipline

Software correctness, accounting consistency, structural verification, parameter identifiability, predictive validation and causal interpretation are distinct claims.

Alpha 0.5 enforces:

- separate calibration / structural-selection / final-holdout roles;
- time-respecting expanding-origin diagnostics;
- mandatory simple baselines;
- explicit practical-identifiability failure rather than hidden regularisation;
- sensitivity analysis;
- final-holdout contamination after first inspection;
- no promotion of a mechanism merely because a tiny holdout happens to look favourable.

## Current gate

Validated behavioural reference mechanisms: **0**.

Therefore **behavioural Alpha 0.6 Interactive Web Simulator is NO-GO as currently scoped**. InfoClar itself remains GO as the primary read-only structural/empirical/theory web interface and should continue to evolve with subsequent scientific work.

A future simulator requires either new data/model evidence that passes validation or an explicit change of scientific scope. Native packaging remains later, at or near v1.

## Development

```bash
git clone https://github.com/LaurentiuStaicu/romania-macro-financial-dynamics.git
cd romania-macro-financial-dynamics
python -m pip install -e '.[test]'
python -m pytest
```

For the current static InfoClar alpha, serve `web/` with any local static HTTP server so `public/model-stage.json` can be fetched by the browser.

## Limitations

- no behavioural mechanism has yet passed full validation;
- the monetary diagnostic sample is very short and the final holdout has only three observations;
- the tested pass-through form is practically weakly identified;
- government refinancing/repricing observables are not yet definitionally matched for a point-calibrated `m`;
- some Accounting Spine bilateral cells remain unresolved;
- no forecast, scenario ranking, policy recommendation or causal effect is claimed;
- behavioural simulation, scenario laboratory and policy laboratory remain gated.

## Roadmap

Development remains **web-first**. InfoClar accumulates scientifically defensible structure, theory, data, validation and later simulation/scenario capabilities in one continuous browser surface. Flatpak development begins only after the web/scientific product is mature near v1. See [Roadmap](docs/ROADMAP.md).

## License

Original software is licensed under the MIT License. Third-party datasets remain subject to their source licences and terms.
