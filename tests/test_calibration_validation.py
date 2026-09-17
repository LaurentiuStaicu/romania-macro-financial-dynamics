import csv
import json
from pathlib import Path

import pytest

from romania_macro_financial_dynamics.calibration import (
    PracticalIdentifiabilityError,
    constant_spread_predictions,
    error_metrics,
    fit_constant_policy_spread,
    fit_partial_adjustment,
    matrix_rank,
    one_step_predictions,
    persistence_predictions,
    rolling_origin_diagnostics,
)

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def load_sample():
    with (ROOT / "data/processed/monetary_pass_through_bnr_2024_2025.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    policy = [float(row["policy_rate_pct"]) for row in rows]
    nfc = [float(row["nfc_new_lending_rate_pct"]) for row in rows]
    households = [float(row["household_new_lending_rate_pct"]) for row in rows]
    return rows, policy, nfc, households


def test_frozen_roles_are_disjoint_and_chronological():
    rows, *_ = load_sample()
    roles = [row["data_role"] for row in rows]
    assert roles == ["calibration"] * 6 + ["structural_selection"] * 4 + ["evaluation_holdout"] * 3
    provenance = load_json("data/provenance/monetary_pass_through_bnr_2024_2025.json")
    assert provenance["holdout_policy"]["may_be_reused_as_independent_holdout_after_inspection"] is False


def test_calibration_slice_is_rank_deficient_and_fails_loudly():
    _, policy, nfc, households = load_sample()
    calibration_targets = list(range(1, 6))
    for series in (nfc, households):
        design = [[1.0, policy[i], series[i - 1]] for i in calibration_targets]
        assert matrix_rank(design) == 2
        with pytest.raises(PracticalIdentifiabilityError):
            fit_partial_adjustment(series, policy, calibration_targets)


def test_structural_selection_candidate_loses_to_simple_baselines():
    _, policy, nfc, households = load_sample()
    expected = load_json("model/calibration_validation/monetary_pass_through_results.json")["structural_selection"]
    common_targets = [7, 8, 9]  # Aug-Oct; July cannot be estimated from prior constant-policy data.

    for name, series in (("nfc", nfc), ("households", households)):
        diagnostics = rolling_origin_diagnostics(series, policy, [6, 7, 8, 9])
        assert diagnostics[0]["status"] == "NOT_IDENTIFIABLE"
        model_predictions = [item["prediction"] for item in diagnostics[1:]]
        actual = [series[i] for i in common_targets]
        candidate = error_metrics(actual, model_predictions)
        persistence = error_metrics(actual, persistence_predictions(series, common_targets))
        spread = fit_constant_policy_spread(series, policy, list(range(0, 6)))
        constant_spread = error_metrics(actual, constant_spread_predictions(policy, common_targets, spread))

        assert candidate["rmse"] == pytest.approx(expected[name]["candidate_partial_adjustment"]["rmse_pp"], rel=1e-8)
        assert persistence["rmse"] == pytest.approx(expected[name]["persistence_baseline"]["rmse_pp"], rel=1e-8)
        assert constant_spread["rmse"] == pytest.approx(expected[name]["constant_policy_spread_baseline"]["rmse_pp"], rel=1e-8)
        assert candidate["rmse"] > persistence["rmse"]
        assert candidate["rmse"] > constant_spread["rmse"]


def test_final_holdout_is_not_used_to_reverse_failed_selection():
    _, policy, nfc, households = load_sample()
    result = load_json("model/calibration_validation/monetary_pass_through_results.json")
    holdout = [10, 11, 12]
    for name, series in (("nfc", nfc), ("households", households)):
        fit = fit_partial_adjustment(series, policy, list(range(1, 10)))
        metrics = error_metrics([series[i] for i in holdout], one_step_predictions(fit, series, policy, holdout))
        assert metrics["rmse"] == pytest.approx(
            result["evaluation_holdout_first_and_only_independent_inspection"][name]["candidate_partial_adjustment"]["rmse_pp"],
            rel=1e-8,
        )
    assert result["evaluation_holdout_first_and_only_independent_inspection"]["holdout_contaminated_after_this_audit"] is True
    assert result["final_disposition"]["status"] == "DEGRADE_ACTIVATED_TO_CANDIDATE"


def test_refinancing_proxy_is_diagnostic_not_calibrated_parameter():
    result = load_json("model/calibration_validation/government_refinancing_assessment.json")
    assert result["diagnostic_calculations"]["2025_redemption_to_dec_2024_maastricht_debt_proxy"] == pytest.approx(70.6 / 963.9411)
    assert result["diagnostic_calculations"]["scientific_status"] == "DIAGNOSTIC_ONLY"
    assert result["identifiability"]["synthetic_allocation_allowed"] is False
    assert result["final_disposition"]["status"] == "DEFER"


def test_no_validated_behavioural_reference_mechanism_exists_yet():
    disposition = load_json("model/calibration_validation/mechanism_disposition.json")
    assert disposition["validated_reference_behavioural_mechanisms"] == 0
    assert disposition["alpha_0_6_behavioural_simulator_gate"] == "NO_GO"
    assert disposition["web_product_continuation"] == "GO_READ_ONLY_INFOCLAR"
