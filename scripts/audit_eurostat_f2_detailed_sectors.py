from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OUT = Path(os.environ.get("EUROSTAT_F2_AUDIT_OUT", "eurostat_f2_audit_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)

API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+Eurostat F2 detailed-sector audit)"

SECTORS = ("S1", "S121", "S12T", "S13", "S12M", "S1V", "S11", "S1M")
CURRENCIES = ("MIO_EUR", "MIO_NAC")
PERIODS = ("2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4")
TOL = 0.1


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(dataset: str, sector: str, currency: str, stock: bool) -> dict[str, object]:
    params: list[tuple[str, str]] = [
        ("lang", "en"),
        ("freq", "Q"),
        ("currency", currency),
        ("bop_item", "FA__O__F2"),
        ("sector10", sector),
        ("sectpart", "S1"),
        ("partner", "WRL_REST"),
        ("geo", "RO"),
        ("sinceTimePeriod", "2025-Q1"),
        ("untilTimePeriod", "2025-Q4"),
    ]
    if stock:
        params.append(("stk_flow", "A_LE"))
    query = urllib.parse.urlencode(params)
    url = f"{API}{dataset}?{query}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
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
                    "dataset": dataset,
                    "sector": sector,
                    "currency": currency,
                    "url": url,
                    "status": "NETWORK_ERROR",
                    "error": str(last_error),
                    "attempts": attempt,
                    "observations": [],
                }
    else:
        raise AssertionError("unreachable retry state")

    raw_name = f"{dataset}_{sector}_{currency}.json"
    raw_path = OUT / "raw" / raw_name
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(body)

    result: dict[str, object] = {
        "dataset": dataset,
        "sector": sector,
        "currency": currency,
        "url": url,
        "http_status": status,
        "raw_path": str(raw_path.relative_to(OUT)),
        "raw_sha256": sha256(body),
        "raw_bytes": len(body),
        "content_type": headers.get("Content-Type"),
        "observations": [],
    }
    if status != 200:
        result["status"] = "HTTP_ERROR"
        result["error_body_prefix"] = body[:500].decode("utf-8", errors="replace")
        return result

    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception as exc:
        result["status"] = "PARSE_ERROR"
        result["error"] = str(exc)
        return result

    result["response_id"] = payload.get("id")
    result["response_size"] = payload.get("size")
    result["updated"] = payload.get("updated")
    result["label"] = payload.get("label")
    result["observations"] = flatten_jsonstat(payload)
    result["status"] = "AVAILABLE" if result["observations"] else "NO_OBSERVATIONS"
    result["stk_flow_categories"] = category_labels(payload, "stk_flow")
    result["sector_categories"] = category_labels(payload, "sector10")
    result["time_categories"] = category_labels(payload, "time")
    return result


def ordered_codes(payload: dict, dim: str) -> list[str]:
    category = payload["dimension"][dim]["category"]
    idx = category.get("index", {})
    if isinstance(idx, list):
        return list(idx)
    return [code for code, _ in sorted(idx.items(), key=lambda kv: kv[1])]


def category_labels(payload: dict, dim: str) -> dict[str, str]:
    if dim not in payload.get("dimension", {}):
        return {}
    category = payload["dimension"][dim]["category"]
    labels = category.get("label", {})
    return {code: labels.get(code, code) for code in ordered_codes(payload, dim)}


def flatten_jsonstat(payload: dict) -> list[dict[str, object]]:
    ids = payload.get("id") or []
    sizes = payload.get("size") or []
    if not ids or not sizes:
        return []
    code_lists = [ordered_codes(payload, dim) for dim in ids]
    values = payload.get("value", [])
    statuses = payload.get("status", {})

    def get_value(flat_index: int):
        if isinstance(values, list):
            return values[flat_index] if flat_index < len(values) else None
        return values.get(str(flat_index))

    def get_status(flat_index: int):
        if isinstance(statuses, list):
            return statuses[flat_index] if flat_index < len(statuses) else None
        if isinstance(statuses, dict):
            return statuses.get(str(flat_index))
        return None

    out = []
    for flat_index, coords in enumerate(itertools.product(*code_lists)):
        value = get_value(flat_index)
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(numeric):
            continue
        row = {dim: code for dim, code in zip(ids, coords)}
        row["value"] = numeric
        row["obs_status"] = get_status(flat_index)
        out.append(row)
    return out


def stock_q4(result: dict[str, object]) -> float | None:
    values = [
        float(row["value"])
        for row in result.get("observations", [])
        if row.get("time") == "2025-Q4"
        and row.get("stk_flow") == "A_LE"
    ]
    if len(values) == 1:
        return values[0]
    return None


def discover_transaction_asset_codes(result: dict[str, object]) -> dict[str, str]:
    labels = result.get("stk_flow_categories", {})
    candidates = {}
    for code, label in labels.items():
        text = str(label).lower()
        if (
            "asset" in text
            and "position" not in text
            and "revaluation" not in text
            and "other changes" not in text
            and "liabilit" not in text
        ):
            candidates[code] = str(label)
    return candidates


def annual_flow_for_code(result: dict[str, object], code: str) -> float | None:
    mapping = {
        row.get("time"): float(row["value"])
        for row in result.get("observations", [])
        if row.get("stk_flow") == code
    }
    if not all(period in mapping for period in PERIODS):
        return None
    return sum(mapping[p] for p in PERIODS)


