# InfoClar Model Suite Design Standard v1.1 — Romania Macro-Financial Dynamics profile

Date adopted: 2026-09-17

This document is the project-specific conformance profile for the shared InfoClar Model Suite Design Standard v1.1. It standardizes product grammar across Romania Macro-Financial Dynamics, Cognitive Epistemic Model and World3 Empirical without making their scientific visualizations identical.

## 1. Non-negotiable family rules

- Web is the reference cross-platform product surface; an elementary-style native Flatpak is added later without forking the scientific implementation.
- English (`EN`) is the default product language; Romanian (`RO`) is a persistent first-class alternative.
- Shared design tokens govern typography, spacing, focus, buttons, badges, tooltips, cards/panels, selection states, legends and navigation.
- Scientific meaning must never depend on colour alone.
- The interface is calm and information-dense rather than decorative: few purposeful panels, strong spacing hierarchy, compact chrome and readable theory.
- Web/native parity is semantic and scientific, not pixel-for-pixel.
- Uniformization must not change model equations, accounting definitions, empirical values, source provenance or validation results.

## 2. Shared desktop workspace

The canonical desktop composition is an asymmetric 2×2 grid:

| Position | Role | Romania Macro-Financial Dynamics content |
|---|---|---|
| top-left, dominant | Model / mechanism workspace | stock-flow and sector diagram, From-Whom-to-Whom/Flow-of-Funds matrix, contextual real-data graphs |
| top-right | Theory / Learn / context | complete theory reader, definitions, mechanism explanation and provenance links tied to the selected model object |
| bottom-left | Dashboard | major stocks, flows, reconciliation status and later dynamic indicators, with unit/period/status visible |
| bottom-right | Auxiliary | sources, validation, limitations, selection details and later exports |

The model panel is intentionally larger than the other panels. The scientific representation remains model-specific: this project uses sectors, financial instruments, stocks/flows, accounting links and real empirical series rather than adopting the diagrams of the other applications.

## 3. Adaptive behaviour

On smaller screens the four areas stack in this order:

`model → theory → dashboard → auxiliary`

The page must not require horizontal scrolling. A scientific diagram may use its own internal pan/zoom surface when a two-dimensional representation is essential. The theory panel remains readable at approximately 66–72 characters per line.

## 4. Header and navigation

The compact header contains:

- application name;
- software version;
- persistent `EN / RO` language switch.

Canonical navigation labels come from `model/registries/product_labels.json`, not from view-local strings. The long-term section vocabulary is:

`Understand → System map → Flow of funds → Dynamics → Simulation → Scenarios → Validation → Data & sources`

Only implemented capabilities may appear as available. During Alpha 0.2.x, Dynamics, Simulation and Scenarios remain future surfaces.

## 5. Theory / Learn contract

Theory is not a detached documentation dump. It must be interleaved with application use:

- selecting a sector, instrument, matrix cell, graph or mechanism exposes the relevant explanation;
- definitions and equations link back to the scientific object they explain;
- source/provenance links are reachable from the same context;
- the complete reader remains available for sequential study;
- concise interface labels do not justify removing scientific depth from the theory content.

## 6. Dashboard contract

When real empirical data are available, the dashboard prioritizes indicators by model relevance/impact rather than arbitrary visual prominence. Every numerical item shows at least unit, period and scientific/data status. An incomplete value remains explicitly unresolved.

The current Accounting Spine can expose, when the web shell is implemented:

- benchmark date and flow period;
- matrix empirical-coverage status;
- B9F/reconciliation status;
- major verified control series;
- unresolved-cell counts.

## 7. Visual language

The shared family branding remains:

- blue-to-teal icon gradient `#3689e6 → #0e9a83`;
- white structural geometry;
- warm-yellow focal accent `#f9c440`;
- restrained neutral application surfaces.

Brand colours are not a scientific categorical scale. Charts and network/stock-flow views must combine colour with direct labels, line patterns, symbols or exact-value views.

The preferred web type stack starts with Inter and falls back to system sans-serif. Native builds use the platform system font. Typography, spacing and focus tokens are machine-readable in `model/registries/design_tokens.json`.

## 8. Accessibility

Target: WCAG 2.2 AA for the web application.

At minimum:

- text contrast meets AA;
- keyboard focus is visible and not obscured;
- controls remain operable without a mouse;
- hover content is supplementary, not the only access path;
- selection and status are not encoded by colour alone;
- text can resize without losing content or functionality;
- headings and labels describe purpose clearly.

## 9. Repository / landing-page grammar

The shared repository presentation order is:

1. centered icon;
2. centered title;
3. version;
4. concise description;
5. one primary Web-app launch control **only after a verified public deployment exists**;
6. concise platform/language/stage/licence badges;
7. model-specific visual when a truthful model view exists;
8. explanation of the model and current scientific stage;
9. data and provenance;
10. theory / learning material;
11. validation / reconciliation;
12. installation / development entry points;
13. limitations;
14. licence.

A planned feature must never be presented as available merely to make the three repositories look symmetrical.

## 10. Current conformance state

Alpha 0.2.1a0 applies the v1.1 semantic/design contract before the full browser application exists. Therefore this pass standardizes:

- default language and canonical labels;
- design tokens;
- adaptive workspace contract;
- repository presentation;
- theory/dashboard responsibilities;
- accessibility requirements;
- web/native continuity.

It deliberately does **not** invent a screenshot, interactive model view, simulation or deployment that the project has not implemented yet.
