# Alpha 0.4.0a0 — Empirical Dynamics final audit

Date: 2026-09-17

## Scope and invariants

Alpha 0.4 adds evidence-traceable behavioural forms on top of the integrated Alpha 0.2 Accounting Spine and Alpha 0.3 Dynamic Core. It does not alter Accounting Spine files, the bilateral stock representation, double-entry conservation, time/unit semantics or InfoClar Model Suite Design Standard v1.1.

`ACTIVATED` in this milestone means **admitted to the Alpha 0.5 calibration/validation set**, not precalibrated. No missing parameter receives a convenience value and no unparameterized behavioural equation is allowed to drive the reference simulation.

## Final mechanism classification

| Mechanism | Status | Functional form / role | Parameter state | Main observables | Main evidence | Key limitation / rejection gate |
|---|---|---|---|---|---|---|
| Monetary policy → lending-rate pass-through | **ACTIVATED** | partial adjustment: `r_t = r_{t-1} + λ(α + β policy_t - r_{t-1})` | `α, β, λ` to estimate in 0.5 | policy rate; household and NFC new-business RON lending rates | IMF 2004; IMF 2017; ECB MIR | degrade/reject if β/λ unstable or non-identifiable, or if no OOS gain over persistence |
| Government refinancing → effective interest rate | **ACTIVATED** | weighted repricing: `(1-m)r_old + m*y_marginal` | refinancing share `m` data-derived/estimated with explicit uncertainty | debt stock; interest expenditure; marginal yield; maturity/refinancing schedule | IMF 2025; EC Debt Sustainability Monitor 2025; ECB Convergence 2026 | degrade/defer if maturity share cannot be bounded without synthetic allocation |
| Household consumption response | **CANDIDATE** | income/rate/debt-service reduced form | all coefficients unestimated | consumption; disposable income; borrowing rate; debt-service ratio | EC 2026 forecast; Eurostat quarterly national accounts | reject if rate/debt-service terms are not identifiable or do not beat income-only OOS baseline |
| Corporate investment response | **CANDIDATE** | demand/rate/EU-fund reduced form | all coefficients unestimated | GFCF; demand/GDP; corporate lending rate; EU-fund impulse | EC 2026 forecast; ECB MIR; Eurostat | reject/degrade if financing-cost effect is unstable or adds no OOS value over demand-only baseline |
| Aggregate bank credit response | **CANDIDATE** | activity/rate/NPL/capital reduced form | all coefficients unestimated | credit; activity; lending rate; NPL; capital/solvency | BNR 2015 bank-lending-channel evidence; IMF 2017 | bank-level evidence cannot be copied to aggregate coefficients; reject if demand/supply trade-offs remain unidentified |
| Sovereign yield/spread response | **CANDIDATE** | debt/deficit/external-risk reduced form | all coefficients unestimated | sovereign spread; debt/GDP; deficit/GDP; external risk | IMF 2025; EC DSM 2025 | endogenous fiscal variables/global risk; reject if simple external-risk/persistence baseline performs as well OOS |
| FX pass-through to inflation | **CANDIDATE** | distributed lag of depreciation | lag weights to re-estimate on current regime | inflation; RON/EUR; external/import-price controls | IMF 2003; IMF 2015; IMF 2017; ECB 2026 | documented regime dependence; pre-2005 coefficients may not be reused |
| Credit-risk / NPL response | **DEFERRED** | output/debt-service/persistence candidate | not estimated | NPL; output; debt-service burden | BNR 2015 | comparable NPL history and borrower-risk observables are insufficiently established at this gate |
| Fiscal primary-balance reaction function | **DEFERRED** | regime-aware fiscal reaction, not a fixed Taylor-style rule | not specified | primary balance; debt; output gap; fiscal package indicators | IMF 2025; EC 2026; ECB 2026 | large discretionary packages/EDP regime shifts; do not hide them behind a false stable rule |
| Monetary-policy reaction function | **DEFERRED** | policy rate response to inflation/activity/FX/expectations | not specified | policy rate; gaps; FX; expectations | IMF 2017; ECB 2026 | policy endogeneity, managed-float intervention and regime changes require explicit identification |
| External FX-refinancing feedback | **DEFERRED** | currency-specific debt-service and maturity mechanism | not specified | currency-specific debt; FX; maturity; interest cost | ECB 2026; IMF 2025 | aggregate debt/financial-account positions are insufficient to infer currency exposure or hedging |
| Direct policy-rate → FX shortcut | **REJECTED** | `ΔFX = β Δpolicy_rate` | none | policy rate; FX | IMF 2017; ECB 2026 | under-specified: confounds global risk, intervention and endogenous policy response |
| Debt-stock-only → default-risk shortcut | **REJECTED** | `risk = β debt_stock` | none | debt stock; risk outcome | BNR 2015 | omits repayment capacity, debt service, collateral/capital and macro conditions |

The machine-readable source, functional-form, observables, limits and rejection criteria are canonical in `model/empirical_dynamics/evidence_registry.json` and `model/empirical_dynamics/mechanism_registry.json`.

## Why only two mechanisms are activated

The activation bar is intentionally higher than plausibility. Romanian evidence directly supports interest-rate transmission, and the refinancing-effective-rate equation is a transparent stock-composition mechanism whose main unknown is the share of debt repriced in each period. By contrast, consumption, investment, aggregate credit, sovereign spreads and FX pass-through all face material identification, aggregation or regime-stability questions that belong in Alpha 0.5 structural selection and validation rather than being promoted by assumption.

The full monetary-credit loop therefore is **not** declared calibrated or causal merely because the first pass-through link is activated. Likewise, the government issuance–yield loop remains a candidate even though refinancing arithmetic is activated.

## Functional-form discipline

All implemented forms are pure Python functions with explicit required parameters. No estimated coefficient, pass-through magnitude, lag weight, maturity share or behavioural elasticity is embedded as a default. Bounds are applied only where they are definitional (for example adjustment/refinancing fractions in `[0,1]`).

Published historical Romanian coefficients are evidence, not current parameters. In particular, older exchange-rate pass-through estimates are not transferred into the current inflation-targeting/managed-float regime.

## Evidence and observability

Primary/current observables are preferentially attached to official sources. ECB MIR provides monthly Romanian RON new-business lending-rate series; Eurostat quarterly national accounts provide GDP/consumption/investment observables. IMF, ECB, European Commission and BNR studies/reports support mechanism existence, regime context and sign hypotheses, but are not treated as substitutes for current-sample calibration.

## Exit-gate result

**PASS.** Every behavioural mechanism in scope is classified `ACTIVATED`, `CANDIDATE`, `REJECTED` or `DEFERRED`; every mechanism has a functional form or explicit reason not to implement one, an evidence trail, observables, parameter/estimation plan, limitations and rejection/degradation criteria. Activated equations contain no fabricated parameter values.

Alpha 0.5 must keep calibration, structural-selection and final evaluation/holdout data separated. An evaluation holdout becomes contaminated once inspected and cannot later be reported as independent validation.