def identity(total: float | None, parts: list[float | None]) -> dict[str, object]:
    if total is None or any(x is None for x in parts):
        return {"status": "COVERAGE_INCOMPLETE", "residual": None}
    residual = sum(float(x) for x in parts) - float(total)
    return {
        "status": "PASS" if abs(residual) <= TOL else "FAIL",
        "residual": residual,
        "total": total,
        "part_sum": sum(float(x) for x in parts),
    }


def main() -> None:
    tasks = []
    for sector in SECTORS:
        for currency in CURRENCIES:
            tasks.append(("bop_iip6_q", sector, currency, True))
            tasks.append(("bop_c6_q", sector, currency, False))

    results = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(fetch, dataset, sector, currency, stock):
            (dataset, sector, currency)
            for dataset, sector, currency, stock in tasks
        }
        for index, future in enumerate(as_completed(futures), start=1):
            spec = futures[future]
            results[spec] = future.result()
            print(f"[{index}/{len(futures)}] {spec}", flush=True)

    availability = []
    stock_values: dict[tuple[str, str], float | None] = {}
    flow_candidates_by_currency: dict[str, set[str]] = {c: set() for c in CURRENCIES}

    for sector in SECTORS:
        for currency in CURRENCIES:
            stock_result = results[("bop_iip6_q", sector, currency)]
            flow_result = results[("bop_c6_q", sector, currency)]
            sv = stock_q4(stock_result)
            stock_values[(sector, currency)] = sv
            flow_codes = discover_transaction_asset_codes(flow_result)
            flow_candidates_by_currency[currency].update(flow_codes)
            availability.append(
                {
                    "sector": sector,
                    "currency": currency,
                    "stock_2025Q4": sv,
                    "stock_status": stock_result["status"],
                    "stock_stk_flow_categories": stock_result.get("stk_flow_categories", {}),
                    "transaction_status": flow_result["status"],
                    "transaction_stk_flow_categories": flow_result.get("stk_flow_categories", {}),
                    "transaction_asset_code_candidates": flow_codes,
                }
            )

    stock_identities = []
    for currency in CURRENCIES:
        get = lambda s: stock_values[(s, currency)]
        stock_identities.append(
            {
                "currency": currency,
                "identity": "S1V = S11 + S1M",
                **identity(get("S1V"), [get("S11"), get("S1M")]),
            }
        )
        stock_identities.append(
            {
                "currency": currency,
                "identity": "S1 = S121 + S12T + S13 + S12M + S11 + S1M",
                **identity(
                    get("S1"),
                    [get("S121"), get("S12T"), get("S13"), get("S12M"), get("S11"), get("S1M")],
                ),
            }
        )

    flow_assessment = []
    for currency in CURRENCIES:
        codes = sorted(flow_candidates_by_currency[currency])
        for code in codes:
            rows = {}
            for sector in SECTORS:
                rows[sector] = annual_flow_for_code(
                    results[("bop_c6_q", sector, currency)], code
                )
            flow_assessment.append(
                {
                    "currency": currency,
                    "stk_flow_code": code,
                    "stk_flow_label": next(
                        (
                            results[("bop_c6_q", sector, currency)]
                            .get("stk_flow_categories", {})
                            .get(code)
                            for sector in SECTORS
                            if code in results[("bop_c6_q", sector, currency)].get("stk_flow_categories", {})
                        ),
                        code,
                    ),
                    "annual_2025_by_sector": rows,
                    "S1V_equals_S11_plus_S1M": identity(
                        rows["S1V"], [rows["S11"], rows["S1M"]]
                    ),
                }
            )

    all_source_statuses = {}
    for result in results.values():
        status = str(result.get("status"))
        all_source_statuses[status] = all_source_statuses.get(status, 0) + 1

    detailed_stock_available = {
        currency: (
            stock_values[("S11", currency)] is not None
            and stock_values[("S1M", currency)] is not None
            and next(
                item for item in stock_identities
                if item["currency"] == currency and item["identity"] == "S1V = S11 + S1M"
            )["status"] == "PASS"
        )
        for currency in CURRENCIES
    }

    report = {
        "audit_version": "0.1",
        "phase": "Eurostat detailed-sector dissemination audit for external F2",
        "benchmark_changed": False,
        "F21_materialization_allowed": False,
        "total_F2_materialization_allowed": False,
        "behavioural_closure_changed": False,
        "source_status_counts": all_source_statuses,
        "network_errors_present": any(
            r.get("status") == "NETWORK_ERROR" for r in results.values()
        ),
        "availability": availability,
        "stock_identity_checks": stock_identities,
        "detailed_stock_H_C_split_available": detailed_stock_available,
        "transaction_asset_code_candidates": {
            c: sorted(flow_candidates_by_currency[c]) for c in CURRENCIES
        },
        "transaction_assessment": flow_assessment,
        "promotion_status": (
            "EUROSTAT_DETAILED_STOCK_SECTORS_AVAILABLE_CONCEPT_BRIDGE_REQUIRED"
            if any(detailed_stock_available.values())
            else "EUROSTAT_DETAILED_H_C_SPLIT_UNAVAILABLE"
        ),
        "rule": (
            "Eurostat dissemination is audited independently of ECB BPS. "
            "Presence of S11/S1M in the dataset nomenclature is not treated as "
            "evidence of Romania observations; only returned observations count."
        ),
    }

    (OUT / "eurostat_f2_detailed_sector_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "source_status_counts": all_source_statuses,
                "network_errors_present": report["network_errors_present"],
                "detailed_stock_H_C_split_available": detailed_stock_available,
                "stock_identity_checks": stock_identities,
                "transaction_asset_code_candidates": report["transaction_asset_code_candidates"],
                "promotion_status": report["promotion_status"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
