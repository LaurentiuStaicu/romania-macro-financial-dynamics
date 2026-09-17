import json
from pathlib import Path

import pytest

from romania_macro_financial_dynamics.government_repricing import (
    RepricingIdentifiabilityError,
    ledger_diagnostics,
    load_ledger,
    reconstructed_effective_rate_pct,
)

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data/processed/government_repricing_ledger_0.5.2a0.csv"


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_acceptance_contract_was_frozen_before_assessment():
    contract = load_json("model/calibration_validation/government_repricing_ledger_contract.json")
    assert contract["frozen_before_ledger_assessment"] is True
    assert contract["prospective_acceptance_gates"]["gate_1_ledger_completeness"]["minimum_opening_principal_coverage_pct"] == 95.0
    assert contract["prospective_acceptance_gates"]["gate_1_ledger_completeness"]["minimum_repricing_event_principal_coverage_pct"] == 90.0
    assert contract["prospective_acceptance_gates"]["gate_3_portfolio_cost_reconstruction"]["maximum_absolute_error_pp_each_snapshot"] == 0.10
    assert contract["hard_prohibitions"]["redemption_share_as_repricing_share"] is True
    assert contract["hard_prohibitions"]["aggregate_refixing_share_paired_with_one_auction_yield"] is True
    assert contract["household_delta_policy_freeze"]["future_observations_reserved_from"] == "2026-08"
    assert contract["household_delta_policy_freeze"]["may_respecify_before_first_new_policy_rate_event_test"] is False


def test_public_ledger_is_audited_but_not_definitionally_complete():
    rows = load_ledger(LEDGER)
    diagnostics = ledger_diagnostics(rows)
    assert diagnostics["rows"] == 7
    assert diagnostics["currencies"] == ["EUR", "RON"]
    assert diagnostics["rate_types_observed"] == ["FIXED"]
    assert diagnostics["rows_with_issue_size"] == 5
    assert diagnostics["rows_with_announced_principal"] == 2
    assert diagnostics["rows_with_opening_outstanding_principal"] == 0
    assert diagnostics["rows_with_principal_repriced"] == 0
    assert diagnostics["rows_with_matched_repricing"] == 0
    assert diagnostics["rows_with_contractual_refixing_date"] == 0


def test_issue_size_and_market_yield_are_not_silently_promoted_to_repricing_inputs():
    rows = load_ledger(LEDGER)
    assert all(row["opening_outstanding_principal"] == "" for row in rows)
    assert all(row["principal_repriced"] == "" for row in rows)
    assert all(row["old_effective_rate_pct"] == "" for row in rows)
    assert all(row["new_or_marginal_rate_pct"] == "" for row in rows)
    with pytest.raises(RepricingIdentifiabilityError):
        reconstructed_effective_rate_pct(rows)


def test_reconstruction_works_only_for_complete_same_currency_blocks():
    complete = [
        {
            "record_id": "a",
            "currency": "RON",
            "opening_outstanding_principal": "100",
            "principal_repriced": "50",
            "old_effective_rate_pct": "4",
            "new_or_marginal_rate_pct": "6",
            "synthetic_allocation": "false",
        },
        {
            "record_id": "b",
            "currency": "RON",
            "opening_outstanding_principal": "100",
            "principal_repriced": "0",
            "old_effective_rate_pct": "5",
            "new_or_marginal_rate_pct": "",
            "synthetic_allocation": "false",
        },
    ]
    assert reconstructed_effective_rate_pct(complete) == pytest.approx(5.0)

    cross_currency = complete + [
        {
            "record_id": "c",
            "currency": "EUR",
            "opening_outstanding_principal": "100",
            "principal_repriced": "0",
            "old_effective_rate_pct": "3",
            "new_or_marginal_rate_pct": "",
            "synthetic_allocation": "false",
        }
    ]
    with pytest.raises(RepricingIdentifiabilityError):
        reconstructed_effective_rate_pct(cross_currency)


def test_final_assessment_preserves_negative_result_and_alpha_0_6_gate():
    assessment = load_json("model/calibration_validation/government_repricing_ledger_assessment.json")
    assert assessment["gate_results"]["gate_1_ledger_completeness"]["status"] == "FAIL"
    assert assessment["gate_results"]["gate_2_balance_reconciliation"]["status"] == "NOT_OPENED"
    assert assessment["gate_results"]["gate_3_portfolio_cost_reconstruction"]["status"] == "NOT_OPENED"
    assert assessment["estimation"]["run"] is False
    assert assessment["final_verdict"] == "DEFERRED"
    assert assessment["candidate_eligibility"] is False
    assert assessment["validated_eligibility"] is False
    assert assessment["validated_reference_behavioural_mechanisms_after_stage"] == 0
    assert assessment["alpha_0_6_gate"] == "NO_GO"
    assert assessment["household_delta_policy"]["respecified_in_alpha_0_5_2"] is False
