from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from romania_macro_financial_dynamics.corporate_investment_selection import (
    CorporateInvestmentIdentifiabilityError,
    build_lagged_rows,
    error_metrics,
    expanding_origin_predictions,
    fit_ols,
    improvement,
    parameter_domain_fraction,
)

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"model"/"calibration_validation"/"corporate_investment_structural_selection_contract.json"
EXECUTION_GATE=ROOT/"model"/"calibration_validation"/"corporate_investment_selection_execution_gate.json"
DEFAULT_OUTPUT=ROOT/"model"/"calibration_validation"/"corporate_investment_structural_selection_result.json"


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def load_contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def source_csv(contract: dict) -> Path:
    p=contract["prerequisite_measurement_panel"]
    return ROOT/p["path"]/p["csv"]


def verify_prerequisites(contract: dict) -> dict[str,object]:
    source=source_csv(contract)
    if not source.exists():
        raise RuntimeError(f"retained corporate-investment panel missing: {source}")
    observed=sha256(source)
    expected=contract["prerequisite_measurement_panel"]["csv_sha256"]
    if observed != expected:
        raise RuntimeError("retained corporate-investment panel SHA-256 mismatch")
    if contract["estimation_authorization"]["authorized_by_this_contract"]:
        raise RuntimeError("structural-selection contract must not itself authorize execution")
    return {
        "source_path":str(source.relative_to(ROOT)),
        "source_sha256":observed,
        "contract_path":str(CONTRACT.relative_to(ROOT)),
        "execution_gate_present":EXECUTION_GATE.exists(),
    }


def execution_is_authorized(contract: dict) -> bool:
    if not EXECUTION_GATE.exists():
        return False
    gate=json.loads(EXECUTION_GATE.read_text(encoding="utf-8"))
    return bool(
        gate.get("selection_execution_authorized") is True
        and gate.get("selection_execution_consumed") is not True
        and gate.get("contract")==str(CONTRACT.relative_to(ROOT))
        and gate.get("source_csv_sha256")==contract["prerequisite_measurement_panel"]["csv_sha256"]
        and gate.get("authorized_scope")=="STRUCTURAL_SELECTION_2022Q1_TO_2023Q4_ONLY"
        and gate.get("final_evaluation_authorized") is False
    )


def read_selection_records(contract: dict) -> list[dict[str,object]]:
    selection_end=contract["windows"]["structural_selection"].split("..",1)[1]
    records=[]
    with source_csv(contract).open(encoding="utf-8",newline="") as handle:
        for row in csv.DictReader(handle):
            if row["period"] > selection_end:
                continue
            records.append({
                "period":row["period"],
                "nfc_investment_rate":float(row["nfc_investment_rate"]),
                "real_gdp_yoy_growth":float(row["real_gdp_yoy_growth"]),
                "investment_grants_support_intensity":float(row["investment_grants_support_intensity"]),
                "nfc_new_business_lending_rate_up_to_one_year_quarterly_mean":float(
                    row["nfc_new_business_lending_rate_up_to_one_year_quarterly_mean"]
                ),
            })
    return records


def rows_between(rows,window):
    start,end=window.split("..",1)
    return [row for row in rows if start <= str(row["period"]) <= end]


def fit_summary(fit):
    return {
        "model_id":fit.model_id,
        "parameters":fit.parameters,
        "training_observations":fit.training_observations,
        "design_rank":fit.design_rank,
        "standardized_condition_number":fit.standardized_condition_number,
    }


def model_eval(model_id,rows,contract):
    windows=contract["windows"]
    gates=contract["identifiability_gates"]
    periods,actual,predicted,fits=expanding_origin_predictions(
        model_id,
        rows,
        *windows["structural_selection"].split("..",1),
        minimum_training_observations=int(gates["minimum_training_observations_per_origin"]),
        condition_number_max=float(gates["standardized_design_condition_number_max"]),
    )
    return {
        "periods":periods,
        "metrics":error_metrics(actual,predicted),
        "origin_count":len(periods),
    },fits


def domain_fractions(fits,contract,parameters):
    domains=contract["identifiability_gates"]["parameter_domains"]
    return {
        p:parameter_domain_fraction(fits,p,domains[p][0],domains[p][1])
        for p in parameters
    }


