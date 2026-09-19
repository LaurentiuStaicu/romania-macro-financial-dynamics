from __future__ import annotations

import hashlib
import json
import os
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(
    os.environ.get(
        "FX_EXTERNAL_PRICE_PROBE_OUT",
        "fx_external_price_probe_artifacts",
    )
)
API = (
    "https://ec.europa.eu/eurostat/api/dissemination/"
    "statistics/1.0/data/ext_st_27_2020msbec"
)
USER_AGENT = (
    "romanian-monetary-dynamics/0.1.0 "
    "(+GitHub FX external-price source structure probe)"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ordered_codes(index: object) -> list[str]:
    if isinstance(index, list):
        return [str(item) for item in index]
    if isinstance(index, dict):
        return [
            str(code)
            for code, _ in sorted(
                index.items(), key=lambda item: int(item[1])
            )
        ]
    return []


def value_at(values: object, position: int) -> object:
    if isinstance(values, list):
        return values[position] if position < len(values) else None
    if isinstance(values, dict):
        value = values.get(str(position))
        if value is None:
            value = values.get(position)
        return value
    return None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    query = urllib.parse.urlencode(
        {
            "lang": "en",
            "geo": "RO",
            "stk_flow": "IMP",
            "partner": "WORLD",
        }
    )
    url = f"{API}?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        body = response.read()
        status = int(response.status)
        headers = dict(response.headers.items())
    (OUT / "raw_ext_st_27_2020msbec_RO_IMP_WORLD.json").write_bytes(body)
    if status != 200:
        raise SystemExit(f"Eurostat returned HTTP {status}")

    payload = json.loads(body.decode("utf-8-sig"))
    ids = [str(x) for x in payload["id"]]
    sizes = [int(x) for x in payload["size"]]
    dims = payload["dimension"]
    codes = {
        dim: ordered_codes(dims[dim]["category"]["index"])
        for dim in ids
    }
    labels = {
        dim: {
            str(k): str(v)
            for k, v in dims[dim]["category"].get("label", {}).items()
        }
        for dim in ids
    }

    required = {"freq", "stk_flow", "indic_et", "partner", "bclas_bec", "geo", "time"}
    if set(ids) != required:
        raise SystemExit(f"unexpected dimensions: {ids}")

    # JSON-stat flattened position: rightmost dimension varies fastest.
    strides = {}
    stride = 1
    for dim, size in reversed(list(zip(ids, sizes))):
        strides[dim] = stride
        stride *= size

    total_index = codes["bclas_bec"].index("TOTAL")
    availability = []
    values = payload.get("value", {})
    for indic_index, indic_code in enumerate(codes["indic_et"]):
        periods = []
        for time_index, period in enumerate(codes["time"]):
            coords = {
                "freq": 0,
                "stk_flow": 0,
                "indic_et": indic_index,
                "partner": 0,
                "bclas_bec": total_index,
                "geo": 0,
                "time": time_index,
            }
            position = sum(coords[dim] * strides[dim] for dim in ids)
            if value_at(values, position) is not None:
                periods.append(period)
        availability.append(
            {
                "indic_et": indic_code,
                "label": labels["indic_et"].get(indic_code),
                "total_product_non_null_observations": len(periods),
                "first_period": periods[0] if periods else None,
                "last_period": periods[-1] if periods else None,
            }
        )

    report = {
        "probe_version": "0.1",
        "generated_at_utc": (
            datetime.now(UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "dataset": "ext_st_27_2020msbec",
        "query": {
            "geo": "RO",
            "stk_flow": "IMP",
            "partner": "WORLD",
        },
        "url": url,
        "provider_updated": payload.get("updated"),
        "raw_sha256": sha256(body),
        "raw_bytes": len(body),
        "http_metadata": {
            "content_type": headers.get("Content-Type"),
            "last_modified": headers.get("Last-Modified"),
        },
        "dimensions": {
            dim: {
                "codes": codes[dim],
                "labels": labels[dim],
            }
            for dim in ids
            if dim != "time"
        },
        "total_product_present": "TOTAL" in codes["bclas_bec"],
        "total_product_indicator_availability": availability,
        "scientific_effect": (
            "SOURCE_STRUCTURE_ONLY_NO_CONTROL_SELECTION_NO_ESTIMATION"
        ),
        "calibration_cycle_open": False,
        "system_dynamics_activation": False,
        "behavioural_closure_change": False,
    }
    (OUT / "fx_external_price_product_probe.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
