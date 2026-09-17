import inspect
import json
from pathlib import Path

import pytest

from romania_macro_financial_dynamics.behavioural import (
    InvalidBehaviouralInput,
    aggregate_credit_growth,
    corporate_investment_growth,
    fx_pass_through_inflation,
    household_consumption_growth,
    partial_adjustment_rate,
    refinancing_effective_rate,
    sovereign_spread,
)

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_status_vocabulary_and_every_mechanism_is_classified():
    registry = load_json("model/empirical_dynamics/mechanism_registry.json")
    allowed = {"ACTIVATED", "CANDIDATE", "REJECTED", "DEFERRED"}
    assert set(registry["status_vocabulary"]) == allowed
    assert registry["mechanisms"]
    assert all(item["classification"] in allowed for item in registry["mechanisms"])


def test_every_mechanism_has_evidence_observables_limits_and_rejection_gate():
    registry = load_json("model/empirical_dynamics/mechanism_registry.json")
    for item in registry["mechanisms"]:
        assert item["evidence"], item["id"]
        assert item["observables"], item["id"]
        assert item["limits"], item["id"]
        assert item["rejection_or_degradation_criteria"], item["id"]
        assert "functional_form" in item
        assert "estimation_plan" in item


def test_all_evidence_ids_resolve_to_registered_sources():
    mechanisms = load_json("model/empirical_dynamics/mechanism_registry.json")["mechanisms"]
    evidence = load_json("model/empirical_dynamics/evidence_registry.json")["sources"]
    source_ids = {item["id"] for item in evidence}
    used = {source for mechanism in mechanisms for source in mechanism["evidence"]}
    assert used <= source_ids
    assert all(item.get("url") for item in evidence)


def test_only_two_mechanisms_are_activated_for_initial_calibration_set():
    contract = load_json("model/empirical_dynamics/contract.json")
    registry = load_json("model/empirical_dynamics/mechanism_registry.json")
    activated = {m["id"] for m in registry["mechanisms"] if m["classification"] == "ACTIVATED"}
    assert activated == set(contract["activated_mechanisms"])
    assert activated == {
        "monetary_policy_lending_rate_pass_through",
        "government_refinancing_effective_rate",
    }


def test_rejected_and_deferred_mechanisms_are_not_central_feedbacks():
    registry = load_json("model/empirical_dynamics/mechanism_registry.json")
    for item in registry["mechanisms"]:
        if item["classification"] in {"REJECTED", "DEFERRED"}:
            assert item["central_feedback"] is False


def test_activated_equations_require_explicit_parameters_not_convenience_defaults():
    signature = inspect.signature(partial_adjustment_rate)
    assert signature.parameters["intercept"].default is inspect.Parameter.empty
    assert signature.parameters["long_run_pass_through"].default is inspect.Parameter.empty
    assert signature.parameters["adjustment_speed"].default is inspect.Parameter.empty

    signature = inspect.signature(refinancing_effective_rate)
    assert signature.parameters["refinancing_share"].default is inspect.Parameter.empty


def test_partial_adjustment_and_refinancing_forms_are_transparent_and_bounded_where_needed():
    assert partial_adjustment_rate(
        8.0,
        6.0,
        intercept=2.0,
        long_run_pass_through=1.0,
        adjustment_speed=0.25,
    ) == pytest.approx(8.0)
    assert refinancing_effective_rate(5.0, 7.0, refinancing_share=0.25) == pytest.approx(5.5)
    with pytest.raises(InvalidBehaviouralInput):
        partial_adjustment_rate(5.0, 6.0, intercept=0.0, long_run_pass_through=1.0, adjustment_speed=1.1)
    with pytest.raises(InvalidBehaviouralInput):
        refinancing_effective_rate(5.0, 7.0, refinancing_share=-0.1)


def test_candidate_forms_do_not_embed_signs_as_parameter_defaults():
    consumption = household_consumption_growth(
        disposable_income_growth=3.0,
        real_borrowing_rate=2.0,
        debt_service_ratio=1.0,
        intercept=0.0,
        income_sensitivity=1.0,
        rate_sensitivity=0.5,
        debt_service_sensitivity=0.25,
    )
    assert consumption == pytest.approx(1.75)

    investment = corporate_investment_growth(
        demand_growth=2.0,
        real_corporate_lending_rate=3.0,
        eu_fund_impulse=1.0,
        intercept=0.0,
        demand_sensitivity=1.0,
        rate_sensitivity=0.25,
        eu_fund_sensitivity=0.5,
    )
    assert investment == pytest.approx(1.75)

    credit = aggregate_credit_growth(
        activity_growth=2.0,
        real_lending_rate=3.0,
        npl_ratio=4.0,
        capital_buffer=1.0,
        intercept=0.0,
        activity_sensitivity=1.0,
        rate_sensitivity=0.1,
        npl_sensitivity=0.2,
        capital_sensitivity=0.3,
    )
    assert credit == pytest.approx(1.2)

    spread = sovereign_spread(
        debt_to_gdp=60.0,
        deficit_to_gdp=8.0,
        external_risk_proxy=1.0,
        intercept=0.0,
        debt_sensitivity=1.0,
        deficit_sensitivity=2.0,
        external_risk_sensitivity=3.0,
    )
    assert spread == pytest.approx(79.0)


def test_fx_pass_through_requires_explicit_lag_weights_and_has_no_historical_hard_code():
    assert fx_pass_through_inflation(
        baseline_inflation=3.0,
        depreciation_lags=(1.0, 2.0),
        lag_weights=(0.1, 0.2),
    ) == pytest.approx(3.5)
    with pytest.raises(InvalidBehaviouralInput):
        fx_pass_through_inflation(baseline_inflation=3.0, depreciation_lags=(1.0,), lag_weights=())


def test_empirical_contract_preserves_prior_invariants_and_holdout_rule():
    contract = load_json("model/empirical_dynamics/contract.json")
    invariants = contract["hard_invariants"]
    assert all(invariants.values())
    assert "cannot subsequently be reported as independent validation" in contract["next_stage"]["holdout_rule"]
