# WORLD3 VISUAL ALIGNMENT AUDIT

Canonical visual source: `LaurentiuStaicu/empirical-world3-dynamics`, PR #10, branch `product/world3-usefulness-recovery`, head `51e236b61a0ec169bc8f28d4f8192e450ab6bd6d`, `web/src/style.css`.

Scope: product shell and design-system recovery only. Accounting Spine, Dynamic Core, Flow-of-Funds semantics, datasets, indicators, vulnerability content, Theory/Learn content, accounting stress semantics, candidate mechanisms, validation status, Alpha 0.6 NO-GO and the count of validated behavioural reference mechanisms remain frozen.

## Exact shared primitives

| property | World3 | Macro | match |
|---|---|---|---|
| font family | `Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif` | same | MATCH |
| root/page background | `#f3f5f7` | `#f3f5f7` | MATCH |
| surface | `#ffffff` | `#ffffff` | MATCH |
| primary text | `#222a34` | `#222a34` | MATCH |
| muted text | `#667180` | `#667180` | MATCH |
| border | `#dce1e7` | `#dce1e7` | MATCH |
| link | `#326b9f` | `#326b9f` | MATCH |
| shadow | `0 10px 35px rgba(31,42,55,.07)` | equivalent canonical token `0 10px 35px rgba(31, 42, 55, 0.07)` | MATCH |
| panel radius | `14px` | `14px` | MATCH |
| control border | `#ccd3db` | `#ccd3db` | MATCH |
| control radius | `9px` | `9px` | MATCH |
| control hover | `#f4f6f8` | `#f4f6f8` | MATCH |
| active language background | `#e8ebf0` | `#e8ebf0` | MATCH |
| active language text | `#20262e` | `#20262e` | MATCH |
| header min-height | `72px` | `72px` | MATCH |
| header padding | `10px 24px` | `10px 24px` | MATCH |
| header gap | `20px` | `20px` | MATCH |
| brand gap | `12px` | `12px` | MATCH |
| brand icon | `42px × 42px` | `42px × 42px` | MATCH |
| title size | `18px` | `18px` | MATCH |
| subtitle size | `12px` | `12px` | MATCH |
| main max-width | `1680px` | `1680px` | MATCH |
| main padding | `18px 22px 44px` | `18px 22px 44px` | MATCH |
| primary panel gap | `16px` | `16px` | MATCH |
| question-band min-height | `54px` | `54px` | MATCH |
| question-band bottom margin | `16px` | `16px` | MATCH |
| mobile header padding | `9px 12px` | `9px 12px` | MATCH |
| mobile icon size | `36px` | `36px` | MATCH |
| mobile main padding | `12px 10px 28px` | `12px 10px 28px` | MATCH |
| mobile primary radius | `11px` | `11px` | MATCH |
| automatic dark mode | none | none | MATCH |

The machine-readable source of this table is `web/world3-visual-parity-contract.json`; regression tests enforce exact values rather than approximate similarity.

## Component and shell parity

- Global header uses the World3 Product Recovery `.product-header` / `.brand` / `.quiet` / `.lang` grammar.
- Macro-specific navigation chips were removed from the global header.
- Global page framing uses the same max-width, viewport margins, question band, surface geometry, border, shadow and spacing rhythm.
- Generic buttons, language switch, inputs and select controls use the same World3 component geometry.
- Automatic OS-driven dark mode was removed from Macro.
- Responsive breakpoints follow the World3 Product Recovery grammar at 1180, 980, 680 and 420 px.

## Intentional model-specific differences

Only domain-semantic differences remain intentional:

- World3 primary object: temporal `Trajectory Explorer`; Macro primary object: `Flow-of-Funds / Sectoral Balance-Sheet Explorer`.
- World3 scenario colours and turning-point markers are not copied into Macro.
- Macro retains semantic colours for observed/accounting flows, conceptual relations, candidate/deferred feedbacks and risk high/moderate/low.
- World3 chart controls are trajectory/scenario-specific; Macro retains STOCK / FLOW / FROM-WHOM-TO-WHOM, instrument layers and relationship inspection.
- World3 uses a chart-oriented control rail; Macro uses a sector/relationship contextual inspector.
- Vulnerability Monitor, Theory/Learn and Accounting Stress retain their existing scientific/content semantics while using the shared visual chrome and progressive-disclosure grammar.

## Six-viewport golden-master gate

Required exact viewport pairs:

- 1920×1080
- 1600×900
- 1440×900
- 1366×768
- 820×1180
- 390×844

CI builds World3 directly from canonical SHA `51e236b61a0ec169bc8f28d4f8192e450ab6bd6d`, renders both products at all six exact CSS viewports and generates side-by-side screenshots. It fails on horizontal page overflow, panel overlap, undersized generic controls, or computed shared-primitive differences.

## Final gate

- CSS parity: **PENDING CI**
- Functional / scientific non-regression CI: **PENDING CI**
- Human visual comparison: **PENDING SCREENSHOT INSPECTION**

`WORLD3 / MACRO VISUAL FAMILY ALIGNMENT = PENDING`

This report must be updated to PASS only after the generated side-by-side screenshots have been inspected. Green CI alone is not sufficient.
