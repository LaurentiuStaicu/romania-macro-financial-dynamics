# Changelog

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
- establishes the RO/EN contract with Romanian as default;
- establishes the web-first, native-near-v1 platform sequence;
- establishes the shared World3/Cognitive visual-family palette with a distinct macro-financial icon;
- aligns repository presentation with Cognitive Epistemic Model: centered icon/title/description, status badges and a launch-style primary control;
- keeps the launch control non-clickable until a CI-verified public web deployment exists;
- adds canonical bilingual product labels so future views cannot drift in user-facing terminology;
- adds canonical sector, financial-instrument and model-contract registries;
- adds a minimal installable Python package and foundation tests;
- records F3 bilateral government securities as the next empirical gate.
