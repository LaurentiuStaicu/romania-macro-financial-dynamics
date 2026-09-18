from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(os.environ.get("F2_PROBE_OUT", "f2_probe_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+GitHub F2 source-structure audit)"

INSTRUMENTS = ("F2", "F21", "F2M", "F22", "F29")
MEASURES = ("LE", "F")


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def key(
    *,
    counterpart_area: str,
    reference_sector: str,
    counterpart_sector: str,
    entry: str,
    measure: str,
    instrument: str,
) -> str:
    return ".".join(
        (
            "Q",
            "N",
            "RO",
            counterpart_area,
            reference_sector,
            counterpart_sector,
            "N",
            entry,
            measure,
            instrument,
            "T",
            "_Z",
            "XDC",
            "_T",
            "S",
            "V",
            "N",
            "_T",
        )
    )


def fetch(series_key: str) -> dict[str, object]:
    query = urllib.parse.urlencode(
        {
            "startPeriod": "2025-Q1",
            "endPeriod": "2025-Q4",
            "format": "csvdata",
        }
    )
    url = f"{API}{series_key}?{query}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/csv"},
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = response.read()
            status = int(response.status)
            headers = dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        body = exc.read()
        status = int(exc.code)
        headers = dict(exc.headers.items())
    except urllib.error.URLError as exc:
        return {
            "key": series_key,
            "url": url,
            "status": "NETWORK_ERROR",
            "error": str(exc),
            "rows": [],
        }

    raw_name = f"{sha256(series_key.encode('utf-8'))[:16]}.raw"
    raw_path = OUT / "raw" / raw_name
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(body)

    result: dict[str, object] = {
        "key": series_key,
        "url": url,
        "http_status": status,
        "raw_path": str(raw_path.relative_to(OUT)),
        "raw_bytes": len(body),
        "raw_sha256": sha256(body),
        "content_type": headers.get("Content-Type"),
        "last_modified": headers.get("Last-Modified"),
        "etag": headers.get("ETag"),
        "rows": [],
    }

    if status != 200:
        result["status"] = "HTTP_ERROR"
        return result

    rows = list(csv.DictReader(io.StringIO(body.decode("utf-8-sig"))))
    parsed = []
    for row in rows:
        period = row.get("TIME_PERIOD")
        value = row.get("OBS_VALUE")
        if not period or value in (None, ""):
            continue
        try:
            numeric = float(value)
        except ValueError:
            continue
        parsed.append(
            {
                "period": period,
                "value": numeric,
                "instrument": row.get("INSTR_ASSET"),
                "reference_sector": row.get("REF_SECTOR"),
                "counterpart_sector": row.get("COUNTERPART_SECTOR"),
                "counterpart_area": row.get("COUNTERPART_AREA"),
                "entry": row.get("ACCOUNTING_ENTRY"),
                "measure": row.get("STO"),
                "maturity": row.get("MATURITY"),
                "unit": row.get("UNIT_MEASURE") or row.get("UNIT"),
                "unit_mult": row.get("UNIT_MULT"),
                "decimals": row.get("DECIMALS"),
                "obs_status": row.get("OBS_STATUS"),
            }
        )

    result["rows"] = parsed
    result["status"] = "AVAILABLE" if parsed else "NO_OBSERVATIONS"
    return result


def add_family(
    specs: dict[str, dict[str, str]],
    name: str,
    *,
    counterpart_area: str,
    reference_sector: str,
    counterpart_sector: str,
    entry: str,
) -> None:
    specs[name] = {
        "counterpart_area": counterpart_area,
        "reference_sector": reference_sector,
        "counterpart_sector": counterpart_sector,
        "entry": entry,
    }


def main() -> None:
    specs: dict[str, dict[str, str]] = {}

    # Published W0 controls for representative RMD sectors and financial aggregates.
    for sector in ("S1M", "S11", "S13", "S12", "S121"):
        for entry in ("A", "L"):
            add_family(
                specs,
                f"W0_{sector}_{entry}",
                counterpart_area="W0",
                reference_sector=sector,
                counterpart_sector="S1",
                entry=entry,
            )

    # Domestic who-to-whom structures that distinguish currency issuer,
    # broad financial sector and MFI-specific deposit counterpart publication.
    domestic_pairs = (
        ("H_to_BNR", "S1M", "S121"),
        ("H_to_S12", "S1M", "S12"),
        ("H_to_S12T", "S1M", "S12T"),
        ("C_to_BNR", "S11", "S121"),
        ("C_to_S12", "S11", "S12"),
        ("C_to_S12T", "S11", "S12T"),
        ("G_to_BNR", "S13", "S121"),
        ("G_to_S12", "S13", "S12"),
        ("G_to_S12T", "S13", "S12T"),
        ("BNR_to_S12", "S121", "S12"),
        ("S12_to_BNR", "S12", "S121"),
        ("S12_to_S12", "S12", "S12"),
    )
    for name, reference_sector, counterpart_sector in domestic_pairs:
        add_family(
            specs,
            name,
            counterpart_area="W2",
            reference_sector=reference_sector,
            counterpart_sector=counterpart_sector,
            entry="A",
        )

    # Deposit who-to-whom data are often published from the issuer liability side.
    # Probe broad financial corporations, MFI aggregates, MFIs excluding the
    # central bank, the central bank itself, and government as potential issuers.
    liability_issuer_pairs = (
        ("S12K_from_H", "S12K", "S1M"),
        ("S12K_from_C", "S12K", "S11"),
        ("S12K_from_G", "S12K", "S13"),
        ("S12T_from_H", "S12T", "S1M"),
        ("S12T_from_C", "S12T", "S11"),
        ("S12T_from_G", "S12T", "S13"),
        ("S12T_from_BNR", "S12T", "S121"),
        ("S12_from_H", "S12", "S1M"),
        ("S12_from_C", "S12", "S11"),
        ("S12_from_G", "S12", "S13"),
        ("S12_from_BNR", "S12", "S121"),
        ("BNR_from_H", "S121", "S1M"),
        ("BNR_from_C", "S121", "S11"),
        ("BNR_from_G", "S121", "S13"),
        ("BNR_from_S12", "S121", "S12"),
        ("G_from_H", "S13", "S1M"),
        ("G_from_C", "S13", "S11"),
        ("G_from_S12", "S13", "S12"),
    )
    for name, issuer_sector, holder_sector in liability_issuer_pairs:
        add_family(
            specs,
            name,
            counterpart_area="W2",
            reference_sector=issuer_sector,
            counterpart_sector=holder_sector,
            entry="L",
        )

    # Rest-of-world boundary examples on both asset and liability sides.
    external = (
        ("H_assets_X", "S1M", "A"),
        ("C_assets_X", "S11", "A"),
        ("G_assets_X", "S13", "A"),
        ("S12_assets_X", "S12", "A"),
        ("BNR_assets_X", "S121", "A"),
        ("X_assets_H", "S1M", "L"),
        ("X_assets_C", "S11", "L"),
        ("X_assets_G", "S13", "L"),
        ("X_assets_S12", "S12", "L"),
        ("X_assets_BNR", "S121", "L"),
    )
    for name, reference_sector, entry in external:
        add_family(
            specs,
            name,
            counterpart_area="W1",
            reference_sector=reference_sector,
            counterpart_sector="S1",
            entry=entry,
        )

    requests = []
    for family, spec in specs.items():
        for measure in MEASURES:
            for instrument in INSTRUMENTS:
                requests.append(
                    {
                        "family": family,
                        "measure": measure,
                        "instrument": instrument,
                        "key": key(
                            counterpart_area=spec["counterpart_area"],
                            reference_sector=spec["reference_sector"],
                            counterpart_sector=spec["counterpart_sector"],
                            entry=spec["entry"],
                            measure=measure,
                            instrument=instrument,
                        ),
                    }
                )

    results = []
    for index, request in enumerate(requests, start=1):
        print(
            f"[{index}/{len(requests)}] {request['family']} "
            f"{request['measure']} {request['instrument']}",
            flush=True,
        )
        result = fetch(request["key"])
        results.append({**request, **result})

    availability: dict[str, dict[str, int]] = {}
    for item in results:
        family = str(item["family"])
        status = str(item["status"])
        availability.setdefault(family, {})
        availability[family][status] = (
            availability[family].get(status, 0) + 1
        )

    exact_identity_tests = []
    grouped = {
        (family, measure): {
            item["instrument"]: item
            for item in results
            if item["family"] == family and item["measure"] == measure
        }
        for family in specs
        for measure in MEASURES
    }

    def period_map(item: dict[str, object]) -> dict[str, float]:
        return {
            str(row["period"]): float(row["value"])
            for row in item.get("rows", [])
        }

    for (family, measure), items in grouped.items():
        direct = items["F2"]
        f21 = items["F21"]
        f2m = items["F2M"]
        f22 = items["F22"]
        f29 = items["F29"]

        for route_name, components in (
            ("F21_PLUS_F2M", (f21, f2m)),
            ("F21_PLUS_F22_PLUS_F29", (f21, f22, f29)),
        ):
            direct_map = period_map(direct)
            component_maps = [period_map(component) for component in components]
            periods = sorted(direct_map)
            comparable = bool(
                direct.get("status") == "AVAILABLE"
                and all(component.get("status") == "AVAILABLE" for component in components)
                and periods
                and all(sorted(component_map) == periods for component_map in component_maps)
            )
            residuals = {}
            if comparable:
                for period in periods:
                    reconstructed = sum(
                        component_map[period]
                        for component_map in component_maps
                    )
                    residuals[period] = direct_map[period] - reconstructed
            exact_identity_tests.append(
                {
                    "family": family,
                    "measure": measure,
                    "route": route_name,
                    "direct_F2_status": direct.get("status"),
                    "component_statuses": [
                        component.get("status") for component in components
                    ],
                    "comparable": comparable,
                    "residuals": residuals,
                    "max_abs_residual": (
                        max(abs(value) for value in residuals.values())
                        if residuals else None
                    ),
                }
            )

    report = {
        "probe_version": "0.1",
        "purpose": "Non-mutating ECB QSA publication-structure probe for RMD F2.",
        "instruments_tested": list(INSTRUMENTS),
        "measures_tested": list(MEASURES),
        "families_tested": list(specs),
        "requests": len(requests),
        "availability_by_family": availability,
        "identity_tests": exact_identity_tests,
        "results": results,
    }
    (OUT / "f2_structure_probe.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "requests": len(requests),
                "status_counts": {
                    status: sum(
                        1 for item in results if item["status"] == status
                    )
                    for status in sorted({str(item["status"]) for item in results})
                },
                "available_by_instrument": {
                    instrument: sum(
                        1
                        for item in results
                        if item["instrument"] == instrument
                        and item["status"] == "AVAILABLE"
                    )
                    for instrument in INSTRUMENTS
                },
                "exact_identity_comparisons": sum(
                    1
                    for item in exact_identity_tests
                    if item["comparable"]
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