def evaluate_selection(contract: dict) -> dict[str,object]:
    records=read_selection_records(contract)
    rows=build_lagged_rows(records)
    windows=contract["windows"]
    idg=contract["identifiability_gates"]
    max_condition=float(idg["standardized_design_condition_number_max"])
    min_train=int(idg["minimum_training_observations_per_origin"])
    calibration=rows_between(rows,windows["initial_calibration"])
    if len(calibration) < min_train:
        raise RuntimeError("initial calibration window violates frozen minimum")

    calibration_fits={
        model:fit_summary(fit_ols(model,calibration,condition_number_max=max_condition))
        for model in (
            "investment_rate_ar",
            "core_lagged_drivers_ar",
            "support_augmented_lagged_drivers_ar",
        )
    }

    model_results={}
    fits_by_model={}
    for model in (
        "persistence",
        "investment_rate_ar",
        "core_lagged_drivers_ar",
        "support_augmented_lagged_drivers_ar",
    ):
        model_results[model],fits_by_model[model]=model_eval(model,rows,contract)

    domain_min=float(idg["parameter_domain_consistency_fraction_min"])
    core_domains=domain_fractions(
        fits_by_model["core_lagged_drivers_ar"],
        contract,["rho","beta_g","beta_r"]
    )
    aug_domains=domain_fractions(
        fits_by_model["support_augmented_lagged_drivers_ar"],
        contract,["rho","beta_g","beta_r","beta_s"]
    )

    persistence=model_results["persistence"]
    ar=model_results["investment_rate_ar"]
    core=model_results["core_lagged_drivers_ar"]
    aug=model_results["support_augmented_lagged_drivers_ar"]
    pg=contract["primary_structural_selection_gates"]
    ag=contract["augmented_extension_gates"]

    core_rmse=float(core["metrics"]["rmse"])
    ar_rmse=float(ar["metrics"]["rmse"])
    persistence_rmse=float(persistence["metrics"]["rmse"])
    best_baseline_mae=min(float(ar["metrics"]["mae"]),float(persistence["metrics"]["mae"]))

    primary_gates={
        "minimum_evaluable_origins":int(core["origin_count"])>=int(pg["minimum_evaluable_origins"]),
        "rmse_vs_persistence":improvement(core_rmse,persistence_rmse)>=float(pg["candidate_rmse_improvement_vs_persistence_fraction_min"]),
        "rmse_vs_investment_rate_ar":improvement(core_rmse,ar_rmse)>=float(pg["candidate_rmse_improvement_vs_investment_rate_ar_fraction_min"]),
        "mae_vs_best_baseline":float(core["metrics"]["mae"]) <= best_baseline_mae*(1.0+float(pg["candidate_mae_may_not_exceed_best_baseline_by_more_than_fraction"])),
        "absolute_bias":abs(float(core["metrics"]["bias_actual_minus_predicted"]))<=float(pg["candidate_absolute_bias_max_percentage_points"]),
        "parameter_domains":all(v>=domain_min for v in core_domains.values()),
    }
    primary_pass=all(primary_gates.values())

    aug_gates={
        "primary_passed":primary_pass,
        "minimum_evaluable_origins":int(aug["origin_count"])>=int(ag["minimum_evaluable_origins"]),
        "rmse_vs_core":improvement(float(aug["metrics"]["rmse"]),core_rmse)>=float(ag["augmented_rmse_improvement_vs_core_fraction_min"]),
        "mae_vs_core":float(aug["metrics"]["mae"])<=float(core["metrics"]["mae"])*(1.0+float(ag["augmented_mae_may_not_exceed_core_by_more_than_fraction"])),
        "absolute_bias":abs(float(aug["metrics"]["bias_actual_minus_predicted"]))<=float(ag["augmented_absolute_bias_max_percentage_points"]),
        "parameter_domains":all(v>=domain_min for v in aug_domains.values()),
    }
    aug_pass=all(aug_gates.values())

    if not primary_pass:
        verdict="FAIL_BEFORE_HOLDOUT"
        selected=None
    elif aug_pass:
        verdict="PASS_AUGMENTED_TO_FINAL_EVALUATION"
        selected="support_augmented_lagged_drivers_ar"
    else:
        verdict="PASS_CORE_TO_FINAL_EVALUATION"
        selected="core_lagged_drivers_ar"

    return {
        "result_version":"0.1-selection",
        "mechanism_id":contract["mechanism_id"],
        "source_csv_sha256":contract["prerequisite_measurement_panel"]["csv_sha256"],
        "selection_window":windows["structural_selection"],
        "final_evaluation_window":windows["final_evaluation"],
        "final_evaluation_opened":False,
        "calibration_fits":calibration_fits,
        "selection_models":model_results,
        "core_parameter_domain_fractions":core_domains,
        "augmented_parameter_domain_fractions":aug_domains,
        "core_rmse_improvement_vs_baselines":{
            "persistence":improvement(core_rmse,persistence_rmse),
            "investment_rate_ar":improvement(core_rmse,ar_rmse),
        },
        "augmented_rmse_improvement_vs_core":improvement(float(aug["metrics"]["rmse"]),core_rmse),
        "primary_gates":primary_gates,
        "augmented_gates":aug_gates,
        "primary_passes_all_gates":primary_pass,
        "augmented_passes_all_gates":aug_pass,
        "selected_form_for_final_evaluation":selected,
        "selection_verdict":verdict,
        "causal_claim_allowed":False,
        "system_dynamics_activation":False,
        "behavioural_closure_change":False,
    }


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--execute-selection",action="store_true")
    parser.add_argument("--output",type=Path,default=DEFAULT_OUTPUT)
    args=parser.parse_args()
    contract=load_contract()
    prerequisites=verify_prerequisites(contract)
    if not args.execute_selection:
        print(json.dumps({
            "status":"RUNNER_READY_EXECUTION_NOT_REQUESTED",
            "prerequisites":prerequisites,
            "estimation_performed":False,
            "final_evaluation_opened":False,
        },indent=2))
        return
    if not execution_is_authorized(contract):
        raise SystemExit("Corporate-investment structural-selection execution is not authorized. No estimation performed.")
    if args.output.exists():
        raise SystemExit("Structural-selection result already exists; frozen execution is single-write.")
    try:
        result=evaluate_selection(contract)
    except CorporateInvestmentIdentifiabilityError as exc:
        result={
            "result_version":"0.1-selection",
            "mechanism_id":contract["mechanism_id"],
            "selection_window":contract["windows"]["structural_selection"],
            "final_evaluation_window":contract["windows"]["final_evaluation"],
            "selection_verdict":"FAIL_BEFORE_HOLDOUT",
            "identifiability_error":str(exc),
            "selected_form_for_final_evaluation":None,
            "final_evaluation_opened":False,
            "causal_claim_allowed":False,
            "system_dynamics_activation":False,
            "behavioural_closure_change":False,
        }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False))


if __name__=="__main__":
    main()
