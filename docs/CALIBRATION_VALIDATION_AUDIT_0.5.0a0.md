# Alpha 0.5.0a0 — Calibration & Validation final audit

Date: 2026-09-17

## Result

Alpha 0.5 is scientifically complete as a **negative/limiting validation result**: neither Alpha 0.4 `ACTIVATED` mechanism qualifies as a validated behavioural reference mechanism on the evidence assembled for this milestone.

This is a valid milestone outcome. The model is not made more complex to manufacture a success.

## Invariants

Unchanged:

- Alpha 0.2 Accounting Spine and explicit `TBD != 0` semantics;
- Alpha 0.3 Dynamic Core stock/flow/delay/double-entry contracts;
- Alpha 0.4 mechanism/evidence history;
- InfoClar Model Suite Design Standard v1.1 scientific-semantics invariant.

New cross-cutting product interpretation: InfoClar is now an implemented **web reference interface**, not merely a design contract. The Alpha 0.5 browser surface is read-only and exposes model structure, Theory/Learn, empirical validation status, official sources and limitations. Flatpak/native development remains deferred until at or near v1.

## Data-role separation

The frozen monetary sample contains 13 monthly observations from January 2024 through January 2025. Before estimation it was split into:

- calibration: January–June 2024, 6 observations;
- structural selection: July–October 2024, 4 observations;
- final evaluation holdout: November 2024–January 2025, 3 observations.

The final holdout was inspected only after the structural-selection judgement was fixed. It is now contaminated for future independent validation and cannot be reused as a new independent holdout after model revision.

## Mechanism 1 — monetary-policy → lending-rate pass-through

### Alpha 0.4 status

`ACTIVATED`: admitted for calibration because Romanian evidence supports an interest-rate transmission mechanism.

### Tested form

`r_t = r_(t-1) + lambda * (alpha + beta * policy_t - r_(t-1))`

Estimated through the linear reparameterisation:

`Delta r_t = c + b * policy_t + d * r_(t-1)`

with `lambda = -d`, `beta = b/lambda`, `alpha = c/lambda`.

No regularisation or prior is introduced to conceal rank deficiency.

### Calibration identifiability

**FAIL.** The calibration-only design has rank `2/3` for both NFC and household rates because the policy rate is constant at 7.00% throughout January–June 2024. Intercept and long-run pass-through cannot be separately identified.

This means there is no scientifically defensible calibration-only estimate of all three parameters.

### Time-respecting structural selection

July 2024 itself is not estimable from the pre-July history because the prior policy-rate driver is constant. The candidate becomes numerically estimable only after a policy-rate change enters the expanding window.

Common candidate/baseline evaluation therefore uses August–October 2024 while separately recording the July identifiability failure.

For NFC new lending rates:

- partial-adjustment candidate RMSE: `0.2217 pp`;
- persistence RMSE: `0.1738 pp`;
- constant policy-spread RMSE: `0.1455 pp`.

For household new lending rates:

- partial-adjustment candidate RMSE: `0.1085 pp`;
- persistence RMSE: `0.0837 pp`;
- constant policy-spread RMSE: `0.0756 pp`.

**FAIL.** The behavioural candidate loses to both simpler baselines for both targets during structural selection.

### Practical-identifiability diagnostics

The expanding-window design remains extremely poorly conditioned even after policy variation appears. The condition proxy remains in the hundreds to above one thousand in early origins.

NFC rolling long-run pass-through estimates fall sharply from approximately `2.10` to `1.57` to `0.54`; after including October in the pre-holdout fit the estimate turns negative (`-0.379`). Household rolling estimates are large and negative throughout structural selection (`-2.77`, `-4.23`, `-2.52`) and remain negative pre-holdout (`-1.85`).

These are signs of practical non-identifiability/model misspecification in this short sample, not credible structural elasticities.

### Historical/in-sample reproduction

Pre-holdout fit through October 2024:

- NFC in-sample RMSE: `0.1541 pp`;
- household in-sample RMSE: `0.1140 pp`.

These values are recorded but are not treated as predictive validation.

### Final holdout

The final holdout contains only three observations.

NFC:

- candidate RMSE: `0.2008 pp`;
- persistence RMSE: `0.2257 pp`;
- constant-spread RMSE: `0.2133 pp`.

Households:

- candidate RMSE: `0.2715 pp`;
- persistence RMSE: `0.2808 pp`;
- constant-spread RMSE: `0.4338 pp`.

The candidate is numerically competitive on this tiny final slice, but **the holdout does not rescue the mechanism**. Selection had already failed, the sample is low-power (`n=3`), and revising the model after seeing these values would contaminate the holdout.

