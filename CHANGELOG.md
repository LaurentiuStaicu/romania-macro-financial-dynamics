# Changelog

## 0.3.0a0 — Dynamic Core

Accounting-constrained executable System Dynamics substrate.

- adds canonical bilateral dynamic positions indexed by holder × issuer × instrument;
- structurally derives holder assets and issuer liabilities from one represented position, enforcing double-entry conservation;
- implements the financial stock identity for period amounts and explicit rate × time updates;
- adopts year as the canonical simulation-time unit and 0.25 year as the default quarterly reference step;
- adds a guarded Accounting Spine → dynamics bridge that rejects `TBD`, source-only and duplicate cells rather than treating missing/ambiguous data as zero;
- adds explicit-Euler structural stepping and a reusable first-order delay primitive;
- registers sovereign, credit, monetary and external feedback candidates while keeping every behavioural loop quantitatively inactive;
- adds a machine-readable dimensional registry for stock, flow-rate, time, delay and dimensionless variables;
- adds the stage-specific InfoClar v1.1 presentation binding without modifying the shared v1.1 workspace/design foundations;
- fixes the central scientific view as a macro-financial stock-flow/sector network with position, transaction, revaluation/other-change and candidate-feedback layers;
- binds empirical/reconciliation indicators, contextual Theory/Learn and auxiliary source/verification/limitation details to the common 2×2 architecture;
- adds canonical Python presentation payload builders so future web/native UIs consume scientific state rather than reimplement accounting logic;
- adds dimensional, zero-flow, large-value, conservation, boundary, delay steady-state, duplicate/incomplete-initialization, presentation-contract and integration-error-convergence tests;
- records explicitly that the user's exploratory schema/draft is not a repository artifact;
- documents that consumption, investment, credit, fiscal, monetary-policy, risk/default, FX and refinancing response equations remain deferred to Alpha 0.4 Empirical Dynamics;
- advances the software version to `0.3.0a0` without claiming forecasting or policy-evaluation capability.

## 0.2.1a0 — InfoClar Model Suite Design Standard v1.1 alignment

Product-family uniformization after the Accounting Spine milestone.

- adopts English as the default product language with persistent Romanian switching;
- adds canonical InfoClar v1.1 design tokens for typography, spacing, neutral surfaces, interaction, focus, components and scientific-visualization accessibility;
- adds the adaptive asymmetric 2×2 workspace contract: model / theory / dashboard / auxiliary;
- preserves macro-financial stock-flow, sector, Flow-of-Funds and real-data views as the model-specific visualization grammar;
- defines contextual Theory/Learn behaviour linked to selected scientific objects and provenance;
- expands canonical EN/RO product labels and navigation vocabulary;
- aligns repository presentation order, status controls and web/native semantic continuity across the InfoClar family;
- targets WCAG 2.2 AA and prohibits colour-only scientific meaning;
- explicitly prevents the uniformization layer from altering scientific results or accounting semantics;
- does not fabricate a web deployment, model screenshot or unavailable Dynamics/Simulation/Scenario capability.

## 0.2.0a0 — Accounting Spine

Auditable L1 accounting/SFC spine.

- adds canonical 6×6 holder-by-issuer matrix address spaces for F3, F2, F4, F8, F5, F6 and F7;
- separates 31.12.2025 closing positions from calendar-2025 financial transactions;
- adds explicit `TBD`, `SOURCE_SERIES_IDENTIFIED`, `OBSERVED`, `DERIVED` and `NOT_APPLICABLE` cell semantics;
- prohibits zero-as-missing and silent/forced accounting closure;
- adds B9F and asset/liability reconciliation helpers that refuse incomplete inputs;
- registers ECB QSA as the primary WTWTW financial-account source and Eurostat government financial accounts / ECB GFS as separate control layers;
- records verified Romanian source keys and empirical controls without relabelling aggregates or partial-maturity series as complete bilateral cells;
- adds the 2025 reconciliation ledger and Alpha 0.2 exit audit;
- adds accounting-spine tests and advances the software version to `0.2.0a0`;
- carries unresolved bilateral cells forward explicitly for later empirical coverage rather than inventing allocations.

## 0.1.0a0 — Project Constitution & Architecture

Foundation candidate.

- defines the project mission and system boundary;
- establishes explicit BNR/S121 handling to avoid double counting when the central bank is shown separately;
- establishes four canonical registries;
- records benchmark stock/flow dates;
- establishes the initial RO/EN contract;
- establishes the web-first, native-near-v1 platform sequence;
- establishes the shared World3/Cognitive visual-family palette with a distinct macro-financial icon;
- aligns repository presentation with Cognitive Epistemic Model: centered icon/title/description, status badges and a launch-style primary control;
- keeps the launch control non-clickable until a CI-verified public web deployment exists;
- adds canonical bilingual product labels so future views cannot drift in user-facing terminology;
- adds canonical sector, financial-instrument and model-contract registries;
- adds a minimal installable Python package and foundation tests;
- records F3 bilateral government securities as the next empirical gate.
