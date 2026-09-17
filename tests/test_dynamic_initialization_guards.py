import json
from pathlib import Path

import pytest

from romania_macro_financial_dynamics.accounting import AccountingCell, INSTRUMENT_PRIORITY, SECTOR_IDS
from romania_macro_financial_dynamics.dynamics import IncompleteEmpiricalState, empirical_cells_to_state

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def complete_f3_cells():
    return [
        AccountingCell(
            holder=holder,
            issuer=issuer,
            instrument="F3",
            measure="stock",
            status="DERIVED",
            value=0.0,
        )
        for holder in SECTOR_IDS
        for issuer in SECTOR_IDS
    ]


def test_duplicate_empirical_address_is_rejected_even_if_address_set_looks_complete():
    cells = complete_f3_cells()
    cells.append(cells[0])
    with pytest.raises(IncompleteEmpiricalState):
        empirical_cells_to_state(cells)


def test_dynamic_boundary_exactly_matches_accounting_spine_boundary_and_priority():
    contract = load_json("model/dynamics/core_contract.json")
    assert tuple(contract["boundary"]["sectors"]) == SECTOR_IDS
    assert tuple(contract["boundary"]["financial_instruments"]) == INSTRUMENT_PRIORITY
    assert contract["boundary"]["closed_for_double_entry_conservation"] is True


def test_dynamic_model_contract_marks_accounting_spine_as_hard_constraint():
    contract = load_json("model/registries/model_contract.json")
    dynamic = contract["dynamic_core"]
    assert dynamic["accounting_spine_is_hard_constraint"] is True
    assert dynamic["behavioural_closure_active"] is False
    assert dynamic["canonical_time_unit"] == "year"
    assert dynamic["default_dt_years"] == 0.25
