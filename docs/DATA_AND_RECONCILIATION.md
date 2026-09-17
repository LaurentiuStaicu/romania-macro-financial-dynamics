# Data and Reconciliation Contract

## Benchmark

- stocks: 31.12.2025;
- annual flows: 01.01.2025–31.12.2025;
- later dynamic series: preferably quarterly where definitions are comparable.

## Minimum numeric-record fields

Every published numeric input used by the model should eventually record:

`id`, `value`, `unit`, `frequency`, `period`, `reference_sector`, `counterpart_sector`, `instrument`, `accounting_entry`, `consolidation`, `valuation`, `source_institution`, `dataset`, `series_key`, `retrieved_at`, `transformation`, `status`, `notes_ro`, `notes_en`.

## Non-negotiable distinctions

Do not silently equate:

- stock and flow;
- quarterly transaction and annual transaction;
- gross new lending and change in loan stock;
- bank credit and total ESA F4;
- money aggregates and sectoral ESA F2;
- Maastricht debt composition and ESA/QSA instrument stocks;
- F8 and pure trade credit;
- deficit, gross issuance and change in debt;
- B9 and B9F;
- primary issuance and secondary-market turnover.

## Reconciliation workflow

For every bilateral financial instrument:

1. match reference date/period;
2. match instrument definition and maturity;
3. match valuation;
4. match consolidation status;
5. match reference and counterpart sector scope;
6. reconcile issuer liabilities against holder assets where counterpart data permit;
7. record the residual rather than forcing closure;
8. explain known methodological causes of residuals.

## Missing data

Use `TBD` in documentation/registries when a value is not established. Approximations must be explicitly labelled and may not masquerade as exact ESA values.
