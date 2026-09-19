from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from romania_macro_financial_dynamics.sovereign_yield_selection import (
    SovereignYieldIdentifiabilityError,
    build_lagged_rows,
    error_metrics,
    expanding_origin_predictions,
    fit_ols,
    improvement,
    parameter_domain_fraction,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "sovereign_yield_structural_selection_contract.json"
)
EXECUTION_GATE = (
    ROOT
    / "model"
    / "calibration_validation"
    / "sovereign_yield_selection_execution_gate.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "sovereign_yield_structural_selection_result.json"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def source_csv(contract: dict) -> Path:
    return (
        ROOT
        / contract["prerequisite_source_vintage"]["path"]
        / "sovereign_yield_quarterly_source.csv"
    )


def verify_prerequisites(contract: dict) -> dict[str, object]:
    source = source_csv(contract)
    if not source.exists():
        raise RuntimeError(f"retained source vintage missing: {source}")
    observed_hash = sha256(source)
    expected_hash = contract["prerequisite_source_vintage"][
        "normalized_csv_sha256"
    ]
    if observed_hash != expected_hash:
        raise RuntimeError("retained sovereign-yield CSV SHA-256 mismatch")
    if contract["estimation_authorization"]["authorized_by_this_contract"]:
        raise RuntimeError(
            "structural-selection contract must not itself authorize execution"
        )
    return {
        "source_path": str(source.relative_to(ROOT)),
        "source_sha256": observed_hash,
        "contract_path": str(CONTRACT.relative_to(ROOT)),
        "execution_gate_present": EXECUTION_GATE.exists(),
    }


def execution_is_authorized(contract: dict) -> bool:
    if not EXECUTION_GATE.exists():
        return False
    gate = json.loads(EXECUTION_GATE.read_text(encoding="utf-8"))
    return bool(
        gate.get("selection_execution_authorized") is True
        and gate.get("contract") == str(CONTRACT.relative_to(ROOT))
        and gate.get("source_csv_sha256")
        == contract["prerequisite_source_vintage"]["normalized_csv_sha256"]
        and gate.get("final_evaluation_authorized") is False
    )


def read_selection_records(contract: dict) -> list[dict[str, object]]:
    selection_end = contract["windows"]["structural_selection"].split("..", 1)[1]
    records: list[dict[str, object]] = []
    with source_csv(contract).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            period = row["period"]
            if period > selection_end:
                continue
            if row["source_completeness"] != "COMPLETE":
                raise RuntimeError(f"incomplete retained source row: {period}")
            records.append(
                {
                    "period": period,
                    "romania_10y_yield_pct": float(row["romania_10y_yield_pct"]),
                    "germany_10y_yield_pct": float(row["germany_10y_yield_pct"]),
                    "euro_area_new_ciss": float(row["euro_area_new_ciss"]),
                    "government_debt_pct_gdp": float(row["government_debt_pct_gdp"]),
                    "government_net_lending_borrowing_pct_gdp": float(
                        row["government_net_lending_borrowing_pct_gdp"]
                    ),
                }
            )
    return records


def rows_between(
    rows: list[dict[str, float | str]],
    window: str,
) -> list[dict[str, float | str]]:
    start, end = window.split("..", 1)
    return [row for row in rows if start <= str(row["period"]) <= end]


def fit_summary(fit) -> dict[str, object]:
    return {
        "model_id": fit.model_id,
        "parameters": fit.parameters,
        "training_observations": fit.training_observations,
        "design_rank": fit.design_rank,
        "standardized_condition_number": fit.standardized_condition_number,
    }


def evaluate_selection(contract: dict) -> dict[str, object]:
    records = read_selection_records(contract)
    rows = build_lagged_rows(records)
    windows = contract["windows"]
    id_gates = contract["identifiability_gates"]
    selection_gates = contract["structural_selection_gates"]
    condition_max = float(id_gates["standardized_design_condition_number_max"])
    min_train = int(id_gates["minimum_training_observations_per_origin"])

    calibration = rows_between(rows, windows["initial_calibration"])
    if len(calibration) < min_train:
        raise RuntimeError("initial calibration window violates frozen minimum")

    calibration_fits = {
        model_id: fit_summary(
            fit_ols(
                model_id,
                calibration,
                condition_number_max=condition_max,
            )
        )
        for model_id in (
            "common_market_ar",
            "fiscal_augmented_common_market_ar",
        )
    }

    model_results: dict[str, dict[str, object]] = {}
    fits_by_model = {}
    for model_id in (
        "persistence",
        "common_market_ar",
        "fiscal_augmented_common_market_ar",
    ):
        periods, actual, predicted, fits = expanding_origin_predictions(
            model_id,
            rows,
            *windows["structural_selection"].split("..", 1),
            minimum_training_observations=min_train,
            condition_number_max=condition_max,
        )
        metrics = error_metrics(actual, predicted)
        model_results[model_id] = {
            "periods": periods,
            "metrics": metrics,
            "origin_count": len(periods),
        }
        fits_by_model[model_id] = fits

    candidate_id = "fiscal_augmented_common_market_ar"
    candidate = model_results[candidate_id]
    persistence = model_results["persistence"]
    common = model_results["common_market_ar"]
    candidate_fits = fits_by_model[candidate_id]

    domains: dict[str, float] = {}
    for parameter, bounds in {
        **id_gates["nuisance_parameter_domains"],
        **id_gates["fiscal_parameter_domains"],
    }.items():
        domains[parameter] = parameter_domain_fraction(
            candidate_fits,
            parameter,
            bounds[0],
            bounds[1],
        )

    fiscal_sign_min = float(id_gates["fiscal_sign_consistency_fraction_min"])
    domain_min = float(id_gates["parameter_domain_consistency_fraction_min"])
    candidate_rmse = float(candidate["metrics"]["rmse"])
    persistence_rmse = float(persistence["metrics"]["rmse"])
    common_rmse = float(common["metrics"]["rmse"])
    best_baseline_mae = min(
        float(persistence["metrics"]["mae"]),
        float(common["metrics"]["mae"]),
    )

    gates = {
        "minimum_evaluable_origins": int(candidate["origin_count"])
        >= int(selection_gates["minimum_evaluable_origins"]),
        "rmse_vs_persistence": improvement(candidate_rmse, persistence_rmse)
        >= float(
            selection_gates[
                "candidate_rmse_improvement_vs_persistence_fraction_min"
            ]
        ),
        "rmse_vs_common_market_ar": improvement(candidate_rmse, common_rmse)
        >= float(
            selection_gates[
                "candidate_rmse_improvement_vs_common_market_ar_fraction_min"
            ]
        ),
        "mae_vs_best_baseline": float(candidate["metrics"]["mae"])
        <= best_baseline_mae
        * (
            1.0
            + float(
                selection_gates[
                    "candidate_mae_may_not_exceed_best_baseline_by_more_than_fraction"
                ]
            )
        ),
        "absolute_bias": abs(
            float(candidate["metrics"]["bias_actual_minus_predicted"])
        )
        <= float(selection_gates["candidate_absolute_bias_max_percentage_points"]),
        "fiscal_beta_d_sign_consistency": domains["beta_d"] >= fiscal_sign_min,
        "fiscal_beta_b_sign_consistency": domains["beta_b"] >= fiscal_sign_min,
        "all_parameter_domains": all(value >= domain_min for value in domains.values()),
    }

    return {
        "result_version": "0.1-selection",
        "mechanism_id": contract["mechanism_id"],
        "source_csv_sha256": contract["prerequisite_source_vintage"][
            "normalized_csv_sha256"
        ],
        "selection_window": windows["structural_selection"],
        "final_evaluation_window": windows["final_evaluation"],
        "final_evaluation_opened": False,
        "calibration_fits": calibration_fits,
        "selection_models": model_results,
        "candidate_parameter_domain_fractions": domains,
        "candidate_rmse_improvement_vs_baselines": {
            "persistence": improvement(candidate_rmse, persistence_rmse),
            "common_market_ar": improvement(candidate_rmse, common_rmse),
        },
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
    parser.add_argument(
        "--execute-selection",
        action="store_true",
        help="Run only the frozen structural-selection window if separately authorized.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    args = parser.parse_args()

    contract = load_contract()
    prerequisites = verify_prerequisites(contract)
    if not args.execute_selection:
        print(
            json.dumps(
                {
                    "status": "RUNNER_READY_EXECUTION_NOT_REQUESTED",
                    "prerequisites": prerequisites,
                    "estimation_performed": False,
                    "final_evaluation_opened": False,
                },
                indent=2,
            )
        )
        return

    if not execution_is_authorized(contract):
        raise SystemExit(
            "Structural-selection execution is not authorized by the frozen "
            "execution gate. No estimation performed."
        )

    try:
        result = evaluate_selection(contract)
    except SovereignYieldIdentifiabilityError as exc:
        result = {
            "result_version": "0.1-selection",
            "selection_verdict": "FAIL_BEFORE_HOLDOUT",
            "identifiability_error": str(exc),
            "final_evaluation_opened": False,
            "causal_claim_allowed": False,
            "system_dynamics_activation": False,
            "behavioural_closure_change": False,
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
