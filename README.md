<p align="center">
  <img src="web/public/icon.svg" width="96" height="96" alt="Romania Macro-Financial Dynamics icon">
</p>

<h1 align="center">Romania Macro-Financial Dynamics</h1>

<p align="center">
  <img alt="Version 0.2.1a0" src="https://img.shields.io/badge/version-0.2.1a0-4e9a06">
</p>

<p align="center">
  Empirical stock-flow-consistent <strong>System Dynamics</strong> model for exploring Romania's macro-financial system through sectors, financial instruments, balance sheets, Flow of Funds and later dynamic feedbacks.
</p>

<p align="center">
  Model empiric <strong>Stock-Flow Consistent + System Dynamics</strong> pentru explorarea sistemului macro-financiar al României, cu interfață <strong>EN/RO</strong>.
</p>

<p align="center">
  <img alt="Web application in development" src="https://img.shields.io/badge/Web_app_in_development-087F73?style=for-the-badge">
</p>

<p align="center">
  <img alt="Development stage: alpha" src="https://img.shields.io/badge/stage-alpha-e5a50a">
  <img alt="Web application: in development" src="https://img.shields.io/badge/app-Web_in_development-4a90d9">
  <img alt="Languages: EN and RO" src="https://img.shields.io/badge/languages-EN_%2F_RO-0e9a83">
  <img alt="elementary OS Flatpak: planned" src="https://img.shields.io/badge/elementary_OS_Flatpak-planned-64baff">
  <a href="LICENSE"><img alt="Code license: MIT" src="https://img.shields.io/badge/code_license-MIT-blue"></a>
</p>

> **Alpha 0.2.1a0 — InfoClar Model Suite v1.1 alignment.** Alpha 0.2 Accounting Spine is integrated and CI-verified. This patch standardizes product language, layout, design tokens, repository presentation and accessibility contracts without changing accounting semantics or scientific values. A clickable `Open app` control will replace the development status only after a CI-verified public web deployment exists.

## Model

The project connects six top-level analytical sectors — households/NPISH (`H`), non-financial corporations (`C`), financial corporations excluding the separately shown central bank (`F`), general government (`G`), rest of the world (`X`) and the National Bank of Romania (`BNR`) — through ESA 2010 financial instruments and accounting relationships.

The reference application workspace follows InfoClar Model Suite Design Standard v1.1:

- a dominant stock-flow/sector and Flow-of-Funds workspace;
- a contextual Theory / Learn panel linked to selected scientific objects;
- a dashboard for major empirical/accounting indicators;
- an auxiliary panel for sources, validation, limitations and selection details.

The layout is adaptive. On small screens these areas stack rather than forcing a desktop grid. The model visualization itself remains macro-financial and is not copied from World3 Empirical or Cognitive Epistemic Model.

A truthful interactive model image is intentionally not shown yet: the browser model view is not implemented in Alpha 0.2.x.

## Current scientific stage

Alpha 0.2 established the auditable Accounting/SFC Spine for the 2025 benchmark:

- 6×6 holder-by-issuer address spaces for F3, F2, F4, F8, F5, F6 and F7;
- separate closing-position and financial-transaction contracts;
- official-source provenance records and exact series identifiers where verified;
- explicit `TBD` / partial-coverage semantics;
- B9F and asset/liability reconciliation logic;
- a reconciliation ledger that prohibits forced closure and zero-as-missing.

The stage distinguishes **accounting architecture** from **empirical coverage**. A missing definitionally matched bilateral value stays unresolved; an aggregate or partial-maturity series is not converted into a fabricated exact cell.

## Data & provenance

Primary benchmark hierarchy:

1. Eurostat / ESA 2010;
2. ECB Data Portal / Quarterly Sector Accounts;
3. BNR;
4. Ministry of Finance and other official Romanian institutions;
5. secondary sources only for cross-checking or context.

Benchmark convention:

- stocks: 31.12.2025 / 2025-Q4;
- annual financial transactions: 01.01.2025–31.12.2025;
- primary WTWTW accounting basis: non-consolidated ESA 2010 quarterly financial accounts.

See [`model/accounting/benchmark_2025.json`](model/accounting/benchmark_2025.json), [`model/accounting/source_registry.json`](model/accounting/source_registry.json) and [Data and Reconciliation](docs/DATA_AND_RECONCILIATION.md).

## Theory / Learn

The mature application will not separate theory from use. Selecting a sector, instrument, matrix cell, empirical graph or later causal mechanism will expose the matching definition, explanation and provenance while a complete sequential theory reader remains available.

The project architecture separates:

- **L0 — Data & Ontology**;
- **L1 — Accounting/SFC Spine**;
- **L2 — Dynamic Causal Engine**;
- **L3 — Empirical/Policy Layer**.

See [Project Constitution](docs/PROJECT_CONSTITUTION.md), [Architecture](docs/ARCHITECTURE.md) and [InfoClar Model Suite Design Standard v1.1 profile](docs/INFOCLAR_MODEL_SUITE_DESIGN_STANDARD_V1.1.md).

## Validation & reconciliation

Software correctness and empirical validity are separate gates. Alpha 0.2 CI enforces matrix address-space integrity, missing-data semantics, partial-source status and reconciliation identities. Empirical controls remain labelled separately from complete bilateral observations.

See [Alpha 0.2 Accounting Spine exit audit](docs/ACCOUNTING_SPINE_AUDIT_0.2.0a0.md) and [`model/accounting/reconciliation_2025.json`](model/accounting/reconciliation_2025.json).

## Installation / development

The current deliverable is the Python scientific core and contracts, not a user-ready application package.

```bash
git clone https://github.com/LaurentiuStaicu/romania-macro-financial-dynamics.git
cd romania-macro-financial-dynamics
python -m pip install -e '.[test]'
python -m pytest
```

The web application remains in development. A native elementary OS Flatpak is intentionally deferred until the scientific and web contracts are stable near v1.

## Limitations

- No calibrated forecasting model is claimed yet.
- No policy recommendation engine exists yet.
- Many bilateral empirical cells remain explicitly unresolved where matched public data have not been established.
- Dynamics, Simulation and Scenarios are roadmap capabilities, not current application features.
- The absence of a clickable launch button or model screenshot is deliberate until a verified implementation exists.

## Product standard

InfoClar Model Suite v1.1 uses English as the default UI language with a persistent Romanian alternative. It standardizes typography, spacing, buttons, badges, tooltips, cards/panels, selection states, legends, navigation and adaptive layout while preserving model-specific scientific visualization.

Canonical resources:

- [InfoClar Model Suite Design Standard v1.1 profile](docs/INFOCLAR_MODEL_SUITE_DESIGN_STANDARD_V1.1.md)
- [Product Presentation Contract](docs/PRODUCT_PRESENTATION_CONTRACT.md)
- [Visual Identity](docs/VISUAL_IDENTITY.md)
- [`design_tokens.json`](model/registries/design_tokens.json)
- [`workspace_contract.json`](model/registries/workspace_contract.json)
- [`product_labels.json`](model/registries/product_labels.json)

## Roadmap

The next scientific milestone after this uniformization pass is **Alpha 0.3 — Dynamic Core**: executable stocks, flows, auxiliaries, feedbacks and delays constrained by the validated accounting spine. See [Roadmap](docs/ROADMAP.md).

## License

Original software is licensed under the MIT License. Third-party datasets remain subject to their source licences and terms. Documentation/data licensing is tracked separately as the corpus grows.
