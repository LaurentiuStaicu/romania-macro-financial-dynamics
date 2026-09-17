from __future__ import annotations

import csv
import json
from pathlib import Path

from romania_macro_financial_dynamics.validation_recovery import (
    RecoveryIdentifiabilityError,
    count_nonzero_policy_changes,
    error_metrics,
    expanding_origin_predictions,
    fit_model,
    parameter_summary,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "validation_recovery"
SPLIT = ROOT / "data" / "provenance" / "validation_recovery_split_0.5.1a0.json"
CONTRACT = ROOT / "model" / "calibration_validation" / "validation_recovery_contract.json"
OUTPUT = ROOT / "model" / "calibration_validation" / "validation_recovery_selection.json"


def read_series(path: Path, cutoff: str) -> dict[str, float]:
    values: dict[str, float] = {}
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            period = row["period"]
            if period > cutoff:
                # Do not parse a reserved final-holdout or post-evaluation value.
                continue
            values[period] = float(row["value_pct"])
    return values


def aligned_series(target_path: Path, cutoff: str) -> tuple[list[str], list[float], list[float]]:
    policy = read_series(DATA / "policy_rate_bis_monthly.csv", cutoff)
    target = read_series(target_path, cutoff)
    periods = sorted(set(policy) & set(target))
    if not periods:
        raise RuntimeError(f"No aligned observations for {target_path}")
    return periods, [policy[p] for p in periods], [target[p] for p in periods]


def indices_between(periods: list[str], start: str, end: str) -> list[int]:
    return [i for i, period in enumerate(periods) if start <= period <= end]


def improvement(candidate: float, baseline: float) -> float:
    if baseline <= 0:
        return float("-inf")
    return 1.0 - candidate / baseline


def evaluate_target(target_id: str, target_path: Path, split: dict, contract: dict) -> dict:
    selection_end = split["roles"]["structural_selection"]["end"]
    periods, policy, lending = aligned_series(target_path, selection_end)

    calibration_idx = indices_between(
        periods,
        split["roles"]["calibration"]["start"],
        split["roles"]["calibration"]["end"],
    )
    selection_idx = indices_between(
        periods,
        split["roles"]["structural_selection"]["start"],
        split["roles"]["structural_selection"]["end"],
    )
    if len(calibration_idx) < contract["identifiability_gates"]["minimum_calibration_months"]:
        raise RuntimeError("Calibration window shorter than preregistered minimum")
    if len(selection_idx) < contract["structural_selection_gates"]["minimum_origins"]:
        raise RuntimeError("Selection window shorter than preregistered minimum")

    through_selection_idx = list(range(1, selection_idx[-1] + 1))
    nonzero_policy_changes = count_nonzero_policy_changes(policy, through_selection_idx)
    required_changes = contract["identifiability_gates"]["minimum_nonzero_policy_changes_before_selection_end"]

    calibration_observations = calibration_idx
    calibration_transitions = [i for i in calibration_idx if i >= 1]

    baseline_ids = [item["id"] for item in contract["baseline_models"]]
    candidate_ids = [item["id"] for item in contract["candidate_models"]]

    baseline_results: dict[str, dict] = {}
    for model_id in baseline_ids:
        predicted, fits = expanding_origin_predictions(model_id, lending, policy, selection_idx)
        metrics = error_metrics([lending[i] for i in selection_idx], predicted)
        baseline_results[model_id] = {
            "metrics": metrics,
            "origins": len(selection_idx),
            "parameter_summary": parameter_summary(model_id, fits) if fits else {"n": 0},
        }

    candidates: dict[str, dict] = {}
    best_baseline_mae = min(float(result["metrics"]["mae"]) for result in baseline_results.values())
    for model_id in candidate_ids:
        calibration_fit = None
        calibration_error = None
        try:
            calibration_fit = fit_model(
                model_id,
                lending,
                policy,
                calibration_observations,
                calibration_transitions,
            )
        except RecoveryIdentifiabilityError as exc:
            calibration_error = str(exc)

        try:
            predicted, fits = expanding_origin_predictions(model_id, lending, policy, selection_idx)
            metrics = error_metrics([lending[i] for i in selection_idx], predicted)
            psummary = parameter_summary(model_id, fits)
            rmse_improvements = {
                baseline_id: improvement(
                    float(metrics["rmse"]),
                    float(baseline_results[baseline_id]["metrics"]["rmse"]),
                )
                for baseline_id in baseline_ids
            }
            gates = {
                "minimum_origins": len(selection_idx) >= contract["structural_selection_gates"]["minimum_origins"],
                "enough_policy_changes": nonzero_policy_changes >= required_changes,
                "rmse_vs_each_baseline": all(
                    value >= contract["structural_selection_gates"]["candidate_rmse_improvement_vs_each_baseline_fraction"]
                    for value in rmse_improvements.values()
                ),
                "mae_vs_best_baseline": float(metrics["mae"])
                <= best_baseline_mae
                * (1.0 + contract["structural_selection_gates"]["candidate_mae_may_not_exceed_best_baseline_by_more_than_fraction"]),
                "absolute_bias": abs(float(metrics["bias_actual_minus_predicted"]))
                <= contract["structural_selection_gates"]["candidate_absolute_bias_max_percentage_points"],
                "parameter_domain_consistency": float(psummary.get("domain_fraction", 0.0))
                >= contract["structural_selection_gates"]["parameter_sign_or_domain_consistency_fraction"],
            }
            candidates[model_id] = {
                "calibration_fit": (
                    {
                        "parameters": calibration_fit.parameters,
                        "training_observations": calibration_fit.training_observations,
                        "driver_sum_squares": calibration_fit.driver_sum_squares,
                        "design_rank": calibration_fit.design_rank,
                    }
                    if calibration_fit
                    else None
                ),
                "calibration_identifiability_error": calibration_error,
                "selection_metrics": metrics,
                "selection_parameter_summary": psummary,
                "rmse_improvement_vs_baselines": rmse_improvements,
                "gates": gates,
                "passes_all_selection_gates": all(gates.values()),
            }
        except RecoveryIdentifiabilityError as exc:
            candidates[model_id] = {
                "calibration_fit": None,
                "calibration_identifiability_error": calibration_error,
                "selection_identifiability_error": str(exc),
                "passes_all_selection_gates": False,
            }

    passed = [model_id for model_id, result in candidates.items() if result["passes_all_selection_gates"]]
    return {
        "target_id": target_id,
        "analysis_period": {"start": periods[0], "end": periods[-1]},
        "calibration_months": len(calibration_idx),
        "selection_months": len(selection_idx),
        "nonzero_policy_changes_through_selection_end": nonzero_policy_changes,
        "identifiability_minimum_policy_changes": required_changes,
        "baseline_results": baseline_results,
        "candidate_results": candidates,
        "passed_candidates": passed,
        "selection_verdict": "PASS_TO_FINAL_EVALUATION" if passed else "FAIL_BEFORE_HOLDOUT",
    }


def main() -> None:
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    targets = {
        "household_housing": DATA / "household_housing_mir_monthly.csv",
        "nfc_upto1y": DATA / "nfc_upto1y_mir_monthly.csv",
    }
    results = {
        "result_version": "0.5.1a0-selection",
        "holdout_opened": False,
        "holdout_period": split["roles"]["final_evaluation_holdout"],
        "old_alpha_0_5_holdout_status": "CONTAMINATED_RECLASSIFIED_AS_STRUCTURAL_SELECTION",
        "targets": {
            target_id: evaluate_target(target_id, path, split, contract)
            for target_id, path in targets.items()
        },
    }
    passed = {
        target: result["passed_candidates"]
        for target, result in results["targets"].items()
        if result["passed_candidates"]
    }
    results["candidates_eligible_for_final_evaluation"] = passed
    results["open_final_holdout"] = bool(passed)
    results["selection_stage_verdict"] = (
        "OPEN_FINAL_HOLDOUT_FOR_ELIGIBLE_TARGETS" if passed else "CLOSE_NO_GO_WITHOUT_OPENING_HOLDOUT"
    )
    OUTPUT.write_text(json.dumps(results, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
