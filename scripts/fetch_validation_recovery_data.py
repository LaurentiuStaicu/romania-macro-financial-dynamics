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

USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+GitHub reproducible research fetch)"
FETCHER_VERSION = "0.2"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def save_attempt(
    name: str,
    institution: str,
    url: str,
    *,
    accept: str | None = None,
    suffix: str,
) -> dict[str, object]:
    status, body, headers = fetch(url, accept=accept)
    path = OUT / f"{name}{suffix}"
    path.write_bytes(body)
    return {
        "name": name,
        "institution": institution,
        "url": url,
        "accept": accept,
        "status": status,
        "bytes": len(body),
        "sha256": sha256_bytes(body),
        "content_type": headers.get("Content-Type"),
        "etag": headers.get("ETag"),
        "last_modified": headers.get("Last-Modified"),
        "path": path.name,
    }


def normalized_metadata(
    destination: Path,
    *,
    source_sha256: str,
    normalizer: str,
    statistics: dict[str, object],
) -> dict[str, object]:
    return {
        **statistics,
        "path": destination.name,
        "sha256": sha256_file(destination),
        "derived_from_raw_sha256": source_sha256,
        "normalizer": normalizer,
    }


def normalize_ecb_csv(
    source_path: Path,
    destination: Path,
    series_label: str,
    *,
    source_sha256: str,
) -> dict[str, object]:
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
    return normalized_metadata(
        destination,
        source_sha256=source_sha256,
        normalizer="normalize_ecb_csv",
        statistics={
            "observations": len(out_rows),
            "first_period": out_rows[0][0] if out_rows else None,
            "last_period": out_rows[-1][0] if out_rows else None,
            "source_rows_with_missing_value": sorted(set(missing_periods)),
        },
    )


def normalize_bis_policy_xml(
    source_path: Path,
    destination: Path,
    *,
    source_sha256: str,
) -> dict[str, object]:
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
    return normalized_metadata(
        destination,
        source_sha256=source_sha256,
        normalizer="normalize_bis_policy_xml",
        statistics={
            "observations": len(rows),
            "first_period": rows[0][0] if rows else None,
            "last_period": rows[-1][0] if rows else None,
            "source_ref": source_ref,
            "compilation": compilation,
        },
    )


def main() -> None:
    fetched_at = datetime.now(timezone.utc)
    snapshot_id = os.environ.get(
        "RECOVERY_SNAPSHOT_ID",
        fetched_at.strftime("validation-recovery-%Y%m%dT%H%M%SZ"),
    )

    source_specs = [
        {
            "name": "ecb_nfc_new_business_total_ron",
            "institution": "European Central Bank / ESCB",
            "url": "https://data-api.ecb.europa.eu/service/data/MIR/M.RO.B.A2A.A.R.A.2240.RON.N?startPeriod=2005-01&format=csvdata",
            "accept": "text/csv",
            "suffix": ".csv",
        },
        {
            "name": "ecb_nfc_new_business_upto1y_ron",
            "institution": "European Central Bank / ESCB",
            "url": "https://data-api.ecb.europa.eu/service/data/MIR/M.RO.B.A2A.F.R.A.2240.RON.N?startPeriod=2005-01&format=csvdata",
            "accept": "text/csv",
            "suffix": ".csv",
        },
        {
            "name": "ecb_household_housing_new_business_ron",
            "institution": "European Central Bank / ESCB",
            "url": "https://data-api.ecb.europa.eu/service/data/MIR/M.RO.B.A2C.A.R.A.2250.RON.N?startPeriod=2005-01&format=csvdata",
            "accept": "text/csv",
            "suffix": ".csv",
        },
        {
            "name": "bis_policy_rate_xml",
            "institution": "Bank for International Settlements / National Bank of Romania",
            "url": "https://stats.bis.org/api/v1/data/WS_CBPOL/M.RO/all?startPeriod=2005-01",
            "accept": "application/vnd.sdmx.structurespecificdata+xml;version=2.1",
            "suffix": ".xml",
        },
    ]

    attempts = [
        save_attempt(
            spec["name"],
            spec["institution"],
            spec["url"],
            accept=spec["accept"],
            suffix=spec["suffix"],
        )
        for spec in source_specs
    ]
    attempts_by_name = {attempt["name"]: attempt for attempt in attempts}

    normalized: dict[str, object] = {}
    for name, label in (
        ("ecb_nfc_new_business_total_ron", "nfc_new_lending_rate_total_pct"),
        ("ecb_nfc_new_business_upto1y_ron", "nfc_new_lending_rate_upto1y_pct"),
        ("ecb_household_housing_new_business_ron", "household_housing_new_lending_rate_pct"),
    ):
        attempt = attempts_by_name[name]
        candidate = OUT / str(attempt["path"])
        destination = OUT / f"normalized_{name}.csv"
        normalized[name] = normalize_ecb_csv(
            candidate,
            destination,
            label,
            source_sha256=str(attempt["sha256"]),
        )

    bis_attempt = attempts_by_name["bis_policy_rate_xml"]
    bis_candidate = OUT / str(bis_attempt["path"])
    destination = OUT / "normalized_bis_policy_rate.csv"
    normalized["bis_policy_rate"] = normalize_bis_policy_xml(
        bis_candidate,
        destination,
        source_sha256=str(bis_attempt["sha256"]),
    )

    fetcher_path = Path(__file__).resolve()
    manifest = {
        "manifest_version": "0.2",
        "snapshot_id": snapshot_id,
        "fetched_at_utc": fetched_at.isoformat(),
        "purpose": "Immutable official-source vintage capture for validation-recovery provenance",
        "fetcher_version": FETCHER_VERSION,
        "fetcher_script": "scripts/fetch_validation_recovery_data.py",
        "fetcher_script_sha256": sha256_file(fetcher_path),
        "attempts": attempts,
        "normalized_series": normalized,
        "source_reuse": {
            "ECB": "https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html",
            "BIS": "https://data.bis.org/help/legal",
        },
        "holdout_rule": "Coverage may be inspected before the split is frozen, but model estimation/selection must not begin until a prospective split manifest is committed. Previously inspected observations remain permanently ineligible for later independent validation.",
        "archival_rule": "Retain this manifest, every raw path and every normalized path together. Reproduction must use retained raw bytes; a later live refetch is a new vintage unless its raw SHA-256 matches exactly.",
    }
    (OUT / "snapshot_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
