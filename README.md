<p align="center">
  <img src="web/public/icon.svg" width="96" height="96" alt="Romania Macro-Financial Dynamics icon">
</p>

<h1 align="center">Romania Macro-Financial Dynamics</h1>

<p align="center"><img alt="Version 0.4.0a0" src="https://img.shields.io/badge/version-0.4.0a0-4e9a06"></p>

<p align="center">
  Empirical stock-flow-consistent <strong>System Dynamics</strong> model of Romania's macro-financial system, with evidence-traceable behavioural mechanisms and an <strong>EN/RO</strong> product contract.
</p>

<p align="center">
  <img alt="Development stage: alpha" src="https://img.shields.io/badge/stage-alpha-e5a50a">
  <img alt="Web application: in development" src="https://img.shields.io/badge/app-Web_in_development-4a90d9">
  <img alt="Languages: EN and RO" src="https://img.shields.io/badge/languages-EN_%2F_RO-0e9a83">
  <img alt="elementary OS Flatpak: planned" src="https://img.shields.io/badge/elementary_OS_Flatpak-planned-64baff">
  <a href="LICENSE"><img alt="Code license: MIT" src="https://img.shields.io/badge/code_license-MIT-blue"></a>
</p>

> **Alpha 0.4.0a0 — Empirical Dynamics.** Behavioural mechanisms are now classified and evidence-linked, but they are not yet calibrated. `ACTIVATED` means admitted to Alpha 0.5 calibration/validation, not numerically validated. No historical coefficient or missing value is silently inserted into the model.

## Scientific architecture

The project retains four layers: **L0 Data & Ontology → L1 Accounting/SFC Spine → L2 Dynamic Causal Engine → L3 Empirical/Policy Layer**. Alpha 0.4 adds the first empirical-behavioural layer while preserving the Accounting Spine, Alpha 0.3 stock/flow/delay semantics and InfoClar Model Suite Design Standard v1.1.

The canonical model boundary remains `H / C / F / G / X / BNR`. Bilateral financial positions remain represented once as a holder asset and issuer liability, so behavioural equations cannot bypass double-entry conservation or reinterpret unresolved Accounting Spine cells as zero.

## Alpha 0.4 mechanism status

The initial calibration set is deliberately small:

- **ACTIVATED:** monetary-policy → lending-rate partial adjustment; government refinancing → effective debt-rate repricing;
- **CANDIDATE:** household consumption, corporate investment, aggregate bank credit, sovereign spread/yield, FX pass-through to inflation;
- **DEFERRED:** credit-risk/NPL response, fiscal primary-balance reaction, monetary-policy reaction function, currency-specific external FX/refinancing feedback;
- **REJECTED:** direct bivariate policy-rate → FX shortcut; debt-stock-only → default-risk shortcut.

Every mechanism has a canonical functional form or explicit reason for deferral/rejection, source/evidence references, observables, parameter or estimation plan, limitations and rejection/degradation criteria. See [`model/empirical_dynamics/mechanism_registry.json`](model/empirical_dynamics/mechanism_registry.json), [`evidence_registry.json`](model/empirical_dynamics/evidence_registry.json) and the [Alpha 0.4 final audit](docs/EMPIRICAL_DYNAMICS_AUDIT_0.4.0a0.md).

## Parameter discipline

Implemented behavioural functions are explicit pure-Python equations. Empirical coefficients are required arguments rather than hidden defaults. Historical Romanian estimates support mechanism plausibility but are not reused automatically under a different monetary, inflation-targeting or exchange-rate regime.

Alpha 0.5 must determine whether admitted forms are practically identifiable and whether they improve on simpler baselines with time-respecting validation. Candidate mechanisms can be promoted only using structural-selection data; the final evaluation holdout cannot be used for model selection.

## Accounting Spine & Dynamic Core

Alpha 0.2 provides the auditable 2025 From-Whom-to-Whom/balance-sheet structure, provenance, B9F/reconciliation logic and explicit `TBD` semantics. Alpha 0.3 provides executable stocks/flows, year-based time semantics (`dt = 0.25` reference step), structural delays, dimensional tests, double-entry conservation and guarded empirical initialization.

See [Accounting Spine audit](docs/ACCOUNTING_SPINE_AUDIT_0.2.0a0.md), [Dynamic Core](docs/DYNAMIC_CORE_0.3.0a0.md) and [Dynamic Core audit](docs/DYNAMIC_CORE_AUDIT_0.3.0a0.md).

## InfoClar Model Suite v1.1

The shared product contract remains unchanged: English default with persistent Romanian alternative; adaptive asymmetric 2×2 workspace; a dominant macro-financial stock-flow/sector view; contextual Theory/Learn; an empirical/dashboard panel; and an auxiliary source/validation/limitations panel. Scientific meaning may not depend on colour alone and the model-specific central diagram is not replaced by a generic suite diagram.

## Validation status

Alpha 0.4 is **not** a forecasting or causal-validation milestone. Passing CI proves software/contract consistency only. Calibration, historical reproduction, practical identifiability, sensitivity and time-respecting out-of-sample validation belong to **Alpha 0.5 — Calibration & Validation**.

## Development

```bash
git clone https://github.com/LaurentiuStaicu/romania-macro-financial-dynamics.git
cd romania-macro-financial-dynamics
python -m pip install -e '.[test]'
python -m pytest
```

The Web simulator and native Flatpak are intentionally not implemented yet.

## Limitations

- behavioural coefficients are not calibrated in Alpha 0.4;
- several mechanisms remain candidates/deferred because aggregation, observability or regime stability is insufficiently established;
- some bilateral Accounting Spine cells remain explicitly unresolved;
- no forecast, scenario ranking, policy recommendation or causal effect is claimed;
- the future Web simulator remains outside the current milestone.

## Roadmap

The next scientific milestone is **Alpha 0.5 — Calibration & Validation**: strict data-role separation, historical reproduction, parameter assessment, practical-identifiability diagnostics, sensitivity analysis, time-respecting multi-origin/holdout evaluation where data permit, simpler baselines and explicit uncertainty. See [Roadmap](docs/ROADMAP.md).

## License

Original software is licensed under the MIT License. Third-party datasets remain subject to their source licences and terms.
