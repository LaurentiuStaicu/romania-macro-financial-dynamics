from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "bnr_bls_panel_regeneration_candidate_contract.json"
)
OUT = Path(
    os.environ.get(
        "BNR_BLS_PANEL_REGENERATION_OUT",
        "bnr_bls_panel_regeneration_candidate_artifacts",
    )
)

FIELDS = [
    "quarter",
    "reference_date",
    "source_id",
    "source_kind",
    "nfc_credit_standards",
    "nfc_loan_demand",
    "household_mortgage_credit_standards",
    "household_consumer_credit_standards",
    "household_mortgage_loan_demand",
    "household_consumer_loan_demand",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quarter_index(period: str) -> int:
    year, quarter = period.split("-Q")
    return int(year) * 4 + int(quarter) - 1


def all_quarters(start: str, end: str) -> list[str]:
    first = quarter_index(start)
    last = quarter_index(end)
    result = []
    for index in range(first, last + 1):
        year, q0 = divmod(index, 4)
        result.append(f"{year:04d}-Q{q0 + 1}")
    return result


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in FIELDS})


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    panel_path = ROOT / contract["current_canonical_panel"]
    current_audit_path = ROOT / contract["current_canonical_audit"]
    semantic_path = ROOT / contract["semantic_review"]

    panel_hash_before = sha256(panel_path)
    current_rows = load_csv(panel_path)
    current_audit = json.loads(current_audit_path.read_text(encoding="utf-8"))
    semantic = json.loads(semantic_path.read_text(encoding="utf-8"))

    expected_current = contract["expected_current_state"]
    current_quarters = [row["quarter"] for row in current_rows]
    if len(current_rows) != expected_current["observed_round_count"]:
        raise RuntimeError("unexpected current canonical BLS row count")
    if current_quarters != expected_current["observed_quarters"]:
        raise RuntimeError(
            f"unexpected current canonical BLS quarters: {current_quarters}"
        )
    if current_audit["missing_quarters"] != expected_current["missing_quarters"]:
        raise RuntimeError("current canonical audit missing-quarter state changed")

    expected_semantic_status = (
        "PASS_MISSING_ROUND_SEMANTIC_COORDINATE_MAPPING_WITH_"
        "EXPLICIT_ROUND_IDENTITY_BRIDGES"
    )
    if semantic["status"] != expected_semantic_status:
        raise RuntimeError(f"semantic review not passed: {semantic['status']}")
    if semantic["passed_rounds"] != contract["authorized_additions"]:
        raise RuntimeError(
            f"unexpected semantic passed rounds: {semantic['passed_rounds']}"
        )

    existing = set(current_quarters)
    additions = []
    identity_audit = {}
    for item in semantic["results"]:
        quarter = item["target_quarter"]
        if quarter not in contract["authorized_additions"]:
            raise RuntimeError(f"unauthorized semantic round: {quarter}")
        if quarter in existing:
            raise RuntimeError(f"candidate would replace existing quarter: {quarter}")
        if not item["all_six_observables_passed"]:
            raise RuntimeError(f"semantic observables did not pass: {quarter}")
        if not item["dsti_boundary_markers_verified"]:
            raise RuntimeError(f"DSTI boundary markers not verified: {quarter}")

        identity = item["round_identity"]
        authority = identity["authority"]
        if authority == "WORKBOOK_COMPANIES_A1":
            reference_date = identity["raw_workbook_header"]
        elif authority == "OFFICIAL_BNR_PUBLICATION_QUARTER":
            if identity.get("silent_date_normalisation_performed") is not False:
                raise RuntimeError(
                    f"silent date normalisation state invalid: {quarter}"
                )
            reference_date = ""
        else:
            raise RuntimeError(
                f"unsupported round identity authority for {quarter}: {authority}"
            )

        source_row = item["row"]
        row = {
            "quarter": quarter,
            "reference_date": reference_date,
            "source_id": source_row["source_id"],
            "source_kind": source_row["source_kind"],
            "nfc_credit_standards": source_row["nfc_credit_standards"],
            "nfc_loan_demand": source_row["nfc_loan_demand"],
            "household_mortgage_credit_standards":
                source_row["household_mortgage_credit_standards"],
            "household_consumer_credit_standards":
                source_row["household_consumer_credit_standards"],
            "household_mortgage_loan_demand":
                source_row["household_mortgage_loan_demand"],
            "household_consumer_loan_demand":
                source_row["household_consumer_loan_demand"],
        }
        additions.append(row)
        identity_audit[quarter] = {
            "authority": authority,
            "canonical_reference_date": reference_date,
            "raw_workbook_header": identity["raw_workbook_header"],
            "official_publication": identity.get("official_publication"),
            "synthetic_reference_date_created": False,
        }

    candidate_rows: list[dict[str, object]] = [dict(row) for row in current_rows]
    candidate_rows.extend(additions)
    candidate_rows.sort(key=lambda row: quarter_index(str(row["quarter"])))

    candidate_quarters = [str(row["quarter"]) for row in candidate_rows]
    if len(candidate_quarters) != len(set(candidate_quarters)):
        raise RuntimeError(f"duplicate candidate quarters: {candidate_quarters}")

    expected_candidate = contract["expected_candidate_state"]
    if len(candidate_rows) != expected_candidate["observed_round_count"]:
        raise RuntimeError("unexpected candidate row count")

    expected_grid = all_quarters(candidate_quarters[0], candidate_quarters[-1])
    missing = [q for q in expected_grid if q not in set(candidate_quarters)]
    if missing != expected_candidate["missing_quarters"]:
        raise RuntimeError(f"unexpected candidate missing quarters: {missing}")

    candidate_panel = OUT / contract["candidate_output_files"]["panel"]
    write_csv(candidate_panel, candidate_rows)

    panel_hash_after = sha256(panel_path)
    if panel_hash_after != panel_hash_before:
        raise RuntimeError("canonical BLS panel mutated during candidate gate")

    audit = {
        "audit_version": "0.1",
        "phase": contract["phase"],
        "status": "PASS_BLS_PANEL_REGENERATION_CANDIDATE_11_OF_12_SINGLE_EXPLICIT_GAP",
        "source_canonical_panel": contract["current_canonical_panel"],
        "source_canonical_panel_sha256": panel_hash_before,
        "source_canonical_audit": contract["current_canonical_audit"],
        "semantic_review": contract["semantic_review"],
        "semantic_review_sha256": sha256(semantic_path),
        "existing_round_count": len(current_rows),
        "added_round_count": len(additions),
        "added_rounds": [row["quarter"] for row in additions],
        "candidate_observed_round_count": len(candidate_rows),
        "candidate_expected_quarter_count_between_bounds": len(expected_grid),
        "candidate_coverage_fraction": len(candidate_rows) / len(expected_grid),
        "candidate_observed_quarters": candidate_quarters,
        "candidate_missing_quarters": missing,
        "reference_date_policy": contract["reference_date_policy"],
        "added_round_identity_audit": identity_audit,
        "existing_rows_preserved_without_replacement": True,
        "canonical_panel_modified": False,
        "canonical_panel_sha256_after": panel_hash_after,
        "interpolation_performed": False,
        "forward_fill_performed": False,
        "synthetic_quarters_created": False,
        "synthetic_reference_dates_created": False,
        "parameter_estimation_performed": False,
        "model_selection_performed": False,
        "holdout_opened": False,
        "system_dynamics_activation": False,
        "behavioural_closure_change": False,
        "hard_rules": contract["hard_rules"],
        "pass_effect": contract["pass_effect"],
    }
    audit_path = OUT / contract["candidate_output_files"]["audit"]
    audit_path.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
