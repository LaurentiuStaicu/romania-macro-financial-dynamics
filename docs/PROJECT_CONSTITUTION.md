# Project Constitution — Alpha 0.1.0a0

## 1. Mission

Build an empirical macro-financial model of Romania that is simultaneously accounting-consistent, dynamically explicit, numerically auditable and understandable to non-specialist users through a bilingual RO/EN application.

## 2. System boundary

Canonical top-level analytical nodes:

- `H` — households + NPISH;
- `C` — non-financial corporations, ESA S11;
- `F` — financial corporations excluding the central bank in presentation-level decompositions where BNR is shown separately;
- `G` — general government, ESA S13;
- `X` — rest of the world, ESA S2;
- `BNR` — central bank, ESA S121, shown separately for monetary-policy and monetary-infrastructure mechanisms.

Raw accounting data must retain official ESA sector definitions. When `BNR` is separated from `F`, aggregation logic must prevent double counting of S121 inside S12.

Romania resident economy is `S1`; the external counterpart is `S2`.

## 3. Time convention

Benchmark stock date: **31.12.2025**.

Benchmark annual-flow interval: **01.01.2025–31.12.2025**.

Later dynamic estimation should use the longest comparable quarterly series available, with higher-frequency data only where definitions remain compatible.

Never equate a period flow, a change in stock and an end-of-period stock.

## 4. Four canonical registries

1. **Concept Registry** — sectors, instruments, variables, mechanisms and definitions.
2. **Numeric/Data Registry** — value, period, unit, sector, instrument, source, series identifier, transformation and status.
3. **Reconciliation Registry** — accounting identities, counterpart tests, discrepancies and explanations.
4. **Equation & Assumption Registry** — stock/flow/auxiliary/exogenous type, equation, units, parameters, delays, evidence status and feedback-loop membership.

No UI may maintain an independent copy of scientific definitions that can drift from these canonical registries.

## 5. Accounting and causality are different layers

The model distinguishes:

- economic transactions and income flows;
- financial transactions (F2–F8 as applicable);
- stocks/balance-sheet positions;
- revaluations and other changes in volume;
- causal dependencies and feedback loops.

An accounting identity is not automatically a behavioural equation. A financial transaction is not automatically a causal feedback link.

## 6. Core stock identity

For an asset/liability stock represented through financial accounts:

`Closing stock = Opening stock + Transactions + Revaluations + Other changes in volume`

The exact source classification and sign convention must be registered before numerical reconciliation.

## 7. B9 and B9F

`B9` (net lending/net borrowing from non-financial accounts) and `B9F` (net acquisition of financial assets minus net incurrence of liabilities) are related but must not be forced to equality in raw published data.

The reconciliation discrepancy is tracked explicitly:

`SD = B9 - B9F`

## 8. Source hierarchy

For benchmark macro-financial data, prefer official primary sources:

1. Eurostat / ESA 2010;
2. ECB Data Portal / Quarterly Sector Accounts;
3. BNR;
4. Ministry of Finance and other official Romanian institutions;
5. secondary sources only as cross-checks or contextual evidence.

Approximate percentages must not be converted into purported exact ESA bilateral values.

## 9. Scientific-status contract

Every quantitative relation must be identifiable as one or more of:

- `ACCOUNTING_IDENTITY`;
- `OBSERVED_EMPIRICAL`;
- `BEHAVIOURAL_CANDIDATE`;
- `CALIBRATED_RELATION`;
- `ASSUMPTION`;
- `EXOGENOUS_INPUT`;
- `DIAGNOSTIC_ONLY`.

Software correctness and empirical validity are separate gates.

## 10. Bilingual contract

Romanian is the default product language and English is a first-class equivalent language.

Stable IDs, code symbols, equations, data keys and schema fields are language-neutral. Human-readable labels, definitions, explanations, limitations and UI strings must have `ro` and `en` forms where user-facing.

A translation must preserve the scientific meaning rather than follow literal word order.

## 11. Platform contract

The scientific core is authoritative and interface-independent.

Development order:

`scientific core -> verified web application -> native elementary OS Flatpak near v1`

The Flatpak must not become an independent scientific implementation. Equivalent reference scenarios must produce numerically equivalent outputs across scientific core, web and native application within declared tolerances.

## 12. Interoperability

XMILE is reserved as a future import/export interoperability format for System Dynamics models. It is not the canonical editable source during the foundation stage.

## 13. First empirical gate

After Alpha 0.1.0a0 closes, the first task is bilateral F3 for general government:

- stocks at 31.12.2025;
- transactions during 2025;
- holder/counterpart sector;
- maturity where available;
- resident/non-resident split;
- consolidation status;
- explicit source/series identifiers;
- reconciliation of government F3 liabilities against counterpart holdings under matched definitions.

Unknown values remain `TBD`.
