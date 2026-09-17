# Product Architecture Recovery — Usefulness v2

This follow-up exists because PR #11 was already merged before the stricter product contract was supplied. It does not reopen behavioural simulation and does not start Flatpak work.

## Central question

How do finances circulate through Romania's economy, who funds whom, who owes whom, where do vulnerabilities accumulate, and how can direct accounting exposures transmit shocks?

## Product changes

- Primary explorer is explicitly split into STOCK / BALANCE-SHEET VIEW, FLOW VIEW and FROM-WHOM-TO-WHOM MATRIX.
- Sector inspection is framed around who funds the sector, whom it funds, what it owns, what it owes, instrument, amount, period and represented changes.
- Internal sector codes and raw registry identifiers are removed from the normal frontend.
- Candidate feedbacks expose hypothesised sign, evidence, parameter status, validation status and the evidence needed before simulation.
- Vulnerability diagnostics remain definition-aware and trace to the implicated map relationships.
- Accounting / exposure stress tests remain mechanical and are explicitly not macroeconomic forecasts.
- Theory/Learn now has a complete-reader mode and a bilingual supplement covering money, From-Whom-to-Whom, ESA F2–F8, sector balance sheets, current account/NIIP, currency and maturity mismatch, debt service, accounting stress versus behavioural simulation and validation boundaries.
- Desktop and mobile captures are mandatory CI artifacts and must be visually inspected before merge.

## Scientific invariants

- validated behavioural reference mechanisms remain 0;
- behavioural simulation remains disabled;
- Prospective Monetary Confirmation remains unchanged;
- missing bilateral values are not synthesized or zero-filled;
- no Flatpak work is started.

## Merge gate

Do not merge until CI, Pages build and visual QA are green and the rendered desktop/mobile captures allow a user to answer the eight usefulness questions without README support.
