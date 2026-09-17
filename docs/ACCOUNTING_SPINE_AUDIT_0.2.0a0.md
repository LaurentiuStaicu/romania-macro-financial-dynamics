# Alpha 0.2.0a0 — Accounting Spine exit audit

Date: 2026-09-17

## Scope

Alpha 0.2 establishes the L1 accounting/SFC spine required before dynamic causal equations are introduced. The milestone is an auditable accounting structure, not a claim that every Romanian bilateral financial-account cell is published or currently recoverable from one source.

The canonical benchmark remains:

- closing positions: 31.12.2025 / 2025-Q4;
- annual financial transactions: 01.01.2025–31.12.2025;
- primary WTWTW basis: ESA 2010 quarterly financial accounts, non-consolidated;
- canonical sectors: H, C, F, G, X and BNR;
- priority instruments: F3 → F2 → F4 → F8 → F5 → F6, with F7 retained explicitly for materiality assessment.

## Exit-gate checks

### 1. Bilateral address space — PASS

Every priority instrument has separate stock and flow matrix specifications. Each specification expands deterministically to all 36 holder × issuer cells. Missing cells are explicit through the matrix default rule rather than omitted.

### 2. Missing-data discipline — PASS

`TBD` and `SOURCE_SERIES_IDENTIFIED` cells cannot carry numeric values. Zero cannot be used as a missing value. Partial source coverage cannot be promoted to `OBSERVED` without a definitionally matched value.

### 3. Stock/flow separation — PASS

Closing positions and annual 2025 transactions are separate objects. Annual flows are not computed from stock differences. Quarterly transactions may only be aggregated after a definition check.

### 4. Source/provenance layer — PASS WITH PARTIAL EMPIRICAL COVERAGE

The source registry records ECB QSA as the primary WTWTW financial-account source and separates Eurostat government financial accounts / ECB GFS as control layers. Verified Romania series are stored with exact series keys and roles.

At this gate, some verified series are intentionally controls rather than bilateral observations. For example, consolidated Maastricht debt and a total-economy non-resident F3 aggregate are not silently converted into government WTWTW cells.

### 5. F3 first empirical gate — PASS AS AN AUDITABLE PARTIAL-COVERAGE GATE

The government/non-resident F3 source path is identified and explicitly records maturity limitations. The model does not fabricate the missing all-maturity bilateral value. The reconciliation ledger records why the liability-side and holder-side totals cannot yet be forced to close.

This satisfies the Alpha 0.2 contract because unresolved cells are explicit and auditable. It does **not** claim complete empirical F3 coverage.

### 6. Balance-sheet contract — PASS

Holder-side positions are assets; issuer-side positions are liabilities. Primary matrices are non-consolidated. Consolidated government-finance controls remain a separate layer.

### 7. B9F and reconciliation — PASS AS CONTRACT, NUMERIC VALUE TBD

B9F is implemented as net acquisition of financial assets minus net incurrence of liabilities. The helper refuses incomplete inputs. The 2025 numerical B9F remains `TBD` until all four quarterly transactions are retrieved under matched definitions. B9 and B9F are not forced to equality; the statistical discrepancy must remain explicit.

### 8. Forced closure — PASS

The reconciliation registry prohibits silent imputation and forced closure. Residuals are numeric only when both sides are available.

### 9. Software tests — REQUIRED CI GATE

The branch includes tests for the complete 6×6 address space, missing-value semantics, partial-source status, aggregate-control separation, B9F/reconciliation identities and forced-closure prohibition. The milestone is integrated only after repository CI is green.

## Scientific limitation carried forward

Alpha 0.2 closes the **accounting architecture and audit contract**. It does not transform unavailable or definitionally mismatched public data into synthetic exact observations. Later empirical-data population can improve coverage without changing the accounting semantics established here.

## Next stage

After CI and integration, apply **InfoClar Model Suite Design Standard v1.1** as a product-family uniformization pass. That pass must not alter the scientific model or numerical results. The next scientific milestone after uniformization is Alpha 0.3 Dynamic Core.
