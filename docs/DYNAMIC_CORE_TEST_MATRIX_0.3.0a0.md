# Alpha 0.3.0a0 — Verification matrix

| Gate | Implementation | Test / evidence |
|---|---|---|
| Accounting hard constraint | `empirical_cells_to_state` | unresolved, duplicate, mixed/invalid matrices rejected |
| Stock identity | `advance_position`, `advance_position_rates` | period and rate-based identity tests |
| Double-entry conservation | single bilateral `PositionKey` representation | sector balance sheets + system net financial worth test |
| Time semantics | canonical year, default `dt=0.25` | rate×time conversion test |
| Dimensional consistency | `unit_registry.json` | signature and equation consistency tests |
| Extreme condition: zero flow | no stock change | zero-flow test |
| Extreme condition: large finite values | finite identity-preserving update | large-value test |
| Delay primitive | first-order delay derivative/integration | steady-state and invalid-parameter tests |
| Integration error | explicit Euler reference | halved time step reduces error on analytic first-order delay case |
| Behavioural isolation | feedback registry inactive | all loops `BEHAVIOURAL_CANDIDATE`, `quantitatively_active=false` |
| Macro-financial central diagram | `presentation_contract.json` | model-specific node/edge-layer tests |
| Empirical dashboard priority | benchmark → reconciliation → dynamics | presentation contract test |
| Contextual Theory/Learn | selection-specific topic mapping | presentation helper/contract test |
| Auxiliary panel separation | details/sources/verification/limitations | presentation helper test |
| InfoClar inheritance | v1.1 referenced, not redefined | branch diff + presentation contract invariants |
| User draft exclusion | no repository artifact | presentation/audit contract records `draft_user_schema_in_repository=false` |

All rows are required for the Alpha 0.3 exit gate. CI is the authoritative execution gate.
