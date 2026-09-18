from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("EUROSTAT_F2_AUDIT_OUT", "eurostat_f2_audit_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)

API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/bop_iip6_q"
USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+GitHub Eurostat F2 sector audit)"
SECTORS = ("S1", "S121", "S12T", "S13", "S1P", "S12M", "S1V", "S11", "S1M")
CURRENCIES = ("MIO_EUR", "MIO_NAC")
PERIOD = "2025-Q4"
TOL = 0.1


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def request_url(sector: str, currency: str) -> str:
    query = urllib.parse.urlencode(
        {
            "lang": "en",
            "freq": "Q",
            "currency": currency,
            "bop_item": "FA__O__F2",
            "sector10": sector,
            "sectpart": "S1",
            "stk_flow": "A_LE",
            "partner": "WRL_REST",
            "geo": "RO",
            "sinceTimePeriod": PERIOD,
            "untilTimePeriod": PERIOD,
        }
    )
    return f"{API}?{query}"


def fetch(sector: str, currency: str) -> dict[str, object]:
    url = request_url(sector, currency)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
                status = int(response.status)
                headers = dict(response.headers.items())
            break
        except urllib.error.HTTPError as exc:
            body = exc.read()
            status = int(exc.code)
            headers = dict(exc.headers.items())
            break
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == 3:
                return {
                    "sector": sector,
                    "currency": currency,
                    "url": url,
                    "status": "NETWORK_ERROR",
                    "error": str(last_error),
                    "attempts": attempt,
                    "value": None,
                }
    else:
        raise AssertionError("unreachable retry state")

    raw_name = hashlib.sha256(f"{sector}|{currency}".encode()).hexdigest()[:16] + ".json"
    raw_path = OUT / "raw" / raw_name
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(body)

    result: dict[str, object] = {
        "sector": sector,
        "currency": currency,
        "url": url,
        "http_status": status,
        "raw_path": str(raw_path.relative_to(OUT)),
        "raw_sha256": sha256(body),
        "raw_bytes": len(body),
        "content_type": headers.get("Content-Type"),
        "value": None,
    }
    if status != 200:
        result["status"] = "HTTP_ERROR"
        result["response_preview"] = body[:500].decode("utf-8", errors="replace")
        return result

    try:
        payload = json.loads(body.decode("utf-8-sig"))
    except Exception as exc:
        result["status"] = "PARSE_ERROR"
        result["error"] = str(exc)
        return result

    if payload.get("class") != "dataset":
        result["status"] = "UNEXPECTED_PAYLOAD"
        result["payload_keys"] = sorted(payload.keys())
        return result

    ids = payload.get("id") or []
    sizes = payload.get("size") or []
    if len(ids) != len(sizes):
        result["status"] = "UNEXPECTED_DIMENSIONS"
        result["ids"] = ids
        result["sizes"] = sizes
        return result

    non_time_sizes = [
        int(size)
        for dim, size in zip(ids, sizes)
        if dim != "time"
    ]
    if any(size != 1 for size in non_time_sizes):
        result["status"] = "UNEXPECTED_MULTI_SERIES_RESPONSE"
        result["ids"] = ids
        result["sizes"] = sizes
        return result

    dimension = payload.get("dimension", {})
    time_dim = dimension.get("time", {})
    index = time_dim.get("category", {}).get("index", {})
    if isinstance(index, list):
        time_codes = list(index)
    else:
        time_codes = [
            code
            for code, _ in sorted(index.items(), key=lambda item: int(item[1]))
        ]
    if PERIOD not in time_codes:
        result["status"] = "NO_OBSERVATION"
        result["available_time_codes"] = time_codes
        return result

    time_pos = time_codes.index(PERIOD)
    values = payload.get("value", {})
    if isinstance(values, list):
        raw_value = values[time_pos] if time_pos < len(values) else None
    else:
        raw_value = values.get(str(time_pos))
        if raw_value is None:
            raw_value = values.get(time_pos)

    if raw_value is None:
        result["status"] = "NO_OBSERVATION"
        return result

    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        result["status"] = "NON_NUMERIC_OBSERVATION"
        result["raw_value"] = raw_value
        return result

    result["status"] = "AVAILABLE"
    result["value"] = value
    result["dataset_updated"] = payload.get("updated")
    result["dataset_label"] = payload.get("label")
    return result


