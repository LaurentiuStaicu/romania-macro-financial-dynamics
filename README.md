<p align="center">
  <img src="web/public/icon.svg" width="96" height="96" alt="Romania Macro-Financial Dynamics icon">
</p>

<h1 align="center">Romania Macro-Financial Dynamics</h1>

<p align="center">
  Bilingual <strong>RO/EN</strong> empirical stock-flow-consistent <strong>System Dynamics</strong> model and web application for exploring Romania's macro-financial system.
</p>

> **Alpha 0.1.0a0 — Project Constitution & Architecture.** The project is in foundation stage. No calibrated forecasting or policy model is claimed yet.

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

The user interface and explanatory material are bilingual from the start: **Romanian is the default language, with English available through a persistent RO/EN switch.** Stable model IDs, equations and data keys are language-neutral.

The visual identity belongs to the same family as World3 Empirical and Cognitive Epistemic Model: a rounded blue-to-teal tile, white structural geometry and a warm-yellow accent, while retaining a distinct macro-financial circulation symbol. See [Visual Identity](docs/VISUAL_IDENTITY.md).

## Current stage

Alpha 0.1.0a0 establishes the project constitution, system boundary, data/model architecture, bilingual contract, canonical registries and release roadmap. The first empirical modelling task after this foundation is the bilateral **F3 government debt-securities matrix** for stocks at 31.12.2025 and transactions during 2025.

See:

- [Project Constitution](docs/PROJECT_CONSTITUTION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [Data and Reconciliation](docs/DATA_AND_RECONCILIATION.md)
- [Visual Identity](docs/VISUAL_IDENTITY.md)

## Scientific boundary

Passing software tests does not establish empirical validity. Accounting identities, observed data, behavioural hypotheses and causal assumptions are kept distinct. Missing bilateral values remain `TBD` until an auditable source and definition are available.

## License

Original software is licensed under the MIT License. Third-party datasets remain subject to their source licences and terms. Documentation/data licensing will be tracked explicitly as the corpus is added.
