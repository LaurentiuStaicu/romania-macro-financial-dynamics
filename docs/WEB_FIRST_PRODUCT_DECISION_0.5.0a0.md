# Web-first product decision — Alpha 0.5.0a0

Date: 2026-09-17

## Decision

InfoClar is the primary reference interface for Romania Macro-Financial Dynamics from Alpha 0.5 through scientific/product maturation to v1.

This means the browser application develops continuously alongside the scientific model rather than being postponed until a late UI phase. The shared InfoClar 2×2 surface progressively receives:

- the model-specific macro-financial stock-flow/sector representation;
- contextual Theory/Learn;
- empirical/reconciliation/calibration/validation dashboards;
- source, provenance, exact-value and limitation information;
- later simulation/scenario/policy controls only after their scientific gates are met.

## Capability truthfulness

The existence of a web surface does not imply that every roadmap capability is active. Alpha 0.5 implements a read-only scientific interface because zero behavioural mechanisms currently satisfy the validated-reference gate.

The application must show failed validation and uncertainty as first-class content rather than hiding them to make the product appear more complete.

## Native boundary

No Flatpak/native implementation begins during current scientific milestones. Native elementary OS development is deferred to late 0.9.x / near v1, after InfoClar web and the scientific contracts are mature.

The future native application will consume the same canonical scientific outputs and must demonstrate numerical/reference-output equivalence. It may not contain a forked economic model.

## Accessibility

The web reference interface targets WCAG 2.2 AA. As functionality grows, controls must remain keyboard operable, focus must remain visible/not obscured, navigation must be predictable and changes in scientific status must be communicated in text/semantics rather than colour alone.

## Repository implication

`web/` is now product source code, not a placeholder documentation directory. `native/` intentionally remains absent.