def main() -> None:
    specs = [(sector, currency) for sector in SECTORS for currency in CURRENCIES]
    results = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(fetch, sector, currency): (sector, currency)
            for sector, currency in specs
        }
        for index, future in enumerate(as_completed(futures), start=1):
            spec = futures[future]
            results[spec] = future.result()
            print(f"[{index}/{len(futures)}] {spec}: {results[spec]['status']}", flush=True)

    bps = json.loads(
        (ROOT / "model" / "accounting" / "bps_f2_sector_structure_assessment.json").read_text(
            encoding="utf-8"
        )
    )
    bps_eur = bps["published_structure"]["stock_EUR_million"]
    bps_ron = bps["published_structure"]["stock_RON_million"]
    mapping = {
        "S1": "S1",
        "S121": "S121",
        "S12T": "S12T",
        "S13": "S13",
        "S1P": "S1P",
        "S12M": "S12M",
        "S1V": "S1V",
    }

    cross_source = []
    for sector, key_name in mapping.items():
        for currency, bps_block in (("MIO_EUR", bps_eur), ("MIO_NAC", bps_ron)):
            eurostat = results[(sector, currency)]
            bps_value = bps_block.get(key_name)
            if bps_value is None or eurostat.get("value") is None:
                status = "CONTROL_UNAVAILABLE"
                residual = None
            else:
                residual = float(eurostat["value"]) - float(bps_value)
                status = "PASS" if abs(residual) <= TOL else "VINTAGE_OR_SOURCE_MISMATCH"
            cross_source.append(
                {
                    "sector": sector,
                    "currency": currency,
                    "eurostat_value": eurostat.get("value"),
                    "bps_retained_value": bps_value,
                    "residual": residual,
                    "status": status,
                }
            )

    availability = [
        {
            "sector": sector,
            "currency": currency,
            "status": results[(sector, currency)]["status"],
            "value": results[(sector, currency)].get("value"),
        }
        for sector, currency in specs
    ]

    critical = {}
    for currency in CURRENCIES:
        s11 = results[("S11", currency)]
        s1m = results[("S1M", currency)]
        s1v = results[("S1V", currency)]
        if s11.get("value") is not None and s1m.get("value") is not None:
            split_sum = float(s11["value"]) + float(s1m["value"])
            residual = (
                None
                if s1v.get("value") is None
                else split_sum - float(s1v["value"])
            )
            status = (
                "PASS"
                if residual is not None and abs(residual) <= TOL
                else "SPLIT_AVAILABLE_CONTROL_MISMATCH"
            )
        else:
            split_sum = None
            residual = None
            status = "S11_OR_S1M_UNAVAILABLE"
        critical[currency] = {
            "S11_value": s11.get("value"),
            "S11_status": s11["status"],
            "S1M_value": s1m.get("value"),
            "S1M_status": s1m["status"],
            "S1V_value": s1v.get("value"),
            "S1V_status": s1v["status"],
            "S11_plus_S1M": split_sum,
            "S1V_residual": residual,
            "status": status,
        }

    network_errors = any(x["status"] == "NETWORK_ERROR" for x in results.values())
    exact_split = (
        not network_errors
        and critical["MIO_EUR"]["status"] == "PASS"
        and critical["MIO_NAC"]["status"] == "PASS"
    )

    status_counts = {}
    for item in results.values():
        status = str(item["status"])
        status_counts[status] = status_counts.get(status, 0) + 1

    report = {
        "audit_version": "0.1",
        "phase": "Eurostat bop_iip6_q detailed-sector audit",
        "benchmark_changed": False,
        "F21_materialization_allowed": False,
        "total_F2_materialization_allowed": False,
        "behavioural_closure_changed": False,
        "period": PERIOD,
        "series_requested": len(specs),
        "series_status_counts": status_counts,
        "network_errors_present": network_errors,
        "availability": availability,
        "critical_S1V_split": critical,
        "cross_source_BPS_controls": cross_source,
        "exact_S11_S1M_split_available": exact_split,
        "promotion_status": (
            "DETAILED_S11_S1M_AVAILABLE_FOR_LATER_CONCEPT_BRIDGE"
            if exact_split
            else "H_C_EXTERNAL_F2_SPLIT_REMAINS_BLOCKED"
        ),
        "rule": (
            "Schema support for S11/S1M is not treated as data availability. "
            "Only direct Eurostat observations can resolve S1V, and BPM6 values remain "
            "outside the ESA/QSA Accounting Spine until a separate concept bridge passes."
        ),
    }
    (OUT / "eurostat_bop_iip6_q_f2_sector_detail_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "series_status_counts": status_counts,
                "critical_S1V_split": critical,
                "exact_S11_S1M_split_available": exact_split,
                "promotion_status": report["promotion_status"],
                "cross_source_BPS_controls": cross_source,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
