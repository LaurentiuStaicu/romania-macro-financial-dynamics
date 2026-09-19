from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(
    os.environ.get(
        "CORPORATE_INVESTMENT_MEASUREMENT_OUT",
        "corporate_investment_measurement_artifacts",
    )
)
CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "corporate_investment_measurement_panel_contract.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quarter_index(period: str) -> int:
    year_raw, quarter_raw = period.split("-Q")
    year = int(year_raw)
    quarter = int(quarter_raw)
    if quarter not in (1, 2, 3, 4):
        raise ValueError(f"invalid quarter: {period}")
    return year * 4 + quarter - 1


def quarter_from_month(period: str) -> str:
    year_raw, month_raw = period.split("-")
    year = int(year_raw)
    month = int(month_raw)
    if month < 1 or month > 12:
        raise ValueError(f"invalid month: {period}")
    return f"{year:04d}-Q{(month - 1) // 3 + 1}"


def load_level_csv(path: Path) -> dict[str, float]:
    values: dict[str, float] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not {"period", "value"}.issubset(set(reader.fieldnames or [])):
            raise ValueError(f"missing period/value columns: {path}")
        for row in reader:
            period = row["period"].strip()
            value = float(row["value"])
            if not period or not math.isfinite(value):
                raise ValueError(f"invalid observation in {path}: {row}")
            if period in values:
                raise ValueError(f"duplicate period in {path}: {period}")
            values[period] = value
    if not values:
        raise ValueError(f"empty source: {path}")
    return values


def load_ecb_raw_monthly_csv(path: Path, *, expected_key: str) -> dict[str, float]:
    values: dict[str, float] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"TIME_PERIOD", "OBS_VALUE"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError(f"missing ECB raw columns: {path}")
        for row in reader:
            key = (row.get("KEY") or "").strip()
            if key and key != expected_key:
                raise ValueError(f"provider KEY mismatch in {path}: {key}")
            period = (row.get("TIME_PERIOD") or "").strip()
            raw = row.get("OBS_VALUE")
            if not period or raw in (None, ""):
                continue
            value = float(raw)
            if not math.isfinite(value):
                raise ValueError(f"non-finite observation in {path}: {period}")
            if period in values:
                raise ValueError(f"duplicate period in {path}: {period}")
            values[period] = value
    if not values:
        raise ValueError(f"empty retained ECB raw source: {path}")
    return values


def lag_quarter(period: str, quarters: int) -> str:
    idx = quarter_index(period) - quarters
    year, q0 = divmod(idx, 4)
    return f"{year:04d}-Q{q0 + 1}"


def trailing_four_sum(values: dict[str, float], period: str) -> float | None:
    required = [lag_quarter(period, lag) for lag in (3, 2, 1, 0)]
    if any(p not in values for p in required):
        return None
    if any(
        quarter_index(b) - quarter_index(a) != 1
        for a, b in zip(required, required[1:])
    ):
        raise AssertionError("internal non-consecutive quarter sequence")
    return sum(values[p] for p in required)


def derive_real_gdp_yoy(real_gdp: dict[str, float]) -> dict[str, float]:
    out: dict[str, float] = {}
    for period, value in real_gdp.items():
        previous = lag_quarter(period, 4)
        if previous not in real_gdp:
            continue
        base = real_gdp[previous]
        if base <= 0:
            raise ValueError(f"non-positive GDP base at {previous}")
        out[period] = 100.0 * (value / base - 1.0)
    return out


def derive_support_intensity(
    grants: dict[str, float],
    gva: dict[str, float],
) -> dict[str, float]:
    out: dict[str, float] = {}
    periods = sorted(set(grants) & set(gva), key=quarter_index)
    for period in periods:
        grants_sum = trailing_four_sum(grants, period)
        gva_sum = trailing_four_sum(gva, period)
        if grants_sum is None or gva_sum is None:
            continue
        if gva_sum <= 0:
            raise ValueError(f"non-positive trailing-four-quarter GVA at {period}")
        out[period] = 100.0 * grants_sum / gva_sum
    return out


