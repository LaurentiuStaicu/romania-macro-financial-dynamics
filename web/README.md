# Web application — InfoClar Model Suite v1.1 contract

The browser application is not yet implemented in Alpha 0.2.1a0. This directory records the reference product contract that future web work must satisfy without duplicating the scientific model.

## Product contract

- cross-platform browser access;
- English default with persistent `EN / RO` switching;
- canonical scientific registries/results imported from the model layer;
- no independent JavaScript/TypeScript copy of scientific equations during early development;
- accessible exact-value tables alongside charts and matrices;
- theory/mechanism/provenance views before policy-control surfaces;
- GitHub Pages deployment only from a CI-verified artifact once a usable alpha exists;
- WCAG 2.2 AA target.

## Workspace

Desktop uses an asymmetric 2×2 layout:

- top-left, dominant: stock-flow/sector model, Flow-of-Funds matrix and contextual empirical graphs;
- top-right: Theory / Learn / contextual explanation;
- bottom-left: major indicators and reconciliation/data-status dashboard;
- bottom-right: sources, validation, limitations and selection details.

On small screens the panels stack `model → theory → dashboard → auxiliary`.

The Theory/Learn surface must react to the selected scientific object and deep-link to definitions, mechanisms and provenance. It is not a detached documentation tab.

## Canonical resources

- design tokens: `../model/registries/design_tokens.json`;
- workspace contract: `../model/registries/workspace_contract.json`;
- product labels: `../model/registries/product_labels.json`;
- standard profile: `../docs/INFOCLAR_MODEL_SUITE_DESIGN_STANDARD_V1.1.md`.

A planned section must not be rendered as available before implementation. Alpha 0.2.x can expose understanding, system-map, Flow-of-Funds, validation/reconciliation and data/source surfaces; Dynamics, Simulation and Scenarios remain future capabilities.
