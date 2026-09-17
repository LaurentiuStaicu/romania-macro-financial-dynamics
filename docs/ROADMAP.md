# Roadmap to v1

This roadmap is a sequence of scientific/product gates, not a promise of calendar dates.

## Cross-cutting product rule — web first

InfoClar is the **reference product interface**, not merely a design specification. Every major scientific milestone evolves the same browser surface where scientifically meaningful: the model-specific stock-flow/sector visualization, contextual Theory/Learn, empirical dashboard and Auxiliary source/validation/limitations panel.

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

## 0.3.x — Dynamic Core

Executable stocks, flows, auxiliaries, feedback skeletons and delays under Accounting Spine, dimensional-consistency, conservation, extreme-condition and integration-error tests.

## 0.4.x — Empirical Dynamics

Evidence-traceable behavioural mechanisms for real-economy, credit, sovereign, monetary, risk, FX and refinancing channels. Every mechanism is classified `ACTIVATED`, `CANDIDATE`, `DEFERRED` or `REJECTED`; activation is admission to calibration, not a claim of calibration or causality.

## 0.5.0a0 — Calibration & Validation + first implemented InfoClar surface

The first time-respecting validation cycle correctly closes with **zero validated behavioural reference mechanisms**. The monetary three-parameter partial-adjustment form is weakly identified and loses to simple baselines during structural selection. The aggregate government refinancing parameter is not definitionally point-identified. Behavioural Alpha 0.6 becomes **NO-GO**.

At the same milestone InfoClar becomes the real read-only reference web interface rather than only a design contract.

## 0.5.1a0 — Validation Recovery / Empirical Basis Expansion

Recovery is attempted without weakening the 0.5 gate.

Scientific work:

- reproducibly capture a long BIS policy-rate vintage and complete ECB MIR household/NFC lending-rate targets;
- freeze new calibration / structural-selection / final-evaluation roles before re-estimation;
- reserve future observations prospectively and permanently retire the inspected Alpha 0.5 holdout from independent-validation use;
- preregister only parsimonious pass-through candidates plus persistence and constant-spread baselines;
- open a fresh holdout only for a form that passes every structural-selection gate;
- reconcile MoF maturity, refixing, portfolio-cost, auction-yield and interest-expenditure definitions before attempting debt-repricing estimation.

Outcome:

- household one-parameter contemporaneous delta-policy pass-through passes structural selection but the fresh 2025 holdout contains zero policy-rate changes, making the candidate identical to persistence and causing failure of the preregistered final-evaluation improvement gate;
- NFC parsimonious forms fail before holdout, so the NFC final holdout remains unopened;
- government refinancing/effective-rate remains `DEFERRED` because the aggregate equation cannot match refixing events and marginal rates across instrument/currency/fixed-floating boundaries without synthetic allocation;
- newly validated reference mechanisms remain **0**;
- Alpha 0.6 behavioural simulator gate remains **NO-GO**;
- InfoClar web remains **GO** and is updated with the expanded data, evidence and limitations while staying read-only for behavioural simulation.

Exit gate: **PASS as a completed negative recovery result**. Failure to produce a VALIDATED mechanism is not a milestone failure when the prospective scientific gates are followed.

### Next justified empirical path inside 0.5.x

Before Alpha 0.6 can be reconsidered, at least one of these must produce a new prospective validation result:

1. **Prospective Monetary Confirmation** — preserve MIR observations from 2026-08 onward and evaluate the already frozen household delta-policy form only after a genuinely new policy-rate easing/tightening event provides identifying variation. Future observations may not be used to revise the form before their first confirmation test.
2. **Government Repricing Ledger** — assemble instrument × currency × fixed/floating opening principal, maturity/reset dates, repriced principal and matched old/new effective rates, then reproduce published MoF portfolio-cost measures without synthetic allocation.

Other Alpha 0.4 candidates require their own newly preregistered data/selection cycles; they are not opened merely because the priority mechanisms fail.

## 0.6.x — Interactive Web Simulator

**Currently gated / not started.** Controlled in-browser behavioural simulation may be enabled only after at least one scientifically defensible reference mechanism passes a prospective validation cycle appropriate to its exposed capability.

If no mechanism is validated, InfoClar continues evolving as a structural/empirical/theory/validation interface; simulator controls must remain absent or disabled rather than exposing unvalidated behaviour.

## 0.7.x — Scenario Laboratory

Rate, fiscal, FX, credit, sovereign-yield, EU-funds and composite shocks. Expose mechanism paths alongside numerical outcomes. Scenario controls must not silently promote unvalidated/deferred mechanisms.

## 0.8.x — Policy Laboratory

Compare intervention bundles under explicit assumptions and objectives. Present trade-offs, uncertainty and sensitivity; do not hide model dependence behind a single score.

## 0.9.x — Scientific & UX Freeze

Stabilize schemas, terminology, equations, reference scenarios, validation outputs, bilingual content, accessibility and web navigation. InfoClar is already the reference product; 0.9 freezes and hardens it.

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
