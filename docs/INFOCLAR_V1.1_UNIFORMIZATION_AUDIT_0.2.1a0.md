# Alpha 0.2.1a0 — InfoClar Model Suite v1.1 uniformization audit

Date: 2026-09-17

## Purpose

This audit verifies that the cross-project uniformization pass changes product presentation and interaction contracts without changing Romania Macro-Financial Dynamics scientific semantics.

## Conformance checks

### Language — PASS

- default UI language: EN;
- persistent alternative: RO;
- canonical labels contain both languages;
- stable scientific IDs remain language-neutral.

### Desktop information architecture — PASS

The canonical workspace is an asymmetric 2×2 grid:

- dominant model/mechanism workspace;
- contextual Theory/Learn panel;
- major-indicator dashboard;
- auxiliary details panel.

### Responsive behaviour — PASS

Small-screen order is `model → theory → dashboard → auxiliary`. Page-level horizontal scrolling is prohibited; scientific diagrams may use internal pan/zoom only where structurally necessary.

### Shared design system — PASS

Machine-readable tokens cover:

- typography;
- spacing;
- radii and surfaces;
- brand accents;
- buttons/badges/tooltips/cards;
- focus and selection states;
- legends/navigation;
- scientific-visualization accessibility.

### Model-specific representation — PASS

The standard explicitly preserves stock-flow/sector diagrams, WTWTW/Flow-of-Funds matrices, empirical graphs and major macro-financial indicators. It does not import World3 trajectories or Cognitive Epistemic Model diagrams as a generic template.

### Theory / Learn — PASS

Theory is specified as both a complete reader and a contextual surface linked to selected sectors, instruments, matrix cells, graphs and later mechanisms, with provenance links.

### Repository presentation — PASS

The README follows the suite sequence while refusing to fabricate a model screenshot or clickable Web-app button before a verified implementation/deployment exists.

### Accessibility — PASS AS CONTRACT

The web target is WCAG 2.2 AA. The contract requires visible keyboard focus, no colour-only scientific meaning, exact-value alternatives and accessible responsive behaviour. Full runtime accessibility testing becomes possible once the browser UI exists.

### Scientific invariance — PASS

Uniformization is explicitly prohibited from changing:

- Accounting Spine values;
- missing-data statuses;
- equations;
- accounting definitions;
- source provenance;
- reconciliation rules;
- validation results.

The only amended model-level contract is the **product display language default** from RO to EN, which is non-scientific.

## Exit condition

Alpha 0.2.1a0 is ready for integration when repository CI passes all foundation, accounting-spine and InfoClar design-contract tests.

After integration, the next scientific milestone is **Alpha 0.3 — Dynamic Core**. That stage introduces causal/dynamic modelling choices and is therefore the next point at which a genuine scientific-direction decision may be required.
