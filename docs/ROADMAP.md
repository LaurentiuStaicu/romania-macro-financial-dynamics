# Roadmap to v1

This roadmap is a sequence of scientific/product gates, not a promise of calendar dates.

## Cross-cutting product rule — web first

InfoClar is the **reference product interface**, not merely a design specification. From Alpha 0.5 onward, every major scientific milestone should evolve the same browser surface where scientifically meaningful: the model-specific stock-flow/sector visualization, contextual Theory/Learn, empirical dashboard and Auxiliary source/validation/limitations panel.

The browser must remain truthful about capability. Read-only understanding/validation surfaces can mature before simulation; a simulator, scenario laboratory or policy laboratory may appear only when its corresponding scientific gate is satisfied.

Native GTK/Granite/Flatpak development is deferred until the web application and scientific contracts are mature **at or near v1**. Native work must later consume the same canonical scientific outputs and prove numerical equivalence rather than becoming a parallel model implementation.

## 0.1.x — Foundation

Project constitution, system boundary, bilingual contract, canonical registries, package skeleton, CI and methodological invariants.

Exit gate: definitions and architecture are stable enough to begin numerical population without semantic drift.

## 0.2.x — Accounting Spine

Priority sequence: `F3 -> F2 -> F4 -> F8 -> F5 -> F6`, with F7 added where material. Build bilateral From-Whom-to-Whom matrices, balance-sheet positions, B9F and reconciliation logs.

Exit gate: benchmark 2025 accounting structure is internally auditable; unresolved cells are explicit rather than imputed silently.

### 0.2.1a0 — InfoClar Model Suite Design Standard v1.1 alignment

Cross-cutting product uniformization after the Accounting Spine gate. Standardize EN-default/RO-switch product language, shared design tokens, adaptive 2×2 workspace grammar, Theory/Learn integration, repository presentation and accessibility requirements while preserving model-specific scientific visualization and all accounting semantics.

Exit gate: product contracts are internally consistent and CI-verified; the uniformization layer cannot alter scientific results.

## 0.3.x — Dynamic Core

Convert the validated conceptual map into executable stocks, flows, auxiliaries, feedbacks and delays. Introduce dimensional-consistency and extreme-condition tests.

Exit gate: the dynamic model executes without violating its accounting and dimensional contracts.

## 0.4.x — Empirical Dynamics

Add evidence-traceable behavioural mechanisms for real-economy, credit, sovereign, monetary, risk, FX and refinancing channels. Every mechanism is classified `ACTIVATED`, `CANDIDATE`, `DEFERRED` or `REJECTED`; an `ACTIVATED` form is admitted to calibration but is not considered calibrated or causal.

Exit gate: every in-scope behavioural mechanism has a functional form or explicit deferral/rejection rationale, sources/evidence, observables, parameter/estimation plan, limitations and rejection/degradation criteria. No empirical coefficient is invented merely to close the milestone.

## 0.5.x — Calibration & Validation + first implemented InfoClar surface

Scientific scope: historical reproduction where identifiable, parameter assessment, practical-identifiability diagnostics, sensitivity, time-respecting multi-origin or holdout tests where data permit, comparisons with simpler baselines and explicit uncertainty.

Calibration data, structural-selection data and final evaluation/holdout data are separate roles. Model/candidate selection may use only calibration and structural-selection information. Once final evaluation data have been inspected, they may not later be described as an independent holdout for a revised model.

Convergence, in-sample goodness-of-fit or historical reproduction are not sufficient evidence of predictive validity or causality.

Product scope: instantiate InfoClar as the real reference browser interface, initially read-only, using the common 2×2 surface and model-specific macro-financial diagram. The UI consumes canonical scientific snapshots/results and exposes validation failures as prominently as successes.

Exit gate: performance, uncertainty, identifiability and limitations are documented separately from software correctness; mechanisms that fail empirical gates are degraded/rejected rather than protected by added complexity. The InfoClar web shell is real, accessible and linked to canonical scientific status without implying simulation capability.

## 0.6.x — Interactive Web Simulator

Potential next product stage, **not automatic after 0.5**. Controlled in-browser simulation may be enabled only for behavioural capabilities that have a scientifically defensible validated reference model, while preserving one scientific implementation. Add exact-value tables, exports and reproducibility metadata.

If Alpha 0.5 has no validated behavioural reference mechanism, InfoClar may continue evolving as a structural/empirical/theory interface, but behavioural simulation remains gated until new data/model evidence or an explicit scope decision resolves the scientific block.

## 0.7.x — Scenario Laboratory

Rate, fiscal, FX, credit, sovereign-yield, EU-funds and composite shocks. Expose the mechanism path alongside numerical outcomes. Scenario controls must be unavailable for mechanisms that remain unvalidated or explicitly deferred unless clearly designated as assumption-driven exploratory experiments.

## 0.8.x — Policy Laboratory

Compare intervention bundles under explicit assumptions and objectives. Present trade-offs, uncertainty and sensitivity; do not hide model dependence behind a single score.

## 0.9.x — Scientific & UX Freeze

Stabilize schemas, terminology, equations, reference scenarios, validation outputs, bilingual content, accessibility and web navigation. By this point InfoClar is already the reference product; 0.9 freezes and hardens it rather than introducing the web application for the first time.

## Late 0.9.x / near v1 — Native Port

Only after the web reference product and scientific contracts have matured, introduce GTK/Granite/Meson/Flatpak for elementary OS using the then-supported SDK/runtime. Preserve the web application and verify numerical/reference-output equivalence. Do not fork model equations into platform-specific UI code.

## 1.0.0 — Mature release

Acceptance requires, within the model's declared scope:

- accounting consistency;
- dynamic and dimensional consistency;
- empirical grounding and documented validation;
- data/equation provenance;
- reproducibility;
- understandable EN/RO explanations;
- uncertainty and limitation disclosure;
- verified cross-platform InfoClar web application as the primary interface;
- reproducible elementary OS Flatpak produced only after web/scientific maturation;
- reference-output equivalence across scientific core, web and native application.
