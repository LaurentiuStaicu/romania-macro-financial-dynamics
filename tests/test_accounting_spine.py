import json
from pathlib import Path

import pytest

from romania_macro_financial_dynamics.accounting import (
    INSTRUMENT_PRIORITY,
    SECTOR_IDS,
    AccountingCell,
    b9f,
    expand_matrix,
    observed_sum,
    reconciliation_residual,
    validate_benchmark_spec,
)

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_benchmark_contract_is_machine_valid():
    spec = load_json("model/accounting/benchmark_2025.json")
    validate_benchmark_spec(spec)
    assert spec["benchmark"]["stock_date"] == "2025-12-31"
    assert spec["instrument_priority"] == list(INSTRUMENT_PRIORITY)


def test_every_instrument_has_complete_6x6_stock_and_flow_address_space():
    spec = load_json("model/accounting/benchmark_2025.json")
    for instrument in INSTRUMENT_PRIORITY:
        for measure in ("stock", "flow"):
            cells = expand_matrix(instrument, measure, spec["matrices"][instrument][measure])
            assert len(cells) == len(SECTOR_IDS) ** 2 == 36
            assert {(cell.holder, cell.issuer) for cell in cells} == {
                (holder, issuer) for holder in SECTOR_IDS for issuer in SECTOR_IDS
            }


def test_unresolved_cells_are_not_numeric_or_zero_filled():
    spec = load_json("model/accounting/benchmark_2025.json")
    cells = expand_matrix("F2", "stock", spec["matrices"]["F2"]["stock"])
    assert all(cell.status == "TBD" for cell in cells)
    assert all(cell.value is None for cell in cells)
    assert observed_sum(cells) is None


def test_partial_f3_source_is_labelled_not_promoted_to_observation():
    spec = load_json("model/accounting/benchmark_2025.json")
    cells = expand_matrix("F3", "stock", spec["matrices"]["F3"]["stock"])
    target = next(cell for cell in cells if cell.holder == "X" and cell.issuer == "G")
    assert target.status == "SOURCE_SERIES_IDENTIFIED"
    assert target.value is None
    assert target.source_series_key == "QSA.Q.N.RO.W1.S13.S1.N.L.LE.F3.L._Z.XDC._T.S.V.N._T"


def test_aggregate_anchors_are_kept_outside_bilateral_cells():
    spec = load_json("model/accounting/benchmark_2025.json")
    anchor_ids = {item["id"] for item in spec["observed_anchors"]}
    assert "gfs_maastricht_debt_ratio_2025q4" in anchor_ids
    assert "qsa_nonresident_debt_securities_total_economy_2025q4" in anchor_ids
    assert "qsa_government_loan_assets_2025q4" in anchor_ids

    observed_cells = []
    for instrument in INSTRUMENT_PRIORITY:
        for measure in ("stock", "flow"):
            observed_cells.extend(
                cell
                for cell in expand_matrix(instrument, measure, spec["matrices"][instrument][measure])
                if cell.status == "OBSERVED"
            )
    assert observed_cells == []


def test_reconciliation_helpers_refuse_missing_values_and_apply_identities():
    assert reconciliation_residual(None, 10.0) is None
    assert reconciliation_residual(12.0, 10.0) == pytest.approx(2.0)
    assert b9f(None, 5.0) is None
    assert b9f(100.0, 70.0) == pytest.approx(30.0)


def test_accounting_cell_rejects_silent_numeric_tbd():
    with pytest.raises(ValueError):
        AccountingCell(
            holder="H",
            issuer="G",
            instrument="F3",
            measure="stock",
            status="TBD",
            value=0.0,
        )


def test_source_registry_has_no_observed_control_masquerading_as_bilateral_cell():
    registry = load_json("model/accounting/source_registry.json")
    controls = [item for item in registry["verified_series"] if item["status"] == "OBSERVED_EMPIRICAL_CONTROL"]
    assert controls
    assert all("control" in item["use"].lower() for item in controls)


def test_reconciliation_ledger_covers_priority_sequence_and_prohibits_forced_closure():
    ledger = load_json("model/accounting/reconciliation_2025.json")
    gates = ledger["instrument_gates"]
    assert [item["instrument"] for item in gates] == list(INSTRUMENT_PRIORITY)
    checks = {item["id"]: item["status"] for item in ledger["closure_checks"]}
    assert checks["missing_is_not_zero"] == "ENFORCED"
    assert checks["forced_closure_prohibited"] == "ENFORCED"
