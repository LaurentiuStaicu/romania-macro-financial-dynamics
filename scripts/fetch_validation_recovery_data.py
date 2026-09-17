from __future__ import annotations

import csv
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request
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
        "content_type": headers.get("Content-Type"),
        "etag": headers.get("ETag"),
        "last_modified": headers.get("Last-Modified"),
        "path": str(path),
    }


def normalize_ecb_csv(source_path: Path, destination: Path, series_label: str) -> int:
    text = source_path.read_text(encoding="utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    out_rows = []
    for row in rows:
        period = row.get("TIME_PERIOD") or row.get("TIME_PERIOD_START")
        value = row.get("OBS_VALUE")
        if not period or value in (None, ""):
            continue
        try:
            numeric = float(value)
        except ValueError:
            continue
        out_rows.append((period[:7], numeric, series_label))
    out_rows.sort()
    with destination.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["period", "value_pct", "series"])
        writer.writerows(out_rows)
    return len(out_rows)


def main() -> None:
    attempts: list[dict[str, object]] = []
    ecb_queries = {
        "ecb_nfc_new_business_ron": "https://data-api.ecb.europa.eu/service/data/MIR/M.RO.B.A2A.A.R.A.2240.RON.N?startPeriod=2005-01&format=csvdata",
        "ecb_household_housing_new_business_ron": "https://data-api.ecb.europa.eu/service/data/MIR/M.RO.B.A2C.A.R.A.2250.RON.N?startPeriod=2005-01&format=csvdata",
    }
    for name, url in ecb_queries.items():
        attempts.append(save_attempt(name, url, accept="text/csv"))

    # BIS v1 and v2 are both tried so the retrieval remains robust across API transitions.
    bis_candidates = [
        (
            "bis_policy_rate_v1_csv",
            "https://stats.bis.org/api/v1/data/WS_CBPOL/M.RO/all?startPeriod=2005-01",
            "text/csv",
        ),
        (
            "bis_policy_rate_v1_xml",
            "https://stats.bis.org/api/v1/data/WS_CBPOL/M.RO/all?startPeriod=2005-01",
            "application/vnd.sdmx.genericdata+xml;version=2.1",
        ),
        (
            "bis_policy_rate_v2_csv",
            "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.RO?startPeriod=2005-01",
            "text/csv",
        ),
    ]
    for name, url, accept in bis_candidates:
        attempts.append(save_attempt(name, url, accept=accept))

    normalized = {}
    for name, label in (
        ("ecb_nfc_new_business_ron", "nfc_new_lending_rate_pct"),
        ("ecb_household_housing_new_business_ron", "household_housing_new_lending_rate_pct"),
    ):
        candidate = OUT / f"{name}.csv"
        if candidate.exists():
            normalized[name] = normalize_ecb_csv(
                candidate, OUT / f"normalized_{name}.csv", label
            )

    manifest = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Alpha 0.5.x validation recovery: official-source vintage capture before model re-estimation",
        "attempts": attempts,
        "normalized_observation_counts": normalized,
        "holdout_rule": "No fetched observation is assigned to calibration/selection/evaluation until a split manifest is committed prospectively after coverage inspection and before estimation.",
    }
    (OUT / "fetch_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
