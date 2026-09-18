from __future__ import annotations

import hashlib
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("F21_CONCEPT_BRIDGE_OUT", "f21_concept_bridge_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)

API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/bop_iip6_q"
USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+GitHub BPM6 ESA F2 concept bridge)"
PERIOD = "2025-Q4"
SECTOR_TOL = 1.5
AGG_TOL = 3.5


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def eurostat_url(sector: str, sectpart: str, currency: str) -> str:
    query = urllib.parse.urlencode(
        {
            "lang": "en",
            "freq": "Q",
            "currency": currency,
            "bop_item": "FA__R__F2",
            "sector10": sector,
            "sectpart": sectpart,
            "stk_flow": "A_LE",
            "partner": "WRL_REST",
            "geo": "RO",
            "sinceTimePeriod": PERIOD,
            "untilTimePeriod": PERIOD,
        }
    )
    return f"{API}?{query}"


def fetch_reserve(sector: str, sectpart: str, currency: str) -> dict[str, object]:
    url = eurostat_url(sector, sectpart, currency)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
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
                    "sectpart": sectpart,
                    "currency": currency,
                    "url": url,
                    "status": "NETWORK_ERROR",
                    "error": str(last_error),
                    "value": None,
                }
    else:
        raise AssertionError("unreachable retry state")

    raw_name = hashlib.sha256(f"{sector}|{sectpart}|{currency}".encode()).hexdigest()[:16] + ".json"
    raw_path = OUT / "raw" / raw_name
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(body)

    result: dict[str, object] = {
        "sector": sector,
        "sectpart": sectpart,
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
        return result

    ids = payload.get("id") or []
    sizes = payload.get("size") or []
    if len(ids) != len(sizes) or any(
        int(size) != 1 for dim, size in zip(ids, sizes) if dim != "time"
    ):
        result["status"] = "UNEXPECTED_DIMENSIONS"
        result["ids"] = ids
        result["sizes"] = sizes
        return result

    time_index = (
        payload.get("dimension", {})
        .get("time", {})
        .get("category", {})
        .get("index", {})
    )
    if isinstance(time_index, list):
        times = list(time_index)
    else:
        times = [k for k, _ in sorted(time_index.items(), key=lambda item: int(item[1]))]
    if PERIOD not in times:
        result["status"] = "NO_OBSERVATION"
        return result

    pos = times.index(PERIOD)
    values = payload.get("value", {})
    raw_value = (
        values[pos] if isinstance(values, list) and pos < len(values)
        else values.get(str(pos)) if isinstance(values, dict)
        else None
    )
    if raw_value is None:
        result["status"] = "NO_OBSERVATION"
        return result

    result["status"] = "AVAILABLE"
    result["value"] = float(raw_value)
    result["dataset_updated"] = payload.get("updated")
    return result


def choose_reserve(results: dict[tuple[str, str, str], dict], currency: str) -> dict:
    candidates = []
    for sector, sectpart in (("S121", "S1"), ("S1", "S1"), ("S121", "S1N"), ("S1", "S1N")):
        item = results[(sector, sectpart, currency)]
        if item.get("value") is not None:
            candidates.append(item)
    if not candidates:
        return {"status": "UNAVAILABLE", "value": None, "candidate_count": 0}

    values = [float(x["value"]) for x in candidates]
    if max(values) - min(values) > SECTOR_TOL:
        return {
            "status": "CONFLICTING_AVAILABLE_REPRESENTATIONS",
            "value": None,
            "candidate_count": len(candidates),
            "candidates": candidates,
        }

    preferred = next(
        (x for x in candidates if x["sector"] == "S121" and x["sectpart"] == "S1"),
        candidates[0],
    )
    return {
        "status": "AVAILABLE",
        "value": float(preferred["value"]),
        "selected": {
            "sector": preferred["sector"],
            "sectpart": preferred["sectpart"],
            "currency": preferred["currency"],
        },
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def main() -> None:
    eurostat = json.loads(
        (ROOT / "model" / "accounting" / "eurostat_f2_sector_detail_assessment.json").read_text(
            encoding="utf-8"
        )
    )
    qsa_f2m = json.loads(
        (ROOT / "model" / "accounting" / "f2m_component_2025.json").read_text(
            encoding="utf-8"
        )
    )
    qsa_controls = json.loads(
        (ROOT / "model" / "accounting" / "f21_f2_external_bridge_assessment.json").read_text(
            encoding="utf-8"
        )
    )

    specs = [
        (sector, sectpart, currency)
        for sector in ("S121", "S1")
        for sectpart in ("S1", "S1N")
        for currency in ("MIO_NAC", "MIO_EUR")
    ]
    reserve_results = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(fetch_reserve, *spec): spec for spec in specs
        }
        for i, future in enumerate(as_completed(futures), start=1):
            spec = futures[future]
            reserve_results[spec] = future.result()
            print(f"[{i}/{len(futures)}] reserve {spec}: {reserve_results[spec]['status']}", flush=True)

    reserve_nac = choose_reserve(reserve_results, "MIO_NAC")
    reserve_eur = choose_reserve(reserve_results, "MIO_EUR")

    oi = eurostat["stock_MIO_NAC"]
    bpm6_other_investment = {
        "H": float(oi["households_NPISH_S1M"]),
        "C": float(oi["nonfinancial_corporations_S11"]),
        "G": float(oi["government_S13"]),
        "F": float(oi["MFI_S12T"]) + float(oi["other_financial_S12M"]),
        "BNR": float(oi["BNR_S121"]),
    }

    f2m_external = {}
    for cell in qsa_f2m["matrices"]["stock"]:
        if cell["issuer"] == "X" and cell["holder"] in {"H", "C", "F", "G", "BNR"}:
            if cell["value"] is None:
                raise RuntimeError(f"Missing materialized external F2M cell: {cell}")
            f2m_external[cell["holder"]] = float(cell["value"])
    if set(f2m_external) != {"H", "C", "F", "G", "BNR"}:
        raise RuntimeError("Incomplete materialized external F2M holder set")

    sector_bridge = []
    reserve_value = reserve_nac.get("value")
    for sector in ("H", "C", "F", "G", "BNR"):
        candidate = bpm6_other_investment[sector]
        components = {
            "BPM6_other_investment_F2_million_RON": bpm6_other_investment[sector]
        }
        if sector == "BNR":
            if reserve_value is None:
                candidate_total = None
            else:
                candidate_total = candidate + float(reserve_value)
                components["BPM6_reserve_assets_F2_million_RON"] = float(reserve_value)
        else:
            candidate_total = candidate

        if candidate_total is None:
            implied_f21 = None
            status = "RESERVE_F2_UNAVAILABLE"
        else:
            implied_f21 = candidate_total - f2m_external[sector]
            status = (
                "PASS_NONNEGATIVE_WITHIN_SOURCE_PRECISION"
                if implied_f21 >= -SECTOR_TOL
                else "FAIL_NEGATIVE_IMPLIED_F21"
            )
        sector_bridge.append(
            {
                "sector": sector,
                "candidate_BPM6_total_external_F2_million_RON": candidate_total,
                "components": components,
                "materialized_QSA_external_F2M_million_RON": f2m_external[sector],
                "implied_external_F21_million_RON": implied_f21,
                "status": status,
            }
        )

    qsa_total_f2 = float(qsa_controls["aggregate_QSA_controls"]["stock"]["published_W1_total_F2_million_RON"])
    qsa_total_f21 = float(qsa_controls["aggregate_QSA_controls"]["stock"]["published_W1_total_F21_million_RON"])

    if all(x["candidate_BPM6_total_external_F2_million_RON"] is not None for x in sector_bridge):
        sum_f2 = sum(float(x["candidate_BPM6_total_external_F2_million_RON"]) for x in sector_bridge)
        sum_f21 = sum(float(x["implied_external_F21_million_RON"]) for x in sector_bridge)
        f2_residual = sum_f2 - qsa_total_f2
        f21_residual = sum_f21 - qsa_total_f21
        f2_status = "PASS" if abs(f2_residual) <= AGG_TOL else "FAIL"
        f21_status = "PASS" if abs(f21_residual) <= AGG_TOL else "FAIL"
    else:
        sum_f2 = sum_f21 = f2_residual = f21_residual = None
        f2_status = f21_status = "CONTROL_BLOCKED"

    sector_level_pass = all(
        x["status"] == "PASS_NONNEGATIVE_WITHIN_SOURCE_PRECISION"
        for x in sector_bridge
    )
    aggregate_pass = f2_status == "PASS" and f21_status == "PASS"
    network_errors = any(
        x.get("status") == "NETWORK_ERROR" for x in reserve_results.values()
    )
    bridge_pass = (
        reserve_nac.get("status") == "AVAILABLE"
        and not network_errors
        and sector_level_pass
        and aggregate_pass
    )

    report = {
        "audit_version": "0.1",
        "phase": "BPM6-to-ESA F2 concept bridge",
        "benchmark_changed": False,
        "F21_materialization_allowed": False,
        "total_F2_materialization_allowed": False,
        "behavioural_closure_changed": False,
        "reserve_asset_F2_probe": {
            "MIO_NAC": reserve_nac,
            "MIO_EUR": reserve_eur,
            "all_probe_results": list(reserve_results.values()),
        },
        "sector_bridge": sector_bridge,
        "aggregate_controls": {
            "candidate_BPM6_sector_sum_F2_million_RON": sum_f2,
            "published_QSA_W1_F2_million_RON": qsa_total_f2,
            "F2_residual_million_RON": f2_residual,
            "F2_status": f2_status,
            "candidate_implied_F21_sum_million_RON": sum_f21,
            "published_QSA_W1_F21_million_RON": qsa_total_f21,
            "F21_residual_million_RON": f21_residual,
            "F21_status": f21_status,
            "aggregate_tolerance_million_RON": AGG_TOL,
        },
        "sector_level_pass": sector_level_pass,
        "aggregate_pass": aggregate_pass,
        "network_errors_present": network_errors,
        "concept_bridge_pass": bridge_pass,
        "promotion_status": (
            "BPM6_ESA_F2_CONCEPT_BRIDGE_ELIGIBLE_FOR_LATER_MATERIALIZATION"
            if bridge_pass
            else "BPM6_ESA_F2_CONCEPT_BRIDGE_BLOCKED"
        ),
        "rule": (
            "Aggregate agreement cannot override a negative sector-level implied F21. "
            "No discrepancy may be set to zero or transferred across sectors."
        ),
    }
    (OUT / "f21_bpm6_esa_concept_bridge_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "reserve_MIO_NAC": reserve_nac,
        "sector_bridge": sector_bridge,
        "aggregate_controls": report["aggregate_controls"],
        "concept_bridge_pass": bridge_pass,
        "promotion_status": report["promotion_status"],
    }, indent=2))


if __name__ == "__main__":
    main()
