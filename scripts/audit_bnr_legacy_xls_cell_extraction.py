from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import xlrd
from xlrd.biffh import (
    XL_CELL_BLANK,
    XL_CELL_BOOLEAN,
    XL_CELL_DATE,
    XL_CELL_EMPTY,
    XL_CELL_ERROR,
    XL_CELL_NUMBER,
    XL_CELL_TEXT,
    error_text_from_code,
)
from xlrd.xldate import xldate_as_datetime

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT / "model" / "calibration_validation"
    / "bnr_legacy_xls_cell_extraction_contract.json"
)
OUT = Path(
    os.environ.get(
        "BNR_LEGACY_XLS_EXTRACTION_OUT",
        "bnr_legacy_xls_extraction_artifacts",
    )
)

CELL_TYPES = {
    XL_CELL_EMPTY: "empty",
    XL_CELL_TEXT: "text",
    XL_CELL_NUMBER: "number",
    XL_CELL_DATE: "date",
    XL_CELL_BOOLEAN: "boolean",
    XL_CELL_ERROR: "error",
    XL_CELL_BLANK: "blank",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def col_name(index: int) -> str:
    if index < 0:
        raise ValueError(index)
    out = ""
    value = index + 1
    while value:
        value, rem = divmod(value - 1, 26)
        out = chr(65 + rem) + out
    return out


def coordinate(rowx: int, colx: int) -> str:
    return f"{col_name(colx)}{rowx + 1}"


def scalar_cell(cell: xlrd.sheet.Cell, datemode: int) -> tuple[str, object] | None:
    ctype = cell.ctype
    if ctype in {XL_CELL_EMPTY, XL_CELL_BLANK}:
        return None
    kind = CELL_TYPES.get(ctype, f"unknown_{ctype}")
    value = cell.value
    if ctype == XL_CELL_DATE:
        value = xldate_as_datetime(value, datemode).isoformat()
    elif ctype == XL_CELL_BOOLEAN:
        value = bool(value)
    elif ctype == XL_CELL_ERROR:
        value = {
            "code": int(value),
            "text": error_text_from_code.get(int(value), "UNKNOWN_ERROR"),
        }
    elif ctype == XL_CELL_NUMBER:
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("non-finite numeric workbook cell")
    elif ctype == XL_CELL_TEXT:
        value = str(value)
    return kind, value


def extract_workbook(path: Path, source_id: str, anchor_tokens: list[str]) -> dict:
    book = xlrd.open_workbook(
        filename=str(path),
        on_demand=False,
        formatting_info=False,
        ignore_workbook_corruption=False,
    )
    sheets = []
    anchor_hits = {token: [] for token in anchor_tokens}
    total_cells = 0

    for sheet_index in range(book.nsheets):
        sh = book.sheet_by_index(sheet_index)
        cells = []
        for rowx in range(sh.nrows):
            for colx in range(sh.ncols):
                parsed = scalar_cell(sh.cell(rowx, colx), book.datemode)
                if parsed is None:
                    continue
                kind, value = parsed
                item = {
                    "coordinate": coordinate(rowx, colx),
                    "row_1based": rowx + 1,
                    "column_1based": colx + 1,
                    "type": kind,
                    "value": value,
                }
                cells.append(item)
                total_cells += 1
                if kind == "text":
                    stripped = str(value).strip()
                    for token in anchor_tokens:
                        if stripped == token:
                            anchor_hits[token].append(
                                {
                                    "sheet": sh.name,
                                    "coordinate": item["coordinate"],
                                }
                            )

        sheets.append(
            {
                "index": sheet_index,
                "name": sh.name,
                "nrows": sh.nrows,
                "ncols": sh.ncols,
                "non_empty_cell_count": len(cells),
                "cells": cells,
            }
        )

    return {
        "source_id": source_id,
        "file": path.name,
        "book_datemode": book.datemode,
        "sheet_count": book.nsheets,
        "sheet_names": book.sheet_names(),
        "non_empty_cell_count": total_cells,
        "anchor_hits": anchor_hits,
        "sheets": sheets,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    source_root = ROOT / contract["source_vintage"]
    anchor_tokens = list(contract["preregistered_anchor_tokens"])
    outputs = []
    all_pass = True

    if xlrd.__version__ != contract["extraction_engine"]["version"]:
        raise RuntimeError(
            f"xlrd version mismatch: {xlrd.__version__} != "
            f"{contract['extraction_engine']['version']}"
        )

    for item in contract["files"]:
        path = source_root / item["path"]
        if not path.is_file():
            raise FileNotFoundError(path)
        actual_size = path.stat().st_size
        actual_hash = sha256(path)
        if actual_size != item["bytes"] or actual_hash != item["sha256"]:
            raise RuntimeError(
                f"source mismatch for {item['id']}: "
                f"size={actual_size}, sha256={actual_hash}"
            )

        extracted = extract_workbook(path, item["id"], anchor_tokens)
        if extracted["sheet_count"] < 1 or extracted["non_empty_cell_count"] < 1:
            all_pass = False
        out_path = OUT / f"{item['id']}_cells.json"
        out_path.write_text(
            json.dumps(extracted, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        outputs.append(
            {
                "source_id": item["id"],
                "source_path": str(path.relative_to(ROOT)),
                "source_bytes": actual_size,
                "source_sha256": actual_hash,
                "output_path": out_path.name,
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

    audit = {
        "audit_version": "0.1",
        "phase": contract["phase"],
        "status": (
            "PASS_LEGACY_XLS_TABULAR_EXTRACTION_PATH_AVAILABLE"
            if all_pass
            else "FAIL_LEGACY_XLS_TABULAR_EXTRACTION_PATH"
        ),
        "engine": {
            "package": "xlrd",
            "version": xlrd.__version__,
            "distribution_filename": os.environ.get("XLRD_DISTRIBUTION_FILENAME"),
            "distribution_sha256": os.environ.get("XLRD_DISTRIBUTION_SHA256"),
        },
        "source_vintage": contract["source_vintage"],
        "workbooks": outputs,
        "all_seven_workbooks_parsed": len(outputs) == 7 and all_pass,
        "behavioural_variable_selection_performed": False,
        "longitudinal_series_materialised": False,
        "dsti_level_claim": False,
        "parameter_estimation_performed": False,
        "model_selection_performed": False,
        "model_outcomes_accessed": False,
        "system_dynamics_activation": False,
        "behavioural_closure_change": False,
        "hard_rules": contract["hard_rules"],
    }
    audit_path = OUT / "bnr_legacy_xls_cell_extraction_audit.json"
    audit_path.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": audit["status"],
                "engine": audit["engine"],
                "workbooks": [
                    {
                        "source_id": item["source_id"],
                        "sheet_count": item["sheet_count"],
                        "sheet_names": item["sheet_names"],
                        "non_empty_cell_count": item["non_empty_cell_count"],
                        "anchor_hit_counts": item["anchor_hit_counts"],
                    }
                    for item in outputs
                ],
                "behavioural_variable_selection_performed": False,
            },
            indent=2,
        )
    )
    if audit["status"] != "PASS_LEGACY_XLS_TABULAR_EXTRACTION_PATH_AVAILABLE":
        raise SystemExit("legacy XLS extraction gate failed")


if __name__ == "__main__":
    main()
