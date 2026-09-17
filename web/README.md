# Web application — InfoClar reference interface

InfoClar is the **primary product interface** for Romania Macro-Financial Dynamics. It is no longer only a design contract: Alpha 0.5 introduces the first implemented browser surface in `web/index.html`, `web/styles.css` and `web/app.js`.

The web application remains deliberately **read-only scientific** at this milestone. It exposes structure, theory, empirical status, provenance and validation diagnostics, but it does not enable behavioural simulation because Alpha 0.5 has not established a validated reference behavioural mechanism.

## Product sequence

The project is web-first through the scientific/product maturation path to v1:

1. continuously evolve the InfoClar browser surface alongside scientific milestones;
2. keep the central visualization specific to the macro-financial stock-flow system;
3. connect Theory/Learn, empirical dashboard and Auxiliary to the same selected scientific objects;
4. introduce controlled simulation only after its scientific validation gate is passed;
5. add native GTK/Granite/Flatpak packaging only at or near v1, after the web reference product is mature.

There is intentionally no `native/` application tree in Alpha 0.5.

## Implemented Alpha 0.5 surface

Desktop uses the InfoClar asymmetric 2×2 workspace:

- **Model — dominant top-left:** interactive/selectable H/C/F/G/X/BNR sector network with financial-position and candidate-feedback visual grammar;
- **Theory / Learn — top-right:** contextual sector explanation and current scientific/evidence state;
- **Dashboard — bottom-left:** empirical data roles, mechanism counts and validation status, with empirical evidence shown before engine metadata;
- **Auxiliary — bottom-right:** selected mechanism disposition, official sources, validation caveats and limitations.

On narrower displays the panels stack `model → theory → dashboard → auxiliary`.

The EN/RO switch persists locally in the browser. Sector selection is keyboard operable. The actual application surface includes a skip link, visible focus states and live status regions as part of the WCAG 2.2 AA target.

## Canonical scientific payload

The browser currently consumes `public/model-stage.json`. This is an exported presentation snapshot whose values are tested against canonical scientific registries/results; it is not a second implementation of the economic equations.

Canonical sources remain:

- scientific runtime: `../src/romania_macro_financial_dynamics/`;
- Accounting Spine: `../model/accounting/`;
- Dynamic Core: `../model/dynamics/`;
- Empirical Dynamics: `../model/empirical_dynamics/`;
- Calibration & Validation: `../model/calibration_validation/`;
- design tokens: `../model/registries/design_tokens.json`;
- workspace contract: `../model/registries/workspace_contract.json`;
- product labels: `../model/registries/product_labels.json`.

Future build/export tooling should generate the web snapshot automatically from these canonical resources rather than allowing manual drift.

## Capability truthfulness

The browser must not render roadmap capabilities as if they are scientifically available. At Alpha 0.5:

- system structure: available;
- Theory/Learn: available in first contextual form;
- empirical/validation dashboard: available;
- source/limitation inspection: available;
- behavioural interactive simulation: **not available**;
- scenario laboratory: **not available**;
- policy laboratory: **not available**;
- native Flatpak: **deferred near v1**.

A later Alpha 0.6 may activate simulation only for capabilities that have a defensible validated scientific reference model, or after an explicit scope decision changes that gate.
