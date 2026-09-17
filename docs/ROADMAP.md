# Roadmap to v1

This roadmap is a sequence of scientific/product gates, not a promise of calendar dates.

## 0.1.x — Foundation

Project constitution, system boundary, bilingual contract, canonical registries, package skeleton, CI and methodological invariants.

Exit gate: definitions and architecture are stable enough to begin numerical population without semantic drift.

## 0.2.x — Accounting Spine

Priority sequence: `F3 -> F2 -> F4 -> F8 -> F5 -> F6`, with F7 added where material. Build bilateral From-Whom-to-Whom matrices, balance-sheet positions, B9F and reconciliation logs.

Exit gate: benchmark 2025 accounting structure is internally auditable; unresolved cells are explicit rather than imputed silently.

### 0.2.1a0 — InfoClar Model Suite Design Standard v1.1 alignment

Cross-cutting product uniformization after the Accounting Spine gate and before the next scientific module. Standardize EN-default/RO-switch product language, shared design tokens, adaptive 2×2 workspace grammar, Theory/Learn integration, repository presentation and accessibility requirements while preserving model-specific scientific visualization and all accounting semantics.

Exit gate: product contracts are internally consistent and CI-verified; the uniformization layer cannot alter scientific results.

## 0.3.x — Dynamic Core

Convert the validated conceptual map into executable stocks, flows, auxiliaries, feedbacks and delays. Introduce dimensional-consistency and extreme-condition tests.

Exit gate: the dynamic model executes without violating its accounting and dimensional contracts.

## 0.4.x — Empirical Dynamics

Add evidence-traceable behavioural mechanisms for real-economy, credit, sovereign, monetary, risk, FX and refinancing channels. Every mechanism is classified `ACTIVATED`, `CANDIDATE`, `DEFERRED` or `REJECTED`; an `ACTIVATED` form is admitted to calibration but is not considered calibrated or causal.

Exit gate: every in-scope behavioural mechanism has a functional form or explicit deferral/rejection rationale, sources/evidence, observables, parameter/estimation plan, limitations and rejection/degradation criteria. No empirical coefficient is invented merely to close the milestone.

## 0.5.x — Calibration & Validation

Historical reproduction, parameter assessment, practical identifiability diagnostics, sensitivity, time-respecting multi-origin or holdout tests where data permit, comparisons with simpler baselines and explicit uncertainty.

Calibration data, structural-selection data and final evaluation/holdout data are separate roles. Model/candidate selection may use only calibration and structural-selection information. Once final evaluation data have been inspected, they may not later be described as an independent holdout for a revised model.

Convergence, in-sample goodness-of-fit or historical reproduction are not sufficient evidence of predictive validity or causality.

Exit gate: performance, uncertainty, identifiability and limitations are documented separately from software correctness; mechanisms that fail the empirical gates are degraded/rejected rather than protected by added complexity.

## 0.6.x — Interactive Web Simulator

After a compute benchmark, enable controlled in-browser simulation while preserving one scientific implementation. Add exact-value tables, exports and reproducibility metadata. This stage begins only if Alpha 0.5 establishes a scientifically defensible validated reference model for the capabilities exposed.

## 0.7.x — Scenario Laboratory

Rate, fiscal, FX, credit, sovereign-yield, EU-funds and composite shocks. Expose the mechanism path alongside numerical outcomes.

## 0.8.x — Policy Laboratory

Compare intervention bundles under explicit assumptions and objectives. Present trade-offs, uncertainty and sensitivity; do not hide model dependence behind a single score.

## 0.9.x — Scientific & UX Freeze

Stabilize schemas, terminology, equations, reference scenarios, validation outputs, bilingual content, accessibility and web navigation. The web application becomes the reference product contract.

## Late 0.9.x — Native Port

Introduce GTK/Granite/Meson/Flatpak for elementary OS, using the then-supported SDK/runtime at that future stage. Preserve the web application and verify numerical equivalence.

## 1.0.0 — Mature release

Acceptance requires, within the model's declared scope:

- accounting consistency;
- dynamic and dimensional consistency;
- empirical grounding and documented validation;
- data/equation provenance;
- reproducibility;
- understandable EN/RO explanations;
- uncertainty and limitation disclosure;
- verified cross-platform web application;
- reproducible elementary OS Flatpak;
- reference-output equivalence across scientific core, web and native application.
