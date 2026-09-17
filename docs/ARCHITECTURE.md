# Architecture — Alpha 0.5.0a0

## Layered scientific model

The project is separated into four scientific layers:

- **L0 — Data & Ontology:** ESA sectors/instruments, units, frequencies, provenance and bilingual definitions.
- **L1 — Accounting/SFC Spine:** balance sheets, Flow of Funds, From-Whom-to-Whom matrices, B9/B9F and reconciliation.
- **L2 — Dynamic Causal Engine:** stocks, flows, auxiliaries, delays, feedbacks and evidence-gated behavioural equations.
- **L3 — Empirical/Policy Layer:** calibration, validation, sensitivity and later scenarios/policy experiments.

L1 constrains L2 accounting-wise. L2 may explain endogenous evolution of selected L1 positions only without breaking L1 identities. L3 may not bypass L0/L1 provenance, reconciliation or missing-data semantics.

## Scientific evolution through Alpha 0.5

### Accounting Spine

The canonical financial boundary uses H/C/F/G/X/BNR and ESA financial instruments. Missing bilateral empirical values remain explicit and may not silently become zero.

### Dynamic Core

A canonical financial dynamic stock is one bilateral position indexed by:

`holder × issuer × instrument`

The same amount is the holder's asset and issuer's liability. Sector totals are derived from these positions rather than updated independently.

For period amounts:

`closing = opening + transactions + revaluations + other changes`

For rate-based simulation:

`closing = opening + (transaction_rate + revaluation_rate + other_change_rate) × dt`

Canonical simulation time is in years with default structural reference step `dt = 0.25`. The Accounting Spine-to-dynamics bridge rejects unresolved/source-only cells for numeric initialization.

### Empirical Dynamics

Alpha 0.4 introduced evidence-traceable behavioural forms with explicit `ACTIVATED`, `CANDIDATE`, `DEFERRED` and `REJECTED` statuses. `ACTIVATED` means admitted to calibration, not validated or causal.

### Calibration & Validation

Alpha 0.5 makes practical identifiability and chronological data-role separation first-class contracts. Calibration, structural selection and final evaluation/holdout are separate roles. An inspected holdout cannot subsequently be called independent validation for a revised model.

The two Alpha 0.4 activated mechanisms fail to become validated reference mechanisms in 0.5: monetary pass-through is degraded to candidate after rank/conditioning/baseline failures; government refinancing/effective-rate repricing is deferred because the required repricing share is not definitionally point-identified by currently assembled official data.

## Web-first product architecture

**InfoClar web is the reference product interface from Alpha 0.5 onward.** It is not a late wrapper around a finished model and not only a design contract. Scientific milestones progressively populate the same browser surface with the strongest currently defensible content.

The reference workspace remains the adaptive asymmetric InfoClar 2×2 layout:

- **top-left / dominant — Model:** model-specific macro-financial stock-flow/sector view, Flow-of-Funds matrices and contextual empirical graphs;
- **top-right — Theory / Learn:** definitions, mechanisms, evidence and explanations linked to the selected scientific object;
- **bottom-left — Dashboard:** observed empirical values, reconciliation/data quality, validation/performance and only then engine metadata;
- **bottom-right — Auxiliary:** sources, exact values, mechanism disposition, validation details and limitations.

Small screens stack `model → theory → dashboard → auxiliary`.

Alpha 0.5 implements the first real surface in `web/index.html`, `web/styles.css` and `web/app.js`. It is intentionally read-only because no behavioural reference mechanism has yet passed validation. A model can therefore become increasingly understandable and auditable on the web without falsely implying that interactive simulation is scientifically ready.

## Canonical web data flow

Python remains the authoritative executable scientific runtime. Web UI code must not copy economic equations independently.

Current flow:

`canonical registries/results → tested presentation snapshot (web/public/model-stage.json) → InfoClar panels`

The snapshot is an exported presentation artifact. Tests compare its critical sector/status/data-role values with canonical resources. A later build/export stage should automate snapshot generation further.

The UI may transform presentation state — selected sector, language, layout, formatting — but scientific quantities/statuses come from canonical artifacts.

## Accessibility and interaction

InfoClar targets WCAG 2.2 AA. The implemented surface includes keyboard-operable sector selection, visible focus styling, skip navigation, live status regions and responsive layout. Scientific distinctions are not encoded by colour alone; labels/status text remain explicit.

Interactive simulation must later preserve keyboard/pointer alternatives and predictable context changes rather than relying on drag-only or opaque visual controls.

## Repository layout

```text
src/romania_macro_financial_dynamics/   authoritative Python scientific package
model/registries/                       canonical model and product registries
model/accounting/                       benchmark Accounting Spine and reconciliation
model/dynamics/                         Dynamic Core contracts
model/empirical_dynamics/               behavioural forms/evidence/classification
model/calibration_validation/           validation contracts, results and dispositions
data/processed/                         frozen empirical analysis datasets
data/provenance/                        source/role/transformation manifests
web/                                    InfoClar reference browser application
locales/                                bilingual source strings where view-independent
tests/                                  scientific/software/product contract tests
docs/                                   methods, audits, theory and architecture
.github/workflows/                      CI and later verified web deployment
```

## Simulator gate

Alpha 0.6 is not simply “the next UI feature.” Behavioural simulation is allowed only where a scientifically defensible validated reference model exists or where an explicit later scope decision clearly reclassifies a feature as assumption-driven exploratory modelling.

Current Alpha 0.5 state:

- validated behavioural reference mechanisms: `0`;
- behavioural Interactive Web Simulator: `NO_GO`;
- read-only structural/empirical/theory InfoClar development: `GO`.

## Native application

There is intentionally no `native/` application tree. Native elementary OS GTK/Granite/Meson/Flatpak packaging begins only **at or near v1**, after the InfoClar web product and scientific contracts have matured. The future native port consumes the same canonical scientific outputs and must prove numerical/reference-output equivalence; it cannot become a second scientific implementation.

## Version sources

`src/romania_macro_financial_dynamics/__init__.py` and `pyproject.toml` expose software version `0.5.0a0`. `model/registries/model_contract.json` records the corresponding scientific/product stage, and `web/public/model-stage.json` exposes a tested presentation snapshot for InfoClar.
