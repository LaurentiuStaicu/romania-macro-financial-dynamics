# Architecture — Alpha 0.1.0a0

## Layered model

The project is separated into four scientific layers:

- **L0 — Data & Ontology:** ESA sectors/instruments, units, frequencies, provenance and bilingual definitions.
- **L1 — Accounting/SFC Spine:** balance sheets, Flow of Funds, From-Whom-to-Whom matrices, B9/B9F and reconciliation.
- **L2 — Dynamic Causal Engine:** stocks, flows, auxiliaries, delays, feedbacks and behavioural equations.
- **L3 — Empirical/Policy Layer:** calibration, validation, sensitivity, scenarios and policy experiments.

L1 constrains L2 accounting-wise; L2 explains the endogenous evolution of selected L1 positions. L3 is not allowed to bypass L0/L1 provenance and reconciliation.

## Repository layout

```text
src/romania_macro_financial_dynamics/   Python scientific package
model/registries/                       canonical model registries
data/                                   later raw/processed/provenance manifests
science/                                later reconciliation/calibration/validation
schemas/                                later machine-readable contracts
web/                                    browser application, initially a consumer
locales/                                bilingual source strings not owned by a view
tests/                                  scientific/software contract tests
docs/                                   method, theory, audit and handoff documentation
.github/workflows/                      CI and later verified deployment
```

`native/` is intentionally absent in the foundation stage. It will be introduced near v1 after the web/scientific contracts stabilize.

## Scientific core

Python is the authoritative executable model language in the current roadmap. Canonical registries live outside individual views. The web layer must consume exported canonical data/results rather than duplicate model equations during early development.

A later compute spike will benchmark in-browser execution (for example Python/WASM approaches) before choosing arbitrary interactive browser simulation. The architectural requirement is equivalence, not a preselected runtime.

## Web application

The web application is cross-platform and bilingual RO/EN. Initial stages focus on understanding and auditability:

1. theory and guided explanation;
2. system/sector map;
3. Flow-of-Funds and balance-sheet explorers;
4. equations and provenance;
5. validation diagnostics;
6. saved reference scenarios.

Interactive arbitrary simulation is added only after the executable model and validation contracts are stable enough to expose safely.

## Native application

Near v1, add a native elementary OS application using the then-supported GTK/Granite/Meson/Flatpak stack. It must consume the same canonical scientific outputs and registries as the web application. Platform-specific UI code must not fork the economic model.

## Version sources

`src/romania_macro_financial_dynamics/__init__.py` contains the software version during Alpha 0.1. The release process will later add checks ensuring Python, web metadata, model specification and exported artifacts identify their versions separately and consistently.