### Sensitivity

One-at-a-time ±10% perturbations show material fragility. For example, household holdout RMSE ranges from roughly `0.296` to `0.469 pp` under a ±10% perturbation of the transformed intercept and from roughly `0.251` to `0.378 pp` under pass-through perturbation. NFC sensitivity is especially large to the transformed intercept (`~0.300–0.313 pp` versus the `0.201 pp` reference RMSE).

### Disposition

`ACTIVATED -> CANDIDATE` / **not validated**.

Published Romanian evidence still supports monetary transmission as a phenomenon. The failure applies to this three-parameter partial-adjustment specification on this frozen short sample, not to the proposition that monetary transmission exists.

Future retest requires a substantially longer monthly history spanning multiple tightening/easing cycles and a newly reserved untouched holdout. A more parsimonious form should be tested before adding controls.

## Mechanism 2 — government refinancing → effective debt rate

### Alpha 0.4 status

`ACTIVATED`: the arithmetic repricing mechanism is structurally transparent and refinancing is materially relevant.

### Official evidence assembled

The Ministry of Finance February 2025 investor presentation reports 2025 financing-plan redemptions of approximately:

- RON 49.8 bn domestic debt redemption;
- RON 20.8 bn foreign debt redemption;
- RON 70.6 bn combined.

The Ministry of Finance public-debt report records December 2024 Maastricht/EU-methodology general-government debt of RON 963.9411 bn.

A diagnostic ratio is therefore:

`70.6 / 963.9411 = 7.3241%`.

The 2024–2026 government debt-management strategy separately targets the share of total debt due within one year and the share changing its interest rate within one year, with reported 10–20% ranges/limits, and average time-to-maturity/time-to-refixing objectives around 7–8 years.

### Identifiability assessment

The `7.3241%` redemption/debt ratio is **DIAGNOSTIC_ONLY**, not the model parameter `m`.

Reasons:

- principal redemption is not identical to interest-rate repricing;
- floating-rate debt can reprice without redemption;
- gross-financing/prefunding/cash-buffer concepts differ from stock boundaries;
- Maastricht debt is not automatically definitionally identical to every financing-plan component;
- the strategy's refixing percentages are targets/risk limits, not realised 2025 empirical shares;
- effective interest expenditure and marginal yields need a matched instrument/currency/maturity boundary.

No synthetic allocation is allowed to bridge these concepts.

### Disposition

`ACTIVATED -> DEFERRED` / **not point identified and not validated**.

Retesting requires matched realised maturity/refixing schedules, effective rates on the opening stock, marginal issuance/refinancing yields and reconciled interest expenditure.

## Mechanisms not calibrated

Alpha 0.4 `CANDIDATE`, `DEFERRED` and `REJECTED` mechanisms were not fitted to the final holdout. Promoting them after observing weaknesses in the activated mechanisms would violate the pre-registered structural-selection discipline.

They remain at their prior evidence classifications until a future scientifically separate selection/calibration cycle with appropriate data is opened.

## Uncertainty statement

The dominant uncertainties are structural and identification-related, not merely numerical confidence intervals:

- insufficient policy-driver variation in the calibration slice;
- tiny structural-selection and holdout samples;
- unstable/ill-conditioned pass-through parameters;
- new-business rates are not effective rates on outstanding loan stocks;
- monetary policy is endogenous;
- government refinancing/repricing concepts are not yet definitionally matched across official datasets;
- unresolved Accounting Spine cells remain unresolved.

Optimizer convergence or low in-sample error would not resolve these uncertainties.

## Alpha 0.6 decision gate

Validated behavioural reference mechanisms: **0**.

Therefore:

- **NO-GO for behavioural Interactive Web Simulator as currently scoped**;
- **GO for continued web-first InfoClar development in read-only structural/empirical/theory mode**;
- no Flatpak/native work begins;
- future scientific work should first enlarge/repair the empirical basis or explicitly revise the scientific scope before behavioural simulation is presented as validated.

## InfoClar product progress in Alpha 0.5

The first real web reference surface is implemented under `web/`:

- macro-financial H/C/F/G/X/BNR system map;
- contextual Theory/Learn linked to sector selection;
- empirical calibration/validation dashboard;
- Auxiliary source/limitation/mechanism-status surface;
- persistent EN/RO switching;
- responsive 2×2 → stacked layout;
- keyboard sector selection, skip link, focus-visible styling and live status regions;
- canonical `web/public/model-stage.json` scientific presentation snapshot tested against registries/results.

This is not Alpha 0.6 simulation. It is the InfoClar reference product progressively absorbing validated scientific content as intended by the web-first roadmap.
