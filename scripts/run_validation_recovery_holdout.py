from __future__ import annotations

import csv
import json
from pathlib import Path

from romania_macro_financial_dynamics.validation_recovery import (
    error_metrics,
    fit_constant_spread,
    fit_delta_policy,
    persistence_prediction,
    predict_constant_spread,
    predict_delta_policy,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "validation_recovery"
SPLIT_PATH = ROOT / "data" / "provenance" / "validation_recovery_split_0.5.1a0.json"
CONTRACT_PATH = ROOT / "model" / "calibration_validation" / "validation_recovery_contract.json"
FREEZE_PATH = ROOT / "model" / "calibration_validation" / "validation_recovery_selection_freeze.json"
OUTPUT = ROOT / "model" / "calibration_validation" / "validation_recovery_holdout.json"


def read_series(path: Path, *, allowed_end: str) -> dict[str, float]:
    values: dict[str, float] = {}
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            period = row["period"]
            if period > allowed_end:
                continue
            values[period] = float(row["value_pct"])
    return values


def main() -> None:
    split = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))

    target_freeze = freeze["targets"]["household_housing"]
    if not target_freeze["final_holdout_may_be_opened"]:
        raise RuntimeError("Selection freeze does not authorize opening household holdout")
    if target_freeze["selected_candidate"] != "delta_policy_contemporaneous":
        raise RuntimeError("Holdout evaluator supports only the frozen selected form")
    if freeze["targets"]["nfc_upto1y"]["final_holdout_may_be_opened"]:
        raise RuntimeError("NFC holdout must remain unopened in this recovery cycle")

    holdout = split["roles"]["final_evaluation_holdout"]
    holdout_start = holdout["start"]
    holdout_end = holdout["end"]
    selection_end = split["roles"]["structural_selection"]["end"]

    policy_map = read_series(DATA / "policy_rate_bis_monthly.csv", allowed_end=holdout_end)
    household_map = read_series(DATA / "household_housing_mir_monthly.csv", allowed_end=holdout_end)
    periods = sorted(set(policy_map) & set(household_map))
    policy = [policy_map[p] for p in periods]
    lending = [household_map[p] for p in periods]

    training_indices = [i for i, p in enumerate(periods) if p <= selection_end]
    training_transitions = [i for i in training_indices if i >= 1]
    holdout_indices = [i for i, p in enumerate(periods) if holdout_start <= p <= holdout_end]
    if len(holdout_indices) < contract["final_holdout_gates_if_opened"]["minimum_observations"]:
        raise RuntimeError("Final holdout is shorter than preregistered minimum")

    candidate_fit = fit_delta_policy(
        lending, policy, training_transitions, lag=0
    )
    spread_fit = fit_constant_spread(lending, policy, training_indices)

    actual = [lending[i] for i in holdout_indices]
    candidate = [
        predict_delta_policy(lending, policy, i, candidate_fit, lag=0)
        for i in holdout_indices
    ]
    persistence = [persistence_prediction(lending, i) for i in holdout_indices]
    constant_spread = [predict_constant_spread(policy, i, spread_fit) for i in holdout_indices]

    metrics = {
        "candidate": error_metrics(actual, candidate),
        "persistence": error_metrics(actual, persistence),
        "constant_policy_spread": error_metrics(actual, constant_spread),
    }

    candidate_rmse = float(metrics["candidate"]["rmse"])
    improvements = {
        baseline: 1.0 - candidate_rmse / float(metrics[baseline]["rmse"])
        for baseline in ("persistence", "constant_policy_spread")
    }
    best_baseline_mae = min(
        float(metrics["persistence"]["mae"]),
        float(metrics["constant_policy_spread"]["mae"]),
    )

    beta = candidate_fit.parameters["beta"]
    sensitivity = {}
    for label, factor in (("minus_10pct", 0.9), ("plus_10pct", 1.1)):
        altered_beta = beta * factor
        altered_predictions = [
            lending[i - 1] + altered_beta * (policy[i] - policy[i - 1])
            for i in holdout_indices
        ]
        sensitivity[label] = error_metrics(actual, altered_predictions)
    sensitivity_pass = all(
        float(result["rmse"]) <= 2.0 * candidate_rmse + 1e-12
        for result in sensitivity.values()
    )

    gates = {
        "minimum_observations": len(holdout_indices)
        >= contract["final_holdout_gates_if_opened"]["minimum_observations"],
        "rmse_vs_each_baseline": all(
            value
            >= contract["final_holdout_gates_if_opened"]["rmse_improvement_vs_each_baseline_fraction"]
            for value in improvements.values()
        ),
        "mae_vs_best_baseline": float(metrics["candidate"]["mae"])
        <= best_baseline_mae
        * (1.0 + contract["final_holdout_gates_if_opened"]["mae_may_not_exceed_best_baseline_by_more_than_fraction"]),
        "absolute_bias": abs(float(metrics["candidate"]["bias_actual_minus_predicted"]))
        <= contract["final_holdout_gates_if_opened"]["absolute_bias_max_percentage_points"],
        "sensitivity": sensitivity_pass,
    }

    nonzero_policy_changes_holdout = sum(
        1
        for i in holdout_indices
        if abs(policy[i] - policy[i - 1]) > 1e-12
    )
    passes = all(gates.values())
    result = {
        "result_version": "0.5.1a0-final-evaluation",
        "selection_freeze": str(FREEZE_PATH.relative_to(ROOT)),
        "target": "household_housing",
        "candidate": "delta_policy_contemporaneous",
        "equation": "lend[t] = lend[t-1] + beta * (policy[t]-policy[t-1])",
        "training_period": {"start": periods[training_indices[0]], "end": periods[training_indices[-1]]},
        "holdout_period": {"start": periods[holdout_indices[0]], "end": periods[holdout_indices[-1]], "n": len(holdout_indices)},
        "frozen_beta": beta,
        "driver_sum_squares_training": candidate_fit.driver_sum_squares,
        "holdout_nonzero_policy_changes": nonzero_policy_changes_holdout,
        "metrics": metrics,
        "rmse_improvement_vs_baselines": improvements,
        "sensitivity_plus_minus_10pct": sensitivity,
        "gates": gates,
        "passes_all_final_holdout_gates": passes,
        "final_mechanism_verdict": "VALIDATED" if passes else "CANDIDATE",
        "causal_claim": false,
        "nfc_final_holdout_opened": false,
        "nfc_verdict": "CANDIDATE",
        "alpha_0_6_behavioural_gate": "RECONSIDER" if passes else "NO_GO",
        "interpretation_rule": "If the holdout contains insufficient policy-rate variation, performance cannot by itself identify pass-through; failure to beat persistence remains a valid negative result under the preregistered gate."
    }
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
