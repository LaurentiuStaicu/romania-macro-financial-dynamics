<p align="center">
  <img src="web/public/icon.svg" width="96" height="96" alt="Romania Macro-Financial Dynamics icon">
</p>

<h1 align="center">Romania Macro-Financial Dynamics</h1>

<p align="center">
  Bilingual <strong>RO/EN</strong> empirical stock-flow-consistent <strong>System Dynamics</strong> model and web application for exploring Romania's macro-financial system.
</p>

<p align="center">
  <img alt="Version 0.2.0a0" src="https://img.shields.io/badge/version-0.2.0a0-4e9a06">
  <img alt="Development stage: alpha" src="https://img.shields.io/badge/stage-alpha-e5a50a">
  <img alt="Web application: in development" src="https://img.shields.io/badge/app-Web_in_development-4a90d9">
  <img alt="Languages: RO and EN" src="https://img.shields.io/badge/languages-RO_%2F_EN-0e9a83">
  <img alt="elementary OS Flatpak: planned" src="https://img.shields.io/badge/elementary_OS_Flatpak-planned-64baff">
  <a href="LICENSE"><img alt="Code license: MIT" src="https://img.shields.io/badge/code_license-MIT-blue"></a>
</p>

<p align="center">
  <img alt="Web application in development / Aplicație web în dezvoltare" src="https://img.shields.io/badge/Aplica%C8%9Bie_web_%C3%AEn_dezvoltare_%2F_Web_app_in_development-087F73?style=for-the-badge">
</p>

> **Alpha 0.2.0a0 — Accounting Spine.** The project now has a machine-auditable L1 accounting/SFC contract for the 2025 benchmark. Published values with incomplete or mismatched definitions remain explicitly unresolved rather than being silently imputed. No calibrated forecasting or policy model is claimed yet. The large launch-style control above remains intentionally non-clickable until a CI-verified public web deployment exists.

## Purpose / Scop

**EN.** The project aims to connect Romania's real economy, sectoral income and saving, funding needs, financial instruments, balance sheets, monetary policy, public finance and the external sector in one accounting-consistent and dynamically explicit model.

**RO.** Proiectul urmărește conectarea economiei reale a României, a veniturilor și economisirii sectoriale, a necesarului de finanțare, instrumentelor financiare, bilanțurilor, politicii monetare, finanțelor publice și sectorului extern într-un singur model coerent contabil și explicit dinamic.

The intended mature product combines:

- System Dynamics / stock-and-flow modelling;
- Stock-Flow Consistent macro-financial accounting;
- Flow of Funds / From-Whom-to-Whom matrices;
- ESA 2010 sector and financial-instrument definitions;
- empirical data, provenance and reconciliation;
- causal feedbacks, delays and behavioural equations;
- calibration, validation, sensitivity analysis and scenario experiments.

## Product direction

The application is **web-first**. A verified browser application will remain available across operating systems. A native **elementary OS Flatpak** using GTK/Granite is planned near v1, after the scientific model and web contracts are stable. Web and native interfaces must consume the same scientific core rather than reimplementing the equations independently.

The user interface and explanatory material are bilingual from the start. Stable model IDs, equations and data keys are language-neutral. Shared user-facing names are stored canonically in [`model/registries/product_labels.json`](model/registries/product_labels.json) rather than being independently re-declared by views.

The visual identity belongs to the same family as World3 Empirical and Cognitive Epistemic Model: a rounded blue-to-teal tile, white structural geometry and a warm-yellow accent, while retaining a distinct macro-financial circulation symbol. The repository presentation also follows the same icon → title → description → status badges → launch-control grammar. See [Visual Identity](docs/VISUAL_IDENTITY.md) and [Product Presentation Contract](docs/PRODUCT_PRESENTATION_CONTRACT.md).

## Current stage

Alpha 0.2.0a0 establishes the auditable Accounting Spine for the 2025 benchmark:

- canonical 6×6 holder-by-issuer address spaces for F3, F2, F4, F8, F5, F6 and F7;
- separate stock and financial-transaction contracts;
- official source and exact-series provenance records;
- explicit missing/partial-coverage semantics;
- B9F and reconciliation logic;
- balance-sheet asset/liability conventions;
- a reconciliation ledger that prohibits forced closure.

The stage deliberately distinguishes **accounting architecture** from **empirical coverage**. Missing definitionally matched bilateral values remain `TBD`; aggregate or partial-maturity controls are not converted into invented exact cells. See [Alpha 0.2 Accounting Spine exit audit](docs/ACCOUNTING_SPINE_AUDIT_0.2.0a0.md).

See also:

- [Project Constitution](docs/PROJECT_CONSTITUTION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [Data and Reconciliation](docs/DATA_AND_RECONCILIATION.md)
- [Visual Identity](docs/VISUAL_IDENTITY.md)
- [Product Presentation Contract](docs/PRODUCT_PRESENTATION_CONTRACT.md)

## Scientific boundary

Passing software tests does not establish empirical validity. Accounting identities, observed data, behavioural hypotheses and causal assumptions are kept distinct. Missing bilateral values remain `TBD` until an auditable source and definition are available.

## License

Original software is licensed under the MIT License. Third-party datasets remain subject to their source licences and terms. Documentation/data licensing will be tracked explicitly as the corpus is added.
