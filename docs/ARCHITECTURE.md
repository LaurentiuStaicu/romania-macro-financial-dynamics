# Architecture — Alpha 0.5.1a0

## Layered scientific model

The project is separated into four scientific layers:

- **L0 — Data & Ontology:** ESA sectors/instruments, units, frequencies, provenance and bilingual definitions.
- **L1 — Accounting/SFC Spine:** balance sheets, Flow of Funds, From-Whom-to-Whom matrices, B9/B9F and reconciliation.
- **L2 — Dynamic Causal Engine:** stocks, flows, auxiliaries, delays, feedbacks and evidence-gated behavioural equations.
- **L3 — Empirical/Policy Layer:** calibration, validation, sensitivity and later scenarios/policy experiments.

L1 constrains L2 accounting-wise. L2 may explain endogenous evolution of selected L1 positions only without breaking L1 identities. L3 may not bypass L0/L1 provenance, reconciliation or missing-data semantics.

## Scientific evolution through Alpha 0.5.x

### Accounting Spine

The canonical financial boundary uses H/C/F/G/X/BNR and ESA financial instruments. Missing bilateral empirical values remain explicit and may not silently become zero.

### Dynamic Core

A canonical financial dynamic stock is one bilateral position indexed by `holder × issuer × instrument`. The same amount is the holder's asset and issuer's liability. Sector totals are derived rather than updated independently.

For period amounts:

`closing = opening + transactions + revaluations + other changes`

For rate-based simulation:

`closing = opening + (transaction_rate + revaluation_rate + other_change_rate) × dt`

Canonical simulation time is in years with default structural reference step `dt = 0.25`. The Accounting Spine-to-dynamics bridge rejects unresolved/source-only cells for numeric initialization.

### Empirical Dynamics

Alpha 0.4 introduced evidence-traceable behavioural forms with explicit `ACTIVATED`, `CANDIDATE`, `DEFERRED` and `REJECTED` statuses. `ACTIVATED` means admitted to calibration, not validated or causal.

### Calibration, validation and recovery

Alpha 0.5 makes practical identifiability and chronological data-role separation first-class contracts and correctly closes with zero validated reference mechanisms.

Alpha 0.5.1 adds a prospective recovery architecture rather than weakening that result:

`official-source vintage → frozen prospective split → preregistered parsimonious candidates + simple baselines → expanding-origin structural selection → model-form freeze → eligible final holdout only → final disposition`

The long policy/lending-rate vintage is persisted by a reproducible GitHub Actions fetch. Source hashes and retrieval metadata are stored with the normalized data. The selection runner does not parse values beyond the selection cutoff. The final holdout workflow can open only a target explicitly authorized by the immutable selection-freeze artifact.

Current recovery outcome:

- household contemporaneous one-parameter delta-policy form: passes structural selection, fails fresh final evaluation versus persistence because the holdout contains zero policy-rate changes → `CANDIDATE`;
- NFC parsimonious forms: fail structural selection; final holdout remains unopened → `CANDIDATE`;
- government refinancing/effective-rate: official maturity, refixing, portfolio-cost and issuance-yield evidence expanded, but aggregate repricing boundary remains unmatched → `DEFERRED`;
- validated reference mechanisms: `0`.

The government recovery path is no longer an aggregate proxy exercise. The next valid representation requires an instrument/currency/fixed-floating repricing ledger that can reconstruct published portfolio-cost measures without synthetic allocation.

## Web-first product architecture

**InfoClar web is the reference product interface.** It is not a late wrapper around a finished model and not only a design contract. Scientific milestones progressively populate the same browser surface with the strongest currently defensible content.

The reference workspace remains the adaptive asymmetric InfoClar 2×2 layout:

- **top-left / dominant — Model:** model-specific macro-financial stock-flow/sector view, Flow-of-Funds matrices and contextual empirical graphs;
- **top-right — Theory / Learn:** definitions, mechanisms, evidence and explanations linked to the selected scientific object;
- **bottom-left — Dashboard:** observed empirical values, reconciliation/data quality, validation/performance and only then engine metadata;
- **bottom-right — Auxiliary:** sources, exact values, mechanism disposition, validation details and limitations.

Small screens stack `model → theory → dashboard → auxiliary`.

The Alpha 0.5.x surface remains read-only for behavioural simulation. It exposes longer empirical coverage, prospective validation roles, negative/positive selection signals, the fresh holdout result and government boundary reconciliation without turning them into simulator controls.

## Canonical web data flow

Python remains the authoritative executable scientific runtime. Web UI code must not copy economic equations independently.

Current flow:

`canonical registries/results → tested presentation snapshot (web/public/model-stage.json) → InfoClar panels`

The snapshot is an exported presentation artifact. Tests compare its critical sector/status/data-role/validation values with canonical resources. A later build/export stage can automate snapshot generation further.

## Accessibility and interaction

InfoClar targets WCAG 2.2 AA. The implemented surface includes keyboard-operable sector selection, visible focus styling, skip navigation, live status regions and responsive layout. Scientific distinctions are not encoded by colour alone; labels/status text remain explicit.

## Repository layout

```text
src/romania_macro_financial_dynamics/   authoritative Python scientific package
model/registries/                       canonical model and product registries
model/accounting/                       benchmark Accounting Spine and reconciliation
model/dynamics/                         Dynamic Core contracts
model/empirical_dynamics/               behavioural forms/evidence/classification
model/calibration_validation/           validation/recovery contracts, freezes, results and dispositions
data/raw/validation_recovery/           frozen official recovery vintage
data/processed/                         processed empirical evidence tables
data/provenance/                        source/role/transformation manifests
scripts/                                reproducible data/validation runners
web/                                    InfoClar reference browser application
locales/                                bilingual source strings where view-independent
tests/                                  scientific/software/product contract tests
docs/                                   methods, audits, theory and architecture
.github/workflows/                      CI and reproducible empirical-recovery jobs
```

## Simulator gate

Alpha 0.6 is not simply the next UI feature. Behavioural simulation is allowed only where a scientifically defensible reference mechanism has passed the appropriate prospective validation gate.

Current Alpha 0.5.1 state:

- validated behavioural reference mechanisms: `0`;
- behavioural Interactive Web Simulator: `NO_GO`;
- read-only structural/empirical/theory InfoClar development: `GO`;
- next empirical confirmation observations: prospectively reserved from `2026-08` onward as they become available for all targets.

## Native application

There is intentionally no `native/` application tree. Native elementary OS GTK/Granite/Meson/Flatpak packaging begins only **at or near v1**, after the InfoClar web product and scientific contracts have matured. The future native port consumes the same canonical scientific outputs and must prove numerical/reference-output equivalence; it cannot become a second scientific implementation.

## Version sources

`src/romania_macro_financial_dynamics/__init__.py` and `pyproject.toml` expose software version `0.5.1a0`. `model/registries/model_contract.json` records the scientific/product stage, and `web/public/model-stage.json` exposes a tested presentation snapshot for InfoClar.
