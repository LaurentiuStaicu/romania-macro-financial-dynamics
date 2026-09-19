from __future__ import annotations

import hashlib
import json
import os
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

OUT = Path(
    os.environ.get(
        "FX_HICP_CURRENT_PROBE_OUT",
        "fx_hicp_current_probe_artifacts",
    )
)
API = (
    "https://ec.europa.eu/eurostat/api/dissemination/"
    "statistics/1.0/data/prc_hicp_minr"
)
USER_AGENT = (
    "romanian-monetary-dynamics/0.1.0 "
    "(+GitHub current HICP ECOICOP-v2 source structure probe)"
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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    query = urllib.parse.urlencode({"lang": "en", "geo": "RO"})
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

    raw_path = OUT / "raw_prc_hicp_minr_RO.json"
    raw_path.write_bytes(body)
    if status != 200:
        raise SystemExit(f"Eurostat returned HTTP {status}")

    payload = json.loads(body.decode("utf-8-sig"))
    ids = [str(x) for x in payload["id"]]
    sizes = [int(x) for x in payload["size"]]
    dims = payload["dimension"]
    summary = {}
    for dim in ids:
        category = dims[dim]["category"]
        codes = ordered_codes(category.get("index", {}))
        labels = {
            str(k): str(v)
            for k, v in category.get("label", {}).items()
        }
        summary[dim] = {
            "size": sizes[ids.index(dim)],
            "codes": codes if dim != "time" else None,
            "labels": labels if dim != "time" else None,
            "first": codes[0] if dim == "time" and codes else None,
            "last": codes[-1] if dim == "time" and codes else None,
            "count": len(codes) if dim == "time" else None,
        }

    # Identify provider-coded all-items candidates without guessing a code.
    all_items = []
    for dim in ("coicop", "coicop18", "ecoicop"):
        if dim not in summary:
            continue
        codes = summary[dim]["codes"] or []
        labels = summary[dim]["labels"] or {}
        for code in codes:
            label = labels.get(code, "")
            if "all-items" in label.casefold() or "all items" in label.casefold():
                all_items.append({"dimension": dim, "code": code, "label": label})

    report = {
        "probe_version": "0.1",
        "generated_at_utc": (
            datetime.now(UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "dataset": "prc_hicp_minr",
        "query": {"geo": "RO"},
        "url": url,
        "provider_updated": payload.get("updated"),
        "raw_sha256": sha256(body),
        "raw_bytes": len(body),
        "http_metadata": {
            "content_type": headers.get("Content-Type"),
            "last_modified": headers.get("Last-Modified"),
        },
        "dimensions": summary,
        "all_items_candidates": all_items,
        "scientific_effect": (
            "SOURCE_STRUCTURE_ONLY_NO_TRANSFORM_SELECTION_NO_ESTIMATION"
        ),
        "calibration_cycle_open": False,
        "system_dynamics_activation": False,
        "behavioural_closure_change": False,
    }
    (OUT / "fx_hicp_current_structure_probe.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
