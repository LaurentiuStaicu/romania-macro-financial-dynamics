# Product Presentation Contract

This document defines the shared presentation grammar for Romania Macro-Financial Dynamics and is intentionally aligned with the user's Cognitive Epistemic Model and World3 Empirical family.

## Repository / landing presentation

Use the following order consistently:

1. centered application icon;
2. centered product title;
3. concise centered bilingual-compatible description;
4. centered status badges;
5. one centered primary launch button only after a verified public web deployment exists;
6. current scientific-development status and limitations;
7. user-facing capabilities and scientific scope.

### Status badges

Keep badges concise and stable. The initial set is:

- software version;
- development stage;
- available application/platform;
- languages RO/EN;
- elementary OS Flatpak status;
- code license.

Use the same visual family as Cognitive Epistemic Model where the semantics match:

- version: `#4e9a06`;
- alpha/stage: `#e5a50a`;
- Web/application: `#4a90d9`;
- elementary OS / Flatpak: `#64baff`;
- bilingual/product-family accent: teal `#0e9a83`;
- primary launch control: deep teal `#087F73`, `for-the-badge` style.

A badge must describe reality. Do not label Web or Flatpak as available until a verified artifact/deployment exists.

## Primary launch button

When GitHub Pages is deployed from a CI-verified artifact, expose exactly one prominent centered launch control in the README/landing presentation:

- RO: `Deschide aplicația`
- EN: `Open app`
- combined repository label: `Deschide aplicația / Open app`

The control must target the verified public web deployment, not a branch preview or an unverified build. Before deployment, show only a development-status badge; do not create a misleading launch link.

## Canonical user-facing labels

Scientific IDs remain language-neutral. Any label that appears in more than one view must be canonical rather than re-declared by each view. The future web application should follow the same pattern already used by Cognitive Epistemic Model's shared `labels.ts` layer.

Each shared label record must provide RO and EN forms and, where useful, a short form for constrained controls. Romanian is the default UI language.

Examples of future canonical navigation concepts:

| ID | RO | EN |
|---|---|---|
| `understand` | Înțelege | Understand |
| `system_map` | Harta sistemului | System map |
| `flow_of_funds` | Fluxuri financiare | Flow of funds |
| `dynamics` | Dinamică | Dynamics |
| `simulation` | Simulare | Simulation |
| `scenarios` | Scenarii | Scenarios |
| `validation` | Validare | Validation |
| `data_sources` | Date și surse | Data & sources |

These are product labels, not scientific variables.

## Web/native continuity

The future elementary OS application should preserve product identity and terminology while using native GTK/Granite controls rather than copying web CSS. Icon, semantic naming, major information architecture and scientific outputs must remain recognizable across Web and Flatpak.

## Cross-project family

Romania Macro-Financial Dynamics, Cognitive Epistemic Model and World3 Empirical should feel like related applications without becoming visually or semantically indistinguishable. Shared family elements include the blue-to-teal icon background, restrained typography, centered repository presentation, status-badge grammar and a common primary-launch treatment. Each application keeps a domain-specific icon symbol and its own information architecture.
