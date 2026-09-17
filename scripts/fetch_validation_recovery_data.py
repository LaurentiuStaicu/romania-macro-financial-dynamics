from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(os.environ.get("RECOVERY_OUT", "recovery_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)

USER_AGENT = "romania-macro-financial-dynamics/0.5.1a0 (+GitHub Actions reproducible research fetch)"


def fetch(url: str, *, accept: str | None = None) -> tuple[int, bytes, dict[str, str]]:
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, response.read(), dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers.items())


def save_attempt(name: str, url: str, *, accept: str | None = None) -> dict[str, object]:
    status, body, headers = fetch(url, accept=accept)
    suffix = ".csv" if b"," in body[:500] and b"TIME_PERIOD" in body[:5000] else ".bin"
    path = OUT / f"{name}{suffix}"
    path.write_bytes(body)
    return {
        "name": name,
        "url": url,
        "accept": accept,
        "status": status,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "content_type": headers.get("Content-Type"),
        "etag": headers.get("ETag"),
        "last_modified": headers.get("Last-Modified"),
        "path": str(path),
    }


def normalize_ecb_csv(source_path: Path, destination: Path, series_label: str) -> dict[str, object]:
    text = source_path.read_text(encoding="utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    out_rows = []
    missing_periods = []
    for row in rows:
        period = row.get("TIME_PERIOD") or row.get("TIME_PERIOD_START")
        value = row.get("OBS_VALUE")
        if not period:
            continue
        if value in (None, ""):
            missing_periods.append(period[:7])
            continue
        try:
            numeric = float(value)
        except ValueError:
            missing_periods.append(period[:7])
            continue
        out_rows.append((period[:7], numeric, series_label))
    out_rows.sort()
    with destination.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["period", "value_pct", "series"])
        writer.writerows(out_rows)
    return {
        "observations": len(out_rows),
        "first_period": out_rows[0][0] if out_rows else None,
        "last_period": out_rows[-1][0] if out_rows else None,
        "source_rows_with_missing_value": sorted(set(missing_periods)),
    }


def normalize_bis_policy_xml(source_path: Path, destination: Path) -> dict[str, object]:
    root = ET.fromstring(source_path.read_bytes())
    rows: list[tuple[str, float, str]] = []
    source_ref = None
    compilation = None
    for element in root.iter():
        if element.tag.endswith("Series"):
            source_ref = element.attrib.get("SOURCE_REF")
            compilation = element.attrib.get("COMPILATION")
        if element.tag.endswith("Obs"):
            period = element.attrib.get("TIME_PERIOD")
            value = element.attrib.get("OBS_VALUE")
            if period and value not in (None, ""):
                rows.append((period[:7], float(value), "policy_rate_pct"))
    rows.sort()
    with destination.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["period", "value_pct", "series"])
        writer.writerows(rows)
    return {
        "observations": len(rows),
        "first_period": rows[0][0] if rows else None,
        "last_period": rows[-1][0] if rows else None,
        "source_ref": source_ref,
        "compilation": compilation,
    }


def main() -> None:
    attempts: list[dict[str, object]] = []
    ecb_queries = {
        "ecb_nfc_new_business_total_ron": "https://data-api.ecb.europa.eu/service/data/MIR/M.RO.B.A2A.A.R.A.2240.RON.N?startPeriod=2005-01&format=csvdata",
        "ecb_nfc_new_business_upto1y_ron": "https://data-api.ecb.europa.eu/service/data/MIR/M.RO.B.A2A.F.R.A.2240.RON.N?startPeriod=2005-01&format=csvdata",
        "ecb_household_housing_new_business_ron": "https://data-api.ecb.europa.eu/service/data/MIR/M.RO.B.A2C.A.R.A.2250.RON.N?startPeriod=2005-01&format=csvdata",
    }
    for name, url in ecb_queries.items():
        attempts.append(save_attempt(name, url, accept="text/csv"))

    # BIS is the policy-rate source because it provides a long monthly series for
    # Romania sourced directly from the National Bank of Romania. The XML query
    # is retained as the canonical recovery representation.
    bis_url = "https://stats.bis.org/api/v1/data/WS_CBPOL/M.RO/all?startPeriod=2005-01"
    attempts.append(
        save_attempt(
            "bis_policy_rate_xml",
            bis_url,
            accept="application/vnd.sdmx.structurespecificdata+xml;version=2.1",
        )
    )

    normalized: dict[str, object] = {}
    for name, label in (
        ("ecb_nfc_new_business_total_ron", "nfc_new_lending_rate_total_pct"),
        ("ecb_nfc_new_business_upto1y_ron", "nfc_new_lending_rate_upto1y_pct"),
        ("ecb_household_housing_new_business_ron", "household_housing_new_lending_rate_pct"),
    ):
        candidate = OUT / f"{name}.csv"
        if candidate.exists():
            normalized[name] = normalize_ecb_csv(
                candidate, OUT / f"normalized_{name}.csv", label
            )

    bis_candidate = OUT / "bis_policy_rate_xml.bin"
    if bis_candidate.exists():
        normalized["bis_policy_rate"] = normalize_bis_policy_xml(
            bis_candidate, OUT / "normalized_bis_policy_rate.csv"
        )

    manifest = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Alpha 0.5.x validation recovery: official-source vintage capture before model re-estimation",
        "attempts": attempts,
        "normalized_series": normalized,
        "holdout_rule": "Coverage may be inspected before the split is frozen, but model estimation/selection must not begin until a prospective split manifest is committed. Previously inspected Nov-2024–Jan-2025 observations are permanently ineligible for independent evaluation.",
    }
    (OUT / "fetch_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
