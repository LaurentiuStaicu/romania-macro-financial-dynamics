from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from romania_macro_financial_dynamics.fx_inflation_design import (
    build_design_rows,
    read_level_records,
    rows_in_window,
)
from romania_macro_financial_dynamics.fx_inflation_selection import (
    FxInflationIdentifiabilityError,
    cumulative_fx_effects,
    error_metrics,
    expanding_origin_predictions,
    fit_ols,
    improvement,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "fx_inflation_structural_selection_contract.json"
)
TRANSFORM_CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "fx_inflation_transform_lag_window_contract.json"
)
EXECUTION_GATE = (
    ROOT
    / "model"
    / "calibration_validation"
    / "fx_inflation_selection_execution_gate.json"
)
RESULT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "fx_inflation_structural_selection_result.json"
)
SOURCE = (
    ROOT
    / "data"
    / "source_vintages"
    / "fx-inflation-monthly-levels-vintage-2026-09-19"
    / "fx_inflation_monthly_raw_source.csv"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_contracts() -> tuple[dict, dict]:
    return (
        json.loads(CONTRACT.read_text(encoding="utf-8")),
        json.loads(TRANSFORM_CONTRACT.read_text(encoding="utf-8")),
    )


def verify_source(transform_contract: dict) -> str:
    observed = sha256(SOURCE)
    expected = transform_contract["prerequisite_source_vintage"][
        "normalized_csv_sha256"
    ]
    if observed != expected:
        raise RuntimeError("FX-inflation retained source SHA-256 mismatch")
    return observed


def execution_is_authorized(source_hash: str) -> bool:
    if not EXECUTION_GATE.exists():
        return False
    gate = json.loads(EXECUTION_GATE.read_text(encoding="utf-8"))
    return bool(
        gate.get("selection_execution_authorized") is True
        and gate.get("selection_execution_consumed") is not True
        and gate.get("contract") == str(CONTRACT.relative_to(ROOT))
        and gate.get("source_csv_sha256") == source_hash
        and gate.get("authorized_scope")
        == "STRUCTURAL_SELECTION_2015_01_TO_2020_12_ONLY"
        and gate.get("final_evaluation_authorized") is False
    )


def load_selection_rows(
    transform_contract: dict,
) -> list[dict[str, float | str]]:
    selection_end = transform_contract["windows"][
        "structural_selection"
    ].split("..")[1]
    records = read_level_records(SOURCE, max_period=selection_end)
    return build_design_rows(
        records,
        first_target=transform_contract["windows"][
            "first_eligible_target"
        ],
        last_target=selection_end,
    )


def fit_summary(fit) -> dict[str, object]:
    return {
        "model_id": fit.model_id,
        "training_observations": fit.training_observations,
        "design_rank": fit.design_rank,
        "standardized_condition_number": (
            fit.standardized_condition_number
        ),
        "parameters": fit.parameters,
    }


def evaluate_selection(
    contract: dict,
    transform_contract: dict,
    source_hash: str,
) -> dict[str, object]:
    rows = load_selection_rows(transform_contract)
    windows = contract["windows"]
    id_gates = contract["identifiability_gates"]
    select_gates = contract["structural_selection_gates"]
    sign_gates = contract["sign_consistency_gates"]
    condition_max = float(
        id_gates["standardized_design_condition_number_max"]
    )
    min_train = int(windows["minimum_training_observations_per_origin"])

    calibration_start, calibration_end = windows[
        "initial_calibration"
    ].split("..")
    calibration = rows_in_window(
        rows, calibration_start, calibration_end
    )
    calibration_fits = {
        model_id: fit_summary(
            fit_ols(
                model_id,
                calibration,
                condition_number_max=condition_max,
            )
        )
        for model_id in (
            "ar2_seasonal",
            "external_price_baseline",
            "fx_candidate",
        )
    }

    selection_start, selection_end = windows[
        "structural_selection"
    ].split("..")
    model_results: dict[str, dict[str, object]] = {}
    fits_by_model = {}
    predictions_by_model = {}
    actual_reference = None
    periods_reference = None

    for model_id in (
        "persistence",
        "ar2_seasonal",
        "external_price_baseline",
        "fx_candidate",
    ):
        periods, actual, predicted, fits = expanding_origin_predictions(
            model_id,
            rows,
            selection_start=selection_start,
            selection_end=selection_end,
            minimum_training_observations=min_train,
            condition_number_max=condition_max,
        )
        if actual_reference is None:
            actual_reference = actual
            periods_reference = periods
        elif periods != periods_reference or actual != actual_reference:
            raise RuntimeError("model selection origins are not aligned")
        model_results[model_id] = {
            "periods": periods,
            "metrics": error_metrics(actual, predicted),
            "origin_count": len(periods),
        }
        fits_by_model[model_id] = fits
        predictions_by_model[model_id] = predicted

    candidate = model_results["fx_candidate"]
    ext = model_results["external_price_baseline"]
    ar = model_results["ar2_seasonal"]
    persistence = model_results["persistence"]

    fx_fits = fits_by_model["fx_candidate"]
    short_effects = []
    full_effects = []
    conditions = []
    for fit in fx_fits:
        short, full = cumulative_fx_effects(fit)
        short_effects.append(short)
        full_effects.append(full)
        conditions.append(fit.standardized_condition_number)

    short_fraction = sum(v >= 0 for v in short_effects) / len(short_effects)
    full_fraction = sum(v >= 0 for v in full_effects) / len(full_effects)

    candidate_rmse = float(candidate["metrics"]["rmse"])
    ext_rmse = float(ext["metrics"]["rmse"])
    ar_rmse = float(ar["metrics"]["rmse"])
    persistence_rmse = float(persistence["metrics"]["rmse"])

    gates = {
        "minimum_evaluable_origins": int(candidate["origin_count"])
        >= int(select_gates["minimum_evaluable_origins"]),
        "rmse_vs_external_price_baseline": improvement(
            candidate_rmse, ext_rmse
        )
        >= float(
            select_gates[
                "candidate_rmse_improvement_vs_external_price_baseline_fraction_min"
            ]
        ),
        "rmse_vs_ar2_seasonal": improvement(
            candidate_rmse, ar_rmse
        )
        >= float(
            select_gates[
                "candidate_rmse_improvement_vs_ar2_seasonal_fraction_min"
            ]
        ),
        "rmse_vs_persistence": improvement(
            candidate_rmse, persistence_rmse
        )
        >= float(
            select_gates[
                "candidate_rmse_improvement_vs_persistence_fraction_min"
            ]
        ),
        "mae_vs_external_price_baseline": float(
            candidate["metrics"]["mae"]
        )
        <= float(ext["metrics"]["mae"])
        * (
            1.0
            + float(
                select_gates[
                    "candidate_mae_may_not_exceed_external_price_baseline_by_more_than_fraction"
                ]
            )
        ),
        "absolute_bias": abs(
            float(candidate["metrics"]["bias_actual_minus_predicted"])
        )
        <= float(
            select_gates[
                "candidate_absolute_bias_max_monthly_percentage_points"
            ]
        ),
        "cumulative_0_3_sign_consistency": short_fraction
        >= float(
            sign_gates[
                "cumulative_0_3_nonnegative_fraction_min"
            ]
        ),
        "cumulative_0_12_sign_consistency": full_fraction
        >= float(
            sign_gates[
                "cumulative_0_12_nonnegative_fraction_min"
            ]
        ),
        "condition_number_path": max(conditions) <= condition_max,
    }

    return {
        "result_version": "0.1-selection",
        "mechanism_id": contract["mechanism_id"],
        "source_csv_sha256": source_hash,
        "selection_window": windows["structural_selection"],
        "final_evaluation_window": windows["final_evaluation"],
        "final_evaluation_opened": False,
        "calibration_fits": calibration_fits,
        "selection_models": model_results,
        "candidate_rmse_improvement_vs_baselines": {
            "external_price_baseline": improvement(
                candidate_rmse, ext_rmse
            ),
            "ar2_seasonal": improvement(
                candidate_rmse, ar_rmse
            ),
            "persistence": improvement(
                candidate_rmse, persistence_rmse
            ),
        },
        "candidate_fx_cumulative_sign_fractions": {
            "cumulative_0_3_nonnegative_fraction": short_fraction,
            "cumulative_0_12_nonnegative_fraction": full_fraction,
        },
        "candidate_fx_cumulative_effect_path": {
            "periods": periods_reference,
            "cumulative_0_3": short_effects,
            "cumulative_0_12": full_effects,
        },
        "candidate_condition_number_path": conditions,
        "gates": gates,
        "passes_all_selection_gates": all(gates.values()),
        "selection_verdict": (
            "PASS_TO_FINAL_EVALUATION"
            if all(gates.values())
            else "FAIL_BEFORE_HOLDOUT"
        ),
        "causal_claim_allowed": False,
        "system_dynamics_activation": False,
        "behavioural_closure_change": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-selection", action="store_true")
    args = parser.parse_args()

    contract, transform_contract = load_contracts()
    source_hash = verify_source(transform_contract)

    if not args.execute_selection:
        print(
            json.dumps(
                {
                    "status": "RUNNER_READY_EXECUTION_NOT_REQUESTED",
                    "source_sha256": source_hash,
                    "selection_window": contract["windows"][
                        "structural_selection"
                    ],
                    "final_evaluation_window": contract["windows"][
                        "final_evaluation"
                    ],
                    "estimation_performed": False,
                    "final_evaluation_opened": False,
                },
                indent=2,
            )
        )
        return

    if not execution_is_authorized(source_hash):
        raise SystemExit(
            "FX-inflation structural-selection execution is not authorized. "
            "No estimation performed."
        )
    if RESULT.exists():
        raise SystemExit(
            "FX-inflation structural-selection result already exists; "
            "single-write execution may not overwrite it."
        )

    try:
        result = evaluate_selection(
            contract, transform_contract, source_hash
        )
    except FxInflationIdentifiabilityError as exc:
        result = {
            "result_version": "0.1-selection",
            "mechanism_id": contract["mechanism_id"],
            "source_csv_sha256": source_hash,
            "selection_window": contract["windows"][
                "structural_selection"
            ],
            "final_evaluation_window": contract["windows"][
                "final_evaluation"
            ],
            "selection_verdict": "FAIL_BEFORE_HOLDOUT",
            "identifiability_error": str(exc),
            "final_evaluation_opened": False,
            "causal_claim_allowed": False,
            "system_dynamics_activation": False,
            "behavioural_closure_change": False,
        }

    RESULT.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
