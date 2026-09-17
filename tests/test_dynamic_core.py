import json
from math import exp
from pathlib import Path

import pytest

from romania_macro_financial_dynamics.accounting import AccountingCell, expand_matrix
from romania_macro_financial_dynamics.dynamics import (
    DEFAULT_DT_YEARS,
    IncompleteEmpiricalState,
    PositionChange,
    PositionKey,
    advance_position,
    advance_position_rates,
    apply_period_changes,
    empirical_cells_to_state,
    first_order_delay_derivative,
    rate_to_period_amount,
    safe_ratio,
    sector_balance_sheets,
    simulate_first_order_delay_euler,
    system_net_financial_worth,
)

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_period_stock_identity():
    closing = advance_position(
        100.0,
        PositionChange(transactions=10.0, revaluations=5.0, other_changes=-2.0),
    )
    assert closing == pytest.approx(113.0)


def test_rate_units_convert_through_dt_before_stock_update():
    assert DEFAULT_DT_YEARS == 0.25
    assert rate_to_period_amount(40.0, 0.25) == pytest.approx(10.0)
    assert advance_position_rates(100.0, transaction_rate=40.0, dt_years=0.25) == pytest.approx(110.0)


def test_zero_flow_extreme_condition_keeps_stock_unchanged():
    key = PositionKey("H", "G", "F3")
    opening = {key: 123.45}
    closing = apply_period_changes(opening, {key: PositionChange()})
    assert closing == opening


def test_large_finite_values_remain_finite_and_follow_identity():
    opening = 1e250
    closing = advance_position(opening, PositionChange(transactions=1e249))
    assert closing == pytest.approx(1.1e250)


def test_bilateral_representation_enforces_double_entry_conservation():
    positions = {
        PositionKey("H", "G", "F3"): 100.0,
        PositionKey("F", "C", "F4"): 50.0,
        PositionKey("X", "G", "F3"): 25.0,
    }
    sheets = sector_balance_sheets(positions)
    assert sheets["H"]["assets"] == pytest.approx(100.0)
    assert sheets["G"]["liabilities"] == pytest.approx(125.0)
    assert sheets["F"]["assets"] == pytest.approx(50.0)
    assert sheets["C"]["liabilities"] == pytest.approx(50.0)
    assert system_net_financial_worth(positions) == pytest.approx(0.0, abs=1e-12)


def test_self_holding_contributes_assets_and_liabilities_but_zero_net():
    key = PositionKey("G", "G", "F3")
    sheets = sector_balance_sheets({key: 20.0})
    assert sheets["G"]["assets"] == pytest.approx(20.0)
    assert sheets["G"]["liabilities"] == pytest.approx(20.0)
    assert sheets["G"]["net_financial_worth"] == pytest.approx(0.0)


def test_unresolved_accounting_matrix_cannot_initialize_simulation():
    spec = load_json("model/accounting/benchmark_2025.json")
    cells = expand_matrix("F2", "stock", spec["matrices"]["F2"]["stock"])
    with pytest.raises(IncompleteEmpiricalState):
        empirical_cells_to_state(cells)


def test_complete_derived_matrix_can_initialize_simulation_without_missing_equals_zero_shortcut():
    cells = []
    for holder in ("H", "C", "F", "G", "X", "BNR"):
        for issuer in ("H", "C", "F", "G", "X", "BNR"):
            cells.append(
                AccountingCell(
                    holder=holder,
                    issuer=issuer,
                    instrument="F3",
                    measure="stock",
                    status="DERIVED",
                    value=100.0 if (holder, issuer) == ("H", "G") else 0.0,
                )
            )
    state = empirical_cells_to_state(cells)
    assert len(state) == 36
    assert state[PositionKey("H", "G", "F3")] == pytest.approx(100.0)


def test_first_order_delay_steady_state_extreme_condition():
    assert first_order_delay_derivative(10.0, 10.0, 1.0) == pytest.approx(0.0)
    final = simulate_first_order_delay_euler(
        initial=10.0,
        input_value=10.0,
        tau_years=1.0,
        horizon_years=5.0,
        dt_years=0.25,
    )
    assert final == pytest.approx(10.0)


def test_halving_time_step_reduces_first_order_delay_integration_error():
    expected = 1.0 - exp(-1.0)
    coarse = simulate_first_order_delay_euler(
        initial=0.0,
        input_value=1.0,
        tau_years=1.0,
        horizon_years=1.0,
        dt_years=0.25,
    )
    fine = simulate_first_order_delay_euler(
        initial=0.0,
        input_value=1.0,
        tau_years=1.0,
        horizon_years=1.0,
        dt_years=0.125,
    )
    assert abs(fine - expected) < abs(coarse - expected)


def test_delay_and_time_step_reject_non_physical_values():
    with pytest.raises(ValueError):
        first_order_delay_derivative(1.0, 0.0, 0.0)
    with pytest.raises(ValueError):
        rate_to_period_amount(1.0, 0.0)


def test_zero_denominator_ratio_is_explicitly_undefined():
    assert safe_ratio(10.0, 0.0) is None
    assert safe_ratio(10.0, 2.0) == pytest.approx(5.0)


def test_dynamic_core_contract_defers_behavioural_closure():
    contract = load_json("model/dynamics/core_contract.json")
    assert contract["time"]["default_dt_years"] == 0.25
    assert contract["behavioural_closure"]["included_in_alpha_0_3"] is False
    assert contract["empirical_initialization_gate"]["unresolved_accounting_cells_allowed"] is False
    assert "integration_error_convergence" in contract["required_tests"]


def test_feedback_candidates_are_documented_but_numerically_inactive():
    registry = load_json("model/dynamics/feedback_registry.json")
    assert registry["loops"]
    assert all(loop["scientific_status"] == "BEHAVIOURAL_CANDIDATE" for loop in registry["loops"])
    assert all(loop["quantitatively_active"] is False for loop in registry["loops"])
    assert all(delay["active"] is False and delay["tau"] == "TBD" for delay in registry["delay_candidates"])
