# Product Presentation Contract — InfoClar Model Suite v1.1

Romania Macro-Financial Dynamics shares a product-family grammar with Cognitive Epistemic Model and World3 Empirical while preserving its own macro-financial scientific representation.

## Repository / landing presentation

Use this order consistently:

1. centered application icon;
2. centered product title;
3. software version;
4. concise centered description;
5. one centered primary Web-app launch control only after a verified public deployment exists;
6. concise status badges;
7. a truthful model-specific visual once such a view exists;
8. model explanation and current scientific stage;
9. data and provenance;
10. theory / learning material;
11. validation and reconciliation;
12. installation / development entry points;
13. limitations;
14. licence.

Do not invent screenshots, model views, deployments or capabilities merely to keep the family visually symmetrical.

## Status badges

Keep badges concise and factual. The common set is:

- software version;
- development stage;
- available application/platform;
- languages EN/RO;
- elementary OS Flatpak status;
- code licence.

Shared semantics retain these family colours:

- version: `#4e9a06`;
- alpha/stage: `#e5a50a`;
- Web/application: `#4a90d9`;
- elementary OS / Flatpak: `#64baff`;
- bilingual/product-family accent: `#0e9a83`;
- primary launch control: `#087F73`, `for-the-badge` style.

A badge must describe reality. Web and Flatpak may not be labelled available until verified artifacts/deployments exist.

## Primary launch control

When GitHub Pages is deployed from a CI-verified artifact, expose exactly one prominent centered launch control:

- EN: `Open app`
- RO: `Deschide aplicația`

Before deployment, show a development-status control rather than a misleading link.

## Language contract

InfoClar Model Suite v1.1 uses **English as the default product language** and Romanian as a persistent first-class alternative. The header exposes a compact `EN / RO` switch.

Translations must preserve scientific meaning. Stable model IDs, equations, dataset keys and schema fields remain language-neutral.

## Canonical user-facing labels

Any repeated interface term comes from `model/registries/product_labels.json`, never from view-local copies. The shared long-term navigation vocabulary is:

| ID | EN | RO |
|---|---|---|
| `understand` | Understand | Înțelege |
| `system_map` | System map | Harta sistemului |
| `flow_of_funds` | Flow of funds | Fluxuri financiare |
| `dynamics` | Dynamics | Dinamică |
| `simulation` | Simulation | Simulare |
| `scenarios` | Scenarios | Scenarii |
| `validation` | Validation | Validare |
| `data_sources` | Data & sources | Date și surse |

Only implemented sections may be presented as active.

## Shared workspace grammar

Desktop uses the InfoClar v1.1 asymmetric 2×2 workspace:

- top-left, dominant: model / mechanisms;
- top-right: Theory / Learn / context;
- bottom-left: dashboard / major indicators;
- bottom-right: auxiliary details.

Small screens stack these areas. The complete machine-readable contract lives in `model/registries/workspace_contract.json`.

## Theory / Learn

The theory surface is detailed and connected to the scientific view. Selecting a sector, instrument, matrix cell, graph or later causal mechanism should expose the relevant explanation, definition and provenance. Concise interface chrome must not reduce scientific depth.

## Web/native continuity

The future elementary OS application preserves semantic naming, information architecture, scientific outputs and icon identity while using native GTK/Granite controls rather than copied web CSS. Web/native parity is semantic and scientific, not pixel parity.

## Cross-project family

The shared family includes restrained typography, spacing-led hierarchy, common interaction/status grammar, the blue-to-teal icon family and the same repository presentation sequence. Each application retains domain-specific symbols, diagrams, graphs and data views.

See `docs/INFOCLAR_MODEL_SUITE_DESIGN_STANDARD_V1.1.md`, `model/registries/design_tokens.json` and `model/registries/workspace_contract.json`.
