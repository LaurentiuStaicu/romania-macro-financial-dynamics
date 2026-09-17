# Alpha 0.5.2a0 — Government Repricing Ledger final audit

Date: 2026-09-17

## Exit verdict

**PASS as a completed negative identification milestone. Government refinancing → effective debt rate remains `DEFERRED`; Alpha 0.6 remains `NO-GO`.**

The stage improves public instrument-level provenance without weakening the scientific gate. No missing principal or rate is synthesized and no aggregate proxy is promoted into a validated repricing mechanism.

## Frozen foundations

Unchanged and not reopened:

- Alpha 0.1 Foundation;
- Alpha 0.2 Accounting Spine;
- InfoClar Model Suite Design Standard v1.1;
- Alpha 0.3 Dynamic Core;
- Alpha 0.4 Empirical Dynamics historical classifications;
- Alpha 0.5.0 Calibration & Validation results;
- Alpha 0.5.1 Validation Recovery results;
- web-first read-only InfoClar product direction;
- native GTK/Granite/Flatpak deferral until at or near v1.

The Alpha 0.5.1 household delta-policy form remains frozen. Observations from 2026-08 onward remain reserved for the first prospective monetary confirmation after a genuinely new BNR policy-rate movement and are not used to revise that form in this stage.

## Acceptance contract frozen before assessment

`model/calibration_validation/government_repricing_ledger_contract.json` was committed before the ledger was assessed.

The mechanism may not be estimated using redemption share, maturity share, a strategic target, an aggregate refixing share paired with one auction yield, issue size treated as outstanding stock, an assumed one-to-one link between new issuance and a maturing instrument, or a mismatched interest-expenditure/debt-stock ratio.

The preregistered gates require:

- at least 95% opening-principal coverage on the exact MoF cost boundary;
- at least 90% realized repricing-event principal coverage;
- principal reconciliation residual no larger than 0.5% of the matched published stock;
- at least three consecutive published cost snapshots reconstructed with no more than 0.10 percentage point absolute error on each snapshot and no more than 0.05 percentage point mean absolute error;
- matched event-level principal and old/new or reset rates before any repricing parameter is estimated;
- a later prospectively reserved non-zero repricing period before `VALIDATED` status is possible.

Historical reconstruction alone can at most support `CANDIDATE`.

## Public ledger assembled

`data/processed/government_repricing_ledger_0.5.2a0.csv` contains seven auditable public records from Ministry of Finance issuance/reopening terms and BVB-listed Ministry securities.

The instrument subset identifies RON and EUR fixed-rate securities with fields such as ISIN, coupon, maturity and published issue value or announced nominal. Five BVB examples have published issue values. Their issue-value sums are RON 923.2642 million and EUR 151.6391 million, retained only as diagnostic issue-size totals.

These values are not classified as same-date outstanding principal. Secondary-market YTM is not classified as the new effective rate on repriced principal.

## New reconciliation evidence

The MoF Investor Presentation of March 2025 reports, as of 30 December 2024:

- debt maturing within one year: 10%;
- debt refixing within one year: 12%;
- ATM: 6.9 years;
- ATR: 6.7 years;
- local-currency debt maturing within one year: 17%;
- local-currency debt refixing within one year: 15%;
- local ATM and ATR: 4.6 years.

The total maturity and refixing shares differ by two percentage points. Maturity therefore remains observably distinct from refixing even at the newer snapshot.

The existing MoF portfolio-average interest-rate references are preserved unchanged: 3.8% in 2019, 3.3% in 2020, 3.1% in 2021, 3.3% in 2022 and 4.2% in 2023.

Eurostat reports for 2025 an apparent cost of Romanian Maastricht general-government debt of 5.2% and a 53% foreign-currency share. These observations are retained as external diagnostics only because Eurostat's Maastricht/general-government boundary and interest-cost definition are not identical to the MoF portfolio-cost boundary.

## What could be reconciled

The stage reconciles:

- instrument identity and source provenance for a reproducible public subset;
- currency, fixed-rate status, contractual coupon and maturity for that subset;
- published issue value or announced nominal where the source explicitly provides it;
- the semantic difference between maturity, refinancing, contractual refixing and new issuance;
- MoF maturity/refixing risk indicators as distinct measures;
- MoF portfolio-average cost observations as reconciliation targets under their own definition;
- Eurostat Maastricht cost/currency measures as a separate external boundary.

## What could not be identified

The public evidence inspected does not provide a full matched ledger containing:

- same-date opening outstanding principal by instrument/currency/fixed-floating across the MoF cost boundary;
- realized principal actually refinanced in each period linked to the old block it replaces;
- contractual reset dates and realized repriced principal for the material floating/indexed portfolio;
- old effective rate and new/reset effective rate on the same repriced principal;
- same-boundary interest-cost decomposition sufficient to reconstruct the MoF portfolio cost without synthetic allocation.

The ledger therefore contains zero rows with opening outstanding principal, zero rows with realized principal repriced and zero rows with a matched old/new effective-rate pair.

## Gate disposition

- Gate 1 — ledger completeness: **FAIL**.
- Gate 2 — balance reconciliation: **NOT OPENED**.
- Gate 3 — portfolio-cost reconstruction: **NOT OPENED**.
- Gate 4 — parameter identification: **FAIL BEFORE ESTIMATION**.
- Gate 5 — prospective confirmation for `VALIDATED`: **NOT OPENED**.

No estimator is run. This is intentional: estimating `m` from the remaining aggregate observables would require the prohibited synthetic allocation the stage was designed to avoid.

## Final mechanism status

Government refinancing → effective debt rate: **DEFERRED**.

The stage does not reject the economic reality of refinancing or interest-rate transmission through sovereign debt. It rejects a claim that the current public data support the model's aggregate transition equation at the required matched boundary.

Validated behavioural reference mechanisms after Alpha 0.5.2a0: **0**.

Alpha 0.6 Interactive Web Simulator: **NO-GO**.

## Product result

The existing InfoClar web application is updated rather than forked. Model, Theory/Learn, Dashboard and Auxiliary now expose the ledger, maturity-versus-refixing distinction, acceptance thresholds, sources, limitations and final `DEFERRED` status. Behavioural controls remain absent/disabled. The GitHub Pages CTA remains active and the Flatpak CTA remains Planned and unlinked.

## Next justified large stage

The next prospective behavioural path remains **Prospective Monetary Confirmation**, but it is executable only after a genuinely new BNR policy-rate movement creates identifying variation for the already frozen household delta-policy form. Reserved observations must not be used to respecify the form before that first confirmation test.

For government repricing, further work is justified only if a new official/reproducible data source supplies same-date outstanding principal plus matched refinancing/reset events and rates over the material MoF portfolio boundary. Repeating aggregate proxy fitting is not a justified next stage.
