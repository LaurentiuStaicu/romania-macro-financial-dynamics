from __future__ import annotations

import json
import os
from pathlib import Path

import xlrd

from audit_bnr_legacy_xls_cell_extraction import extract_workbook, sha256

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "bnr_bls_missing_round_cell_extraction_contract.json"
)
OUT = Path(
    os.environ.get(
        "BNR_BLS_MISSING_ROUND_CELL_EXTRACTION_OUT",
        "bnr_bls_missing_round_cell_extraction_artifacts",
    )
)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    engine = contract["extraction_engine"]
    if xlrd.__version__ != engine["version"]:
        raise RuntimeError(
            f"xlrd version mismatch: {xlrd.__version__} != {engine['version']}"
        )

    source_root = ROOT / contract["source_vintage"]
    tokens = list(contract["preregistered_anchor_tokens"])
    outputs: list[dict] = []
    all_pass = True

    for item in contract["files"]:
        path = source_root / item["path"]
        if not path.is_file():
            raise FileNotFoundError(path)
        size = path.stat().st_size
        digest = sha256(path)
        if size != item["bytes"] or digest != item["sha256"]:
            raise RuntimeError(
                f"source mismatch for {item['id']}: size={size}, sha256={digest}"
            )

        extracted = extract_workbook(path, item["id"], tokens)
        if extracted["sheet_count"] < 1 or extracted["non_empty_cell_count"] < 1:
            all_pass = False

        out_name = f"{item['id']}_cells.json"
        out_path = OUT / out_name
        out_path.write_text(
            json.dumps(extracted, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        outputs.append(
            {
                "source_id": item["id"],
                "target_quarter": item["target_quarter"],
                "source_path": str(path.relative_to(ROOT)),
                "source_bytes": size,
                "source_sha256": digest,
                "output_path": out_name,
                "output_bytes": out_path.stat().st_size,
                "output_sha256": sha256(out_path),
                "sheet_count": extracted["sheet_count"],
                "sheet_names": extracted["sheet_names"],
                "non_empty_cell_count": extracted["non_empty_cell_count"],
                "anchor_hit_counts": {
                    token: len(hits)
                    for token, hits in extracted["anchor_hits"].items()
                },
            }
        )

    status = (
        "PASS_MISSING_ROUND_LEGACY_XLS_CELL_EXTRACTION"
        if len(outputs) == 3 and all_pass
        else "FAIL_MISSING_ROUND_LEGACY_XLS_CELL_EXTRACTION"
    )
    audit = {
        "audit_version": "0.1",
        "phase": contract["phase"],
        "status": status,
        "engine": {
            "package": engine["package"],
            "version": xlrd.__version__,
            "distribution_filename": os.environ.get(
                "XLRD_DISTRIBUTION_FILENAME"
            ),
            "distribution_sha256": os.environ.get(
                "XLRD_DISTRIBUTION_SHA256"
            ),
        },
        "source_vintage": contract["source_vintage"],
        "workbooks": outputs,
        "all_three_workbooks_parsed": len(outputs) == 3 and all_pass,
        "behavioural_variable_selection_performed": False,
        "canonical_panel_modified": False,
        "longitudinal_series_materialised": False,
        "parameter_estimation_performed": False,
        "model_selection_performed": False,
        "model_outcomes_accessed": False,
        "system_dynamics_activation": False,
        "behavioural_closure_change": False,
        "hard_rules": contract["hard_rules"],
    }
    audit_path = OUT / "bnr_bls_missing_round_cell_extraction_audit.json"
    audit_path.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2, ensure_ascii=False))
    if status != "PASS_MISSING_ROUND_LEGACY_XLS_CELL_EXTRACTION":
        raise SystemExit("missing-round legacy XLS cell extraction failed")


if __name__ == "__main__":
    main()