def derive_quarterly_rate(monthly: dict[str, float]) -> dict[str, float]:
    grouped: dict[str, dict[int, float]] = defaultdict(dict)
    for period, value in monthly.items():
        year_raw, month_raw = period.split("-")
        month = int(month_raw)
        quarter = quarter_from_month(period)
        if month in grouped[quarter]:
            raise ValueError(f"duplicate month in quarter {quarter}: {period}")
        grouped[quarter][month] = value

    out: dict[str, float] = {}
    for quarter, months in grouped.items():
        q = int(quarter[-1])
        expected = set(range((q - 1) * 3 + 1, (q - 1) * 3 + 4))
        if set(months) != expected:
            continue
        out[quarter] = sum(months[m] for m in sorted(expected)) / 3.0
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    core = ROOT / contract["retained_source_vintages"]["core"]
    supplemental = ROOT / contract["retained_source_vintages"]["supplemental"]
    rate_screening = (
        ROOT / contract["retained_source_vintages"]["financing_rate_screening"]
    )

    paths = {
        "target": core / contract["inputs"]["target"],
        "grants": core / contract["inputs"]["grants"],
        "lending_rate_raw": rate_screening / contract["inputs"]["lending_rate_raw"],
        "nfc_gva": supplemental / contract["inputs"]["nfc_gva"],
        "real_gdp": supplemental / contract["inputs"]["real_gdp"],
    }
    for name, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"missing retained source {name}: {path}")

    target = load_level_csv(paths["target"])
    grants = load_level_csv(paths["grants"])
    monthly_rate = load_ecb_raw_monthly_csv(
        paths["lending_rate_raw"],
        expected_key=contract["inputs"]["lending_rate_series_key"],
    )
    gva = load_level_csv(paths["nfc_gva"])
    real_gdp = load_level_csv(paths["real_gdp"])

    gdp_yoy = derive_real_gdp_yoy(real_gdp)
    support = derive_support_intensity(grants, gva)
    rate_q = derive_quarterly_rate(monthly_rate)

    complete = sorted(
        set(target) & set(gdp_yoy) & set(support) & set(rate_q),
        key=quarter_index,
    )
    if not complete:
        raise RuntimeError("no complete aligned measurement quarters")

    panel_path = OUT / contract["output_files"]["panel"]
    fields = contract["panel_columns"]
    with panel_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for period in complete:
            writer.writerow(
                {
                    "period": period,
                    "nfc_investment_rate": f"{target[period]:.12g}",
                    "real_gdp_yoy_growth": f"{gdp_yoy[period]:.12g}",
                    "investment_grants_support_intensity": f"{support[period]:.12g}",
                    "nfc_new_business_lending_rate_up_to_one_year_quarterly_mean": f"{rate_q[period]:.12g}",
                }
            )

    source_hashes = {
        name: sha256(path)
        for name, path in paths.items()
    }
    expected_indices = list(
        range(quarter_index(complete[0]), quarter_index(complete[-1]) + 1)
    )
    actual_indices = [quarter_index(period) for period in complete]
    panel_contiguous = actual_indices == expected_indices
    if not panel_contiguous:
        raise RuntimeError(
            "aligned measurement panel is not quarterly contiguous over common window"
        )

    audit = {
        "audit_version": "0.1",
        "mechanism_id": contract["mechanism_id"],
        "phase": contract["phase"],
        "status": "PASS_OFFLINE_MEASUREMENT_PANEL_READY_FOR_STRUCTURAL_SELECTION_DESIGN",
        "input_files": {
            name: str(path.relative_to(ROOT))
            for name, path in paths.items()
        },
        "input_sha256": source_hashes,
        "derived_series_coverage": {
            "target": {
                "rows": len(target),
                "first_period": min(target, key=quarter_index),
                "last_period": max(target, key=quarter_index),
            },
            "real_gdp_yoy_growth": {
                "rows": len(gdp_yoy),
                "first_period": min(gdp_yoy, key=quarter_index),
                "last_period": max(gdp_yoy, key=quarter_index),
            },
            "investment_grants_support_intensity": {
                "rows": len(support),
                "first_period": min(support, key=quarter_index),
                "last_period": max(support, key=quarter_index),
            },
            "nfc_new_business_lending_rate_up_to_one_year_quarterly_mean": {
                "rows": len(rate_q),
                "first_period": min(rate_q, key=quarter_index),
                "last_period": max(rate_q, key=quarter_index),
            },
        },
        "complete_panel": {
            "rows": len(complete),
            "first_period": complete[0],
            "last_period": complete[-1],
            "periods": complete,
            "sha256": sha256(panel_path),
            "quarterly_contiguous": panel_contiguous,
        },
        "transformations": contract["transformations"],
        "hard_rules": contract["hard_rules"],
        "parameter_estimation_performed": False,
        "model_selection_performed": False,
        "lag_selection_performed": False,
        "holdout_opened": False,
        "causal_claim": False,
        "system_dynamics_activation": False,
        "behavioural_closure_change": False,
    }
    audit_path = OUT / contract["output_files"]["audit"]
    audit_path.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
