from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "bnr_bls_missing_round_semantic_mapping_contract.json"
)
OUT = Path(
    os.environ.get(
        "BNR_BLS_MISSING_ROUND_SEMANTIC_OUT",
        "bnr_bls_missing_round_semantic_mapping_artifacts",
    )
)


def load_cells(path: Path) -> dict[str, dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        sheet["name"]: {
            cell["coordinate"]: cell["value"]
            for cell in sheet["cells"]
        }
        for sheet in payload["sheets"]
    }


def choose_sheet(
    sheets: dict[str, dict[str, object]],
    aliases: list[str],
) -> tuple[str, dict[str, object]]:
    hits = [name for name in aliases if name in sheets]
    if len(hits) != 1:
        raise ValueError(f"expected one sheet alias from {aliases}, got {hits}")
    return hits[0], sheets[hits[0]]


def quarter_from_date(text: str) -> str:
    dt = datetime.strptime(text, "%d/%m/%Y")
    return f"{dt.year:04d}-Q{(dt.month - 1) // 3 + 1}"


def numeric(cellmap: dict[str, object], coord: str) -> float:
    value = cellmap.get(coord)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"expected numeric {coord}, got {value!r}")
    return float(value)


def resolve_round_identity(
    item: dict,
    companies: dict[str, object],
) -> dict:
    header = item["workbook_header"]
    actual = companies.get(header["cell"])
    if actual != header["raw_value"]:
        raise ValueError(
            f"{item['source_id']} raw header changed: {actual!r} "
            f"!= {header['raw_value']!r}"
        )

    authority = item["round_authority"]
    if authority == "WORKBOOK_COMPANIES_A1":
        if not isinstance(actual, str):
            raise ValueError(f"{item['source_id']} non-text workbook date")
        quarter = quarter_from_date(actual)
        if quarter != item["target_quarter"]:
            raise ValueError(
                f"{item['source_id']} workbook quarter {quarter} "
                f"!= target {item['target_quarter']}"
            )
        return {
            "authority": authority,
            "raw_workbook_header": actual,
            "resolved_quarter": quarter,
            "official_publication": None,
        }

    if authority == "OFFICIAL_BNR_PUBLICATION_QUARTER":
        publication = item["official_publication"]
        if not publication:
            raise ValueError(
                f"{item['source_id']} missing frozen publication authority"
            )
        declared = publication["declared_period"]
        expected_declared = {
            "2023-Q2": "Trimestrul II 2023",
            "2024-Q2": "Trimestrul II 2024",
        }.get(item["target_quarter"])
        if declared != expected_declared:
            raise ValueError(
                f"{item['source_id']} publication period mismatch: "
                f"{declared!r} != {expected_declared!r}"
            )
        return {
            "authority": authority,
            "raw_workbook_header": actual,
            "workbook_header_status": header["status"],
            "resolved_quarter": item["target_quarter"],
            "official_publication": publication,
            "silent_date_normalisation_performed": False,
        }

    raise ValueError(f"unsupported round authority: {authority}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    mapping = json.loads(
        (ROOT / contract["mapping_authority"]).read_text(encoding="utf-8")
    )
    source_root = ROOT / contract["extraction_vintage"]

    results = []
    all_pass = True
    for item in contract["rounds"]:
        sheets = load_cells(source_root / item["file"])
        _, companies = choose_sheet(
            sheets, mapping["sheet_name_aliases"]["companies"]
        )
        _, households = choose_sheet(
            sheets, mapping["sheet_name_aliases"]["households"]
        )

        round_identity = resolve_round_identity(item, companies)
        row = {
            "quarter": round_identity["resolved_quarter"],
            "source_id": item["source_id"],
            "source_kind": "retained_legacy_xls_semantic_coordinate_review",
        }
        validations = {}

        for obs in mapping["realised_observables"]:
            cellmap = (
                companies
                if obs["question_id"].startswith("C")
                else households
            )
            question = cellmap.get(obs["question_cell"])
            if question != obs["question_id"]:
                raise ValueError(
                    f"{item['source_id']} {obs['id']} question mismatch at "
                    f"{obs['question_cell']}: {question!r}"
                )
            metric = str(
                cellmap.get(obs["metric_label_cell"], "")
            ).strip()
            if metric not in obs["allowed_metric_labels"]:
                raise ValueError(
                    f"{item['source_id']} {obs['id']} metric mismatch: "
                    f"{metric!r}"
                )
            value = numeric(cellmap, obs["net_percentage_cell"])
            row[obs["id"]] = value
            validations[obs["id"]] = {
                "question_id": obs["question_id"],
                "question_cell": obs["question_cell"],
                "metric_label_cell": obs["metric_label_cell"],
                "metric_label": metric,
                "value_cell": obs["net_percentage_cell"],
                "value": value,
                "sign_convention": obs["sign_convention"],
            }

        for qid, coord in contract["dsti_boundary"][
            "verify_question_ids"
        ].items():
            if households.get(coord) != qid:
                raise ValueError(
                    f"{item['source_id']} missing DSTI boundary marker "
                    f"{qid} at {coord}"
                )

        results.append(
            {
                "source_id": item["source_id"],
                "target_quarter": item["target_quarter"],
                "round_identity": round_identity,
                "row": row,
                "observable_validations": validations,
                "all_six_observables_passed": len(validations) == 6,
                "dsti_boundary_markers_verified": True,
            }
        )
        all_pass = all_pass and len(validations) == 6

    status = (
        "PASS_MISSING_ROUND_SEMANTIC_COORDINATE_MAPPING_WITH_EXPLICIT_ROUND_IDENTITY_BRIDGES"
        if len(results) == 3 and all_pass
        else "FAIL_MISSING_ROUND_SEMANTIC_COORDINATE_MAPPING"
    )
    audit = {
        "audit_version": "0.1",
        "phase": contract["phase"],
        "status": status,
        "mapping_authority": contract["mapping_authority"],
        "extraction_vintage": contract["extraction_vintage"],
        "results": results,
        "passed_rounds": [
            item["target_quarter"]
            for item in results
            if item["all_six_observables_passed"]
        ],
        "canonical_panel_modified": False,
        "interpolation_performed": False,
        "synthetic_quarters_created": False,
        "parameter_estimation_performed": False,
        "model_selection_performed": False,
        "holdout_opened": False,
        "system_dynamics_activation": False,
        "behavioural_closure_change": False,
        "hard_rules": contract["hard_rules"],
        "pass_effect": contract["pass_effect"],
    }
    out_path = OUT / "bnr_bls_missing_round_semantic_mapping_audit.json"
    out_path.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2, ensure_ascii=False))
    if not status.startswith("PASS_"):
        raise SystemExit("missing-round semantic mapping review failed")


if __name__ == "__main__":
    main()
