# Alpha 0.3.0a0 — Handoff to Empirical Dynamics

Date: 2026-09-17

## What Alpha 0.3 now guarantees

The project has an executable structural dynamic substrate whose numerical state is constrained by the Accounting Spine and whose presentation binding inherits InfoClar Model Suite Design Standard v1.1.

Guaranteed at this boundary:

- one canonical bilateral financial-position representation;
- double-entry conservation;
- explicit stock/flow/change identities;
- explicit time unit and reference integration step;
- guarded empirical initialization;
- first-order delay primitive;
- dimension registry;
- candidate feedback registry with all candidates inactive;
- macro-financial stock-flow central-diagram contract;
- canonical empirical-dashboard, Theory/Learn and Auxiliary bindings;
- Python presentation payloads for future UI consumption;
- structural verification and integration-error tests.

## What Alpha 0.3 intentionally does not decide

The following remain scientifically open:

- which behavioural equations should close the household sector;
- which investment function should represent non-financial corporations;
- how bank credit demand and supply should be separated and estimated;
- how fiscal reaction and sovereign refinancing should be represented;
- which monetary-transmission channels are endogenous vs exogenous;
- how credit/default/sovereign risk premia respond to state variables;
- whether and how exchange-rate dynamics are endogenized;
- how maturity/refinancing structures and delays are parameterized;
- which relationships are estimated econometrically, calibrated from literature, or retained exogenous.

## Next decision gate

Alpha 0.4 Empirical Dynamics requires a model-closure strategy. This is the first gate after Alpha 0.3 where different choices can produce materially different dynamic behaviour while all software tests remain green.

The recommended default is **modular evidence-first closure**:

1. admit one behavioural block at a time;
2. register its causal hypothesis and alternatives;
3. identify observables and candidate equations;
4. estimate or source parameters with provenance;
5. run dimensional/extreme-condition/sensitivity tests;
6. test historical behaviour before coupling the next block;
7. preserve rejected alternatives and diagnostics.

A simultaneous multi-block closure is possible but increases identification and attribution difficulty. Selecting between these approaches is therefore a genuine scientific-direction decision rather than a routine implementation detail.
