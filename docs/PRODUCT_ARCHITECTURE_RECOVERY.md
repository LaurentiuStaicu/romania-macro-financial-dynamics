# Product Architecture Recovery — Flow-of-Funds usefulness recovery

Date: 2026-09-17

## Product criterion

The reference web product must let a user see how finances circulate through the Romanian economy, who finances whom, who owes whom, where macro-financial vulnerabilities accumulate and how accounting exposures can propagate. A more elaborate version of the former six-circle diagram is not sufficient.

The primary object is therefore an interactive **Flow-of-Funds / sectoral balance-sheet map** backed by the existing Accounting Spine and Dynamic Core semantics. It preserves the canonical sectors H, C, F, G, BNR and X and adds subsectorisation only when observed data justify it.

## Scientific invariants

This is a cross-cutting product recovery, not Alpha 0.6. Alpha 0.1–0.5.2 results remain unchanged. Accounting Spine and Dynamic Core remain unchanged. Validated behavioural reference mechanisms remain 0. Alpha 0.6 remains NO-GO. Prospective Monetary Confirmation remains frozen under its existing conditions. Government refinancing → effective debt rate remains DEFERRED. Missing bilateral values are never converted to zero or synthetically allocated. Flatpak work remains deferred.

## Main model surface

The model offers two complementary views of the same accounting system:

1. an interactive network map for tracing circuits and propagation paths;
2. a from-whom-to-whom matrix with holder/creditor sectors on rows and issuer/debtor sectors on columns.

Layers are REAL ECONOMY, FISCAL, MONEY & CREDIT, BALANCE SHEETS, EXTERNAL and DYNAMIC FEEDBACKS. The interface distinguishes non-financial flows, fiscal flows, financial transactions, stocks, revaluations/other flows and behavioural candidates/deferred mechanisms.

The map covers wages, household consumption, taxes, social contributions, transfers, government purchases/investment, deposits, loans, interest, reserves, government securities, refinancing, exports/imports, external financing and foreign-currency revaluation. ESA instruments F2/F3/F4 are represented directly where current Accounting Spine relations exist; the product contract retains F2–F8 as the instrument family to expose whenever the underlying model has valid observations or relations.

Selecting a sector answers: what claims/assets are represented; what liabilities/funding are represented; counterparties; instruments; incoming and outgoing relations; net position only where supported; vulnerability channels and limitations.

Selecting a relationship exposes: definition, direction, instrument, accounting class, value only when observed and definitionally matched, period, unit, provenance/source, epistemic role, affected sectors and limitations.

## Macro-Financial Imbalance & Vulnerability Monitor

The dashboard is no longer a software-status dashboard. It focuses on Romanian macro-financial problems and data-supported vulnerability classes.

Currently represented diagnostics include: current-account imbalance; NIIP/external position; public debt and refinancing; sovereign FX exposure; household debt/debt-service burden; NFC leverage/external funding; bank–sovereign exposure; maturity mismatch; and credit growth/credit-to-GDP gap.

A diagnostic can be `NOT ASSESSED` or `UNRESOLVED EXPOSURE` when the required definitionally compatible series is absent. This is intentional. Missing evidence is not transformed into a low-risk classification.

Benchmarks are applied only when unit, period, statistical boundary and institutional definition match. For example, the MIP current-account threshold uses a three-year backward moving average and is therefore not applied directly to an annual Commission forecast or a quarterly Eurostat balance. The MIP NIIP, household-debt, NFC-debt and credit-flow thresholds are not applied until the matched series is present. BIS debt-service and credit-gap definitions remain methodologically separate from national or ad-hoc proxies.

Each diagnostic links back to exact sectors and relations on the central map.

## Accounting / Exposure Stress

The recovery adds mechanical accounting stress tests explicitly labelled **ACCOUNTING / EXPOSURE STRESS**. They are not forecasts and do not reopen Alpha 0.6.

Permitted tests implemented in the reference product include:

- RON depreciation applied mechanically to the documented foreign-currency share of Maastricht government debt;
- one-year maturity exposure translated into principal mechanically subject to rollover;
- mark-to-market change on a selected government-security exposure without fabricating the missing bilateral holding amount;
- a bilateral stock change that preserves equal asset/liability double-entry entries.

No consumption, investment, credit-supply, endogenous FX, fiscal reaction or unvalidated feedback response is simulated.

## Theory / Learn

Theory remains a bilingual EN/RO contextual reader plus complete manual. It covers the circuit of money; institutional sectors; stocks vs flows; Flow of Funds and double entry; bank-money creation; credit, deposits and interest; BNR and central-bank money; monetary transmission; fiscal flows, deficit and debt; government securities; external accounts; saving and investment; assets/liabilities; feedbacks and delays; macro-financial imbalances; provenance; calibration/validation and model limits.

The map and diagnostics open the contextually relevant theory while the full reader, glossary and references remain available without requiring README access.

## Institutional methodological basis

The recovery uses Eurostat / ESA 2010 for sector and financial-account semantics, ECB from-whom-to-whom financial-account guidance, European Commission MIP methodology, IMF Balance Sheet Approach, BIS credit-gap and debt-service methodology, BNR where compatible national evidence is integrated, and Ministry of Finance debt-risk evidence already frozen in Alpha 0.5.2. Boundaries are not mixed for convenience.

## Usefulness Gate

PR #11 is mergeable only if all eight conditions are genuinely satisfied:

1. a user can trace at least one complete financial circuit through the economy;
2. a user can identify who holds liabilities of a sector;
3. a user can see the main imbalances currently supported by evidence;
4. an imbalance can highlight the sectors and relations explaining it;
5. observed, accounting, conceptual, candidate and deferred objects are distinguishable;
6. pure accounting stress tests can be run without being confused with forecasts;
7. necessary theory can be understood without README;
8. a user can state concrete, source-aware findings about Romania's macro-financial system.

The test suite now makes these product conditions executable guards against regression.
