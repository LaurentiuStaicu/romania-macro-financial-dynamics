from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


def read_rows(path: Path) -> list[tuple[str, str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = []
        for row in csv.DictReader(handle):
            rows.append(
                (
                    row["period"].strip(),
                    row["value_pct"].strip(),
                    row["series"].strip(),
                )
            )
    return rows


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: compare_live_normalized_to_retained.py "
            "LIVE_DIR RETAINED_DIR OUTPUT_JSON"
        )

    live = Path(sys.argv[1])
    retained = Path(sys.argv[2])
    output = Path(sys.argv[3])

    mapping = {
        "ecb_household_housing_new_business_ron": (
            live / "normalized_ecb_household_housing_new_business_ron.csv",
            retained / "household_housing_mir_monthly.csv",
        ),
        "ecb_nfc_new_business_upto1y_ron": (
            live / "normalized_ecb_nfc_new_business_upto1y_ron.csv",
            retained / "nfc_upto1y_mir_monthly.csv",
        ),
        "ecb_nfc_new_business_total_ron": (
            live / "normalized_ecb_nfc_new_business_total_ron.csv",
            retained / "nfc_total_mir_available_observations.csv",
        ),
        "bis_policy_rate": (
            live / "normalized_bis_policy_rate.csv",
            retained / "policy_rate_bis_monthly.csv",
        ),
    }

    comparisons = []
    all_match = True
    for name, (live_path, retained_path) in mapping.items():
        live_rows = read_rows(live_path)
        retained_rows = read_rows(retained_path)
        same = live_rows == retained_rows
        all_match = all_match and same
        first_difference = None
        if not same:
            limit = max(len(live_rows), len(retained_rows))
            for index in range(limit):
                left = live_rows[index] if index < len(live_rows) else None
                right = retained_rows[index] if index < len(retained_rows) else None
                if left != right:
                    first_difference = {
                        "row_index": index,
                        "live": left,
                        "retained": right,
                    }
                    break
        comparisons.append(
            {
                "name": name,
                "live_rows": len(live_rows),
                "retained_rows": len(retained_rows),
                "semantic_rows_match": same,
                "first_difference": first_difference,
            }
        )

    result = {
        "all_normalized_statistical_inputs_match": all_match,
        "comparisons": comparisons,
        "interpretation": (
            "This compares the statistical rows actually used by the model. "
            "It does not replace raw-byte provenance; it distinguishes a changed "
            "transport envelope from a changed normalized statistical series."
        ),
    }
    output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
