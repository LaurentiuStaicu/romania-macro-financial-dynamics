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


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "fx_inflation_transform_lag_window_contract.json"
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Retained for explicitness; design building is summary-only.",
    )
    args = parser.parse_args()
    _ = args

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    expected = contract["prerequisite_source_vintage"][
        "normalized_csv_sha256"
    ]
    observed = sha256(SOURCE)
    if observed != expected:
        raise SystemExit("retained FX-inflation source CSV SHA-256 mismatch")

    # Hard isolation: the runner never loads source values after selection end.
    selection_end = contract["windows"]["structural_selection"].split("..")[1]
    records = read_level_records(SOURCE, max_period=selection_end)
    rows = build_design_rows(
        records,
        first_target=contract["windows"]["first_eligible_target"],
        last_target=selection_end,
    )
    calibration_start, calibration_end = contract["windows"][
        "initial_calibration"
    ].split("..")
    selection_start, selection_end = contract["windows"][
        "structural_selection"
    ].split("..")
    calibration = rows_in_window(
        rows, calibration_start, calibration_end
    )
    selection = rows_in_window(
        rows, selection_start, selection_end
    )

    result = {
        "status": "DESIGN_READY_NO_ESTIMATION",
        "source_sha256": observed,
        "source_max_period_loaded": selection_end,
        "first_design_target": rows[0]["period"],
        "last_design_target": rows[-1]["period"],
        "design_rows": len(rows),
        "calibration_rows": len(calibration),
        "selection_rows": len(selection),
        "final_evaluation_window": contract["windows"][
            "final_evaluation"
        ],
        "final_evaluation_loaded": False,
        "estimation_performed": False,
        "system_dynamics_activation": False,
        "behavioural_closure_change": False,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
