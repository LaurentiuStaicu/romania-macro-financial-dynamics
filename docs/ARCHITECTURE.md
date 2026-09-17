# Architecture — Alpha 0.3.0a0

## Layered model

The project is separated into four scientific layers:

- **L0 — Data & Ontology:** ESA sectors/instruments, units, frequencies, provenance and bilingual definitions.
- **L1 — Accounting/SFC Spine:** balance sheets, Flow of Funds, From-Whom-to-Whom matrices, B9/B9F and reconciliation.
- **L2 — Dynamic Causal Engine:** stocks, flows, auxiliaries, delays, feedbacks and later behavioural equations.
- **L3 — Empirical/Policy Layer:** calibration, validation, sensitivity, scenarios and policy experiments.

L1 constrains L2 accounting-wise; L2 may explain the endogenous evolution of selected L1 positions only without breaking L1 identities. L3 is not allowed to bypass L0/L1 provenance and reconciliation.

## Alpha 0.3 structural dynamic core

Alpha 0.3 introduces the executable substrate of L2 while deliberately deferring behavioural closure.

The canonical financial dynamic stock is one bilateral position indexed by:

`holder × issuer × instrument`

The same represented amount is the holder's financial asset and the issuer's equal financial liability. Sector balance-sheet totals are derived from these positions rather than updated independently, preventing numerical drift between asset and liability views.

For period amounts:

`closing = opening + transactions + revaluations + other changes`

For rate-based simulation:

`closing = opening + (transaction_rate + revaluation_rate + other_change_rate) × dt`

Canonical simulation time is measured in **years** with a default reference step of **0.25 year**, matching the preferred quarterly empirical cadence when definitions are comparable.

The Accounting Spine-to-dynamics bridge is guarded: a matrix containing `TBD` or source-only cells cannot initialize a numeric simulation. Missing empirical values therefore cannot silently become zeros.

A reusable first-order delay primitive is available:

`d(delay_state)/dt = (input - delay_state) / tau`

Concrete economic delays and behavioural equations remain inactive until their evidence and parameter gates are passed.

See `model/dynamics/core_contract.json`, `model/dynamics/feedback_registry.json` and `docs/DYNAMIC_CORE_0.3.0a0.md`.

## Feedback architecture

Candidate loops are registered for sovereign refinancing/interest costs, issuance/yields, bank credit/balance sheets, monetary-credit transmission and external FX/refinancing. In Alpha 0.3 they are qualitative hypotheses only:

- `scientific_status = BEHAVIOURAL_CANDIDATE`;
- `quantitatively_active = false`;
- delay parameters remain `TBD`;
- no candidate can affect numerical results.

Behavioural closure begins only in Alpha 0.4 Empirical Dynamics, after explicit equation, units, evidence, parameter-source/estimation, extreme-condition and sensitivity gates.

## Repository layout

```text
src/romania_macro_financial_dynamics/   Python scientific package
model/registries/                       canonical model and product registries
model/accounting/                       benchmark accounting spine and reconciliation
model/dynamics/                         dynamic-core and feedback contracts
data/                                   later raw/processed/provenance manifests
science/                                later reconciliation/calibration/validation
schemas/                                later machine-readable contracts
web/                                    browser application, initially a consumer
locales/                                bilingual source strings not owned by a view
tests/                                  scientific/software contract tests
docs/                                   method, theory, audit and handoff documentation
.github/workflows/                      CI and later verified deployment
```

`native/` remains intentionally absent. It will be introduced near v1 after the web/scientific contracts stabilize.

## Scientific core

Python is the authoritative executable model language. Canonical registries live outside individual views. The web layer must consume exported canonical data/results rather than duplicate model equations.

Structural verification currently includes accounting-stock identities, double-entry conservation, dimensional rate×time conversion, extreme conditions, delay steady-state behaviour, incomplete-state rejection and integration-error convergence.

A later compute spike will benchmark in-browser execution before choosing arbitrary interactive browser simulation. The architectural requirement is numerical equivalence, not a preselected runtime.

## Web application

The web application is cross-platform and bilingual EN/RO under InfoClar Model Suite Design Standard v1.1. Initial stages focus on understanding and auditability:

1. theory and guided explanation;
2. system/sector map;
3. Flow-of-Funds and balance-sheet explorers;
4. equations and provenance;
5. validation diagnostics;
6. saved reference scenarios when those scenarios actually exist.

Interactive arbitrary simulation is added only after the executable model and validation contracts are stable enough to expose safely.

## Native application

Near v1, add a native elementary OS application using the then-supported GTK/Granite/Meson/Flatpak stack. It must consume the same canonical scientific outputs and registries as the web application. Platform-specific UI code must not fork the economic model.

## Version sources

`src/romania_macro_financial_dynamics/__init__.py` and `pyproject.toml` expose the software version. CI tests keep these user-visible/version-contract expectations synchronized. Later release automation will also verify web metadata, model specification and exported-artifact versions.
