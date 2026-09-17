import json
from pathlib import Path

import pytest

from romania_macro_financial_dynamics.dynamics import PositionKey
from romania_macro_financial_dynamics.presentation import (
    auxiliary_context,
    build_balance_sheet_dashboard,
    build_stock_flow_graph,
    theory_context,
)

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def sample_positions():
    return {
        PositionKey("H", "G", "F3"): 100.0,
        PositionKey("F", "C", "F4"): 50.0,
        PositionKey("X", "G", "F3"): 25.0,
    }


def test_central_view_is_macro_financial_stock_flow_not_generic_network():
    contract = load_json("model/dynamics/presentation_contract.json")
    model_panel = contract["model_panel"]
    assert model_panel["workspace_area"] == "model"
    assert model_panel["primary_view"] == "macro_financial_stock_flow_network"
    assert model_panel["not_generic_network_diagram"] is True
    assert {node["id"] for node in model_panel["nodes"]} == {"H", "C", "F", "G", "X", "BNR"}
    assert {layer["id"] for layer in model_panel["edge_layers"]} == {
        "financial_positions",
        "transactions",
        "revaluations_and_other_changes",
        "candidate_feedbacks",
    }


def test_presentation_inherits_infoclar_without_redefining_foundations_or_user_draft():
    contract = load_json("model/dynamics/presentation_contract.json")
    assert contract["inherits"]["standard"] == "InfoClar Model Suite Design Standard v1.1"
    invariance = contract["foundation_invariance"]
    assert invariance["accounting_spine_unchanged"] is True
    assert invariance["infoclar_v1_1_unchanged"] is True
    assert invariance["draft_user_schema_in_repository"] is False


def test_candidate_feedback_overlay_is_visually_and_numerically_non_confirmatory():
    contract = load_json("model/dynamics/presentation_contract.json")
    overlay = next(
        item for item in contract["model_panel"]["edge_layers"] if item["id"] == "candidate_feedbacks"
    )
    assert overlay["default_visibility"] == "off"
    assert overlay["render_rule"] == "candidate_dashed_and_status_labelled"
    assert overlay["must_never_look_empirically_confirmed"] is True
    assert overlay["must_never_modify_numeric_state_in_alpha_0_3"] is True


def test_stock_flow_graph_payload_preserves_issuer_to_holder_semantics_and_exact_values():
    graph = build_stock_flow_graph(sample_positions(), period="2025-Q4")
    assert graph["view"] == "macro_financial_stock_flow_network"
    assert len(graph["nodes"]) == 6
    assert graph["essential_information_requires_hover"] is False
    assert graph["colour_only_encoding"] is False
    edge = next(item for item in graph["edges"] if item["id"] == "F3:G->H")
    assert edge["source"] == "G"
    assert edge["target"] == "H"
    assert edge["issuer"] == "G"
    assert edge["holder"] == "H"
    assert edge["value"] == pytest.approx(100.0)
    assert edge["semantic"] == "issuer_liability_equals_holder_asset"


def test_dashboard_payload_exposes_exact_sector_balance_sheets_and_conservation():
    dashboard = build_balance_sheet_dashboard(sample_positions(), period="2025-Q4")
    assert dashboard["view"] == "balance_sheet_dashboard"
    assert dashboard["conservation_expected"] is True
    assert dashboard["system_net_financial_worth"] == pytest.approx(0.0, abs=1e-12)
    government = next(row for row in dashboard["rows"] if row["sector"] == "G")
    assert government["liabilities"] == pytest.approx(125.0)
    assert government["unit"] == "million_RON"
    assert government["period"] == "2025-Q4"


def test_theory_learn_is_contextual_and_auxiliary_is_not_theory_duplicate():
    feedback_topics = theory_context("feedback_candidate")
    assert "evidence_status" in feedback_topics
    assert "why_inactive" in feedback_topics
    aux = auxiliary_context(
        object_id="government_refinancing_interest_loop",
        scientific_status="BEHAVIOURAL_CANDIDATE",
        limitations=["quantitatively inactive"],
    )
    assert aux["sections"] == ("selection_details", "sources", "verification", "limitations")
    assert "theory" not in aux["sections"]


def test_dashboard_contract_prioritizes_empirical_and_reconciliation_status_before_dynamic_structure():
    contract = load_json("model/dynamics/presentation_contract.json")
    groups = contract["dashboard_panel"]["indicator_groups"]
    assert [group["id"] for group in groups] == [
        "empirical_benchmark",
        "accounting_reconciliation",
        "dynamic_structure",
    ]
    assert [group["priority"] for group in groups] == [1, 2, 3]
    assert "unresolved_is_not_zero" in contract["dashboard_panel"]["requirements"]


def test_unit_registry_covers_stock_rate_time_and_dimensionless_contracts():
    registry = load_json("model/dynamics/unit_registry.json")
    variables = {item["id"]: item for item in registry["variables"]}
    assert variables["bilateral_financial_position"]["signature"] == {"currency": 1, "time": 0}
    assert variables["financial_transaction_rate"]["signature"] == {"currency": 1, "time": -1}
    assert variables["dt"]["signature"] == {"currency": 0, "time": 1}
    assert variables["safe_ratio"]["signature"] == {"currency": 0, "time": 0}
    assert all(check["status"] == "CONSISTENT" for check in registry["equation_checks"])
