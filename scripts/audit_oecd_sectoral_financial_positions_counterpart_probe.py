from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "model"
    / "dynamics"
    / "sectoral_financial_positions_oecd_counterpart_probe_contract.json"
)
OUT = Path(
    os.environ.get(
        "OECD_SECTORAL_COUNTERPART_PROBE_OUT",
        "sectoral_financial_positions_oecd_counterpart_probe_artifacts",
    )
)
USER_AGENT = (
    "romanian-monetary-dynamics/0.1.0 "
    "(+OECD sectoral-financial-position counterpart discovery probe)"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def fetch(
    url: str,
    *,
    accept: str,
    timeout: int = 60,
    attempts: int = 2,
) -> tuple[bytes, dict[str, str], int | None, str | None]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": accept,
        },
    )
    last_error: str | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return (
                    response.read(),
                    dict(response.headers.items()),
                    int(response.status),
                    None,
                )
        except urllib.error.HTTPError as exc:
            return (
                exc.read(),
                dict(exc.headers.items()),
                int(exc.code),
                f"HTTPError:{exc.code}",
            )
        except Exception as exc:
            last_error = f"{type(exc).__name__}:{exc}"
            if attempt < attempts:
                time.sleep(1)
    return b"", {}, None, last_error


def dimension_order_from_structure(xml_bytes: bytes) -> list[str]:
    root = ET.fromstring(xml_bytes)
    candidates: list[list[tuple[int, str, bool]]] = []

    for element in root.iter():
        if local_name(element.tag) != "DataStructure":
            continue

        dimensions: list[tuple[int, str, bool]] = []
        for child in element.iter():
            kind = local_name(child.tag)
            if kind not in {"Dimension", "TimeDimension"}:
                continue
            dimension_id = child.attrib.get("id")
            if not dimension_id:
                continue
            position_raw = child.attrib.get("position")
            position = int(position_raw) if position_raw is not None else 10_000
            dimensions.append(
                (position, dimension_id, kind == "TimeDimension")
            )

        if dimensions:
            candidates.append(dimensions)

    for dimensions in candidates:
        ids = {item[1] for item in dimensions}
        if {"REF_AREA", "FREQ"} <= ids:
            ordered = sorted(dimensions, key=lambda item: item[0])
            return [
                dimension_id
                for _, dimension_id, is_time in ordered
                if not is_time and dimension_id != "TIME_PERIOD"
            ]

    raise ValueError(
        "No SDMX DataStructure containing REF_AREA and FREQ dimensions was found"
    )


def build_country_key(
    dimension_order: list[str],
    *,
    reference_area: str,
    frequency: str,
) -> str:
    values: list[str] = []
    for dimension_id in dimension_order:
        if dimension_id == "REF_AREA":
            values.append(reference_area)
        elif dimension_id == "FREQ":
            values.append(frequency)
        else:
            values.append("")

    if "REF_AREA" not in dimension_order:
        raise ValueError("REF_AREA is absent from SDMX dimension order")
    if "FREQ" not in dimension_order:
        raise ValueError("FREQ is absent from SDMX dimension order")

    return ".".join(values)


def inspect_csv(data: bytes) -> dict:
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        return {
            "header": [],
            "data_row_count": 0,
            "romania_identity_present": False,
        }

    row_count = 0
    romania = False
    for row in reader:
        if not any(cell.strip() for cell in row):
            continue
        row_count += 1
        for cell in row:
            value = cell.strip()
            if value == "ROU" or value.casefold() == "romania":
                romania = True

    return {
        "header": header,
        "data_row_count": row_count,
        "romania_identity_present": romania,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    scope = contract["query_scope"]
    base_data_url = contract["provider"]["base_data_url"]

    results = []
    for item in contract["provider"]["dataflows"]:
        structure_body, structure_headers, structure_status, structure_error = fetch(
            item["structure_url"],
            accept="application/vnd.sdmx.structure+xml,application/xml,text/xml,*/*",
        )
        structure_path = OUT / f'{item["id"]}_structure.xml'
        if structure_body:
            structure_path.write_bytes(structure_body)

        dimension_order: list[str] = []
        query_key: str | None = None
        structure_parse_error: str | None = None
        if structure_status == 200 and structure_body:
            try:
                dimension_order = dimension_order_from_structure(structure_body)
                query_key = build_country_key(
                    dimension_order,
                    reference_area=scope["reference_area"],
                    frequency=scope["frequency"],
                )
            except Exception as exc:
                structure_parse_error = f"{type(exc).__name__}:{exc}"

        data_body = b""
        data_headers: dict[str, str] = {}
        data_status: int | None = None
        data_error: str | None = None
        data_url: str | None = None
        csv_summary = {
            "header": [],
            "data_row_count": 0,
            "romania_identity_present": False,
        }

        if query_key is not None:
            query = urllib.parse.urlencode(
                {
                    "startPeriod": scope["start_period"],
                    "endPeriod": scope["end_period"],
                    "dimensionAtObservation": scope["dimension_at_observation"],
                    "format": scope["response_format"],
                }
            )
            # OECD Data Explorer emits an empty version slot before the key
            # for these current dataflows: <flow_ref>,/<selection-key>.
            data_url = f"{base_data_url}/{item['flow_ref']},/{query_key}?{query}"
            data_body, data_headers, data_status, data_error = fetch(
                data_url,
                accept="text/csv,application/vnd.sdmx.data+csv,*/*",
            )
            data_path = OUT / f'{item["id"]}_romania.csv'
            if data_body:
                data_path.write_bytes(data_body)
            if data_status == 200 and data_body:
                csv_summary = inspect_csv(data_body)

        available = (
            data_status
            == contract["discovery_pass_rule"]["each_required_http_status"]
            and csv_summary["data_row_count"] > 0
            and csv_summary["romania_identity_present"]
        )

        results.append(
            {
                "id": item["id"],
                "flow_ref": item["flow_ref"],
                "structure_url": item["structure_url"],
                "structure_http_status": structure_status,
                "structure_error": structure_error,
                "structure_content_type": structure_headers.get("Content-Type"),
                "structure_bytes": len(structure_body),
                "structure_sha256": sha256(structure_body)
                if structure_body
                else None,
                "structure_parse_error": structure_parse_error,
                "dimension_order": dimension_order,
                "query_key": query_key,
                "data_url": data_url,
                "data_http_status": data_status,
                "data_error": data_error,
                "data_content_type": data_headers.get("Content-Type"),
                "data_bytes": len(data_body),
                "data_sha256": sha256(data_body) if data_body else None,
                "csv_header": csv_summary["header"],
                "csv_data_row_count": csv_summary["data_row_count"],
                "romania_identity_present": csv_summary[
                    "romania_identity_present"
                ],
                "country_data_available": available,
            }
        )

    by_id = {item["id"]: item for item in results}
    required = contract["discovery_pass_rule"]["required_dataflows"]
    pass_gate = all(
        by_id.get(item_id, {}).get("country_data_available", False)
        for item_id in required
    )

    audit = {
        "audit_version": "0.1",
        "generated_at_utc": datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "phase": contract["phase"],
        "reference_mode": contract["reference_mode"],
        "formal_reference_mode_gate": False,
        "query_scope": scope,
        "results": results,
        "discovery_gate_pass": pass_gate,
        "disposition": (
            contract["discovery_pass_rule"]["effect_if_pass"]
            if pass_gate
            else contract["discovery_pass_rule"]["effect_if_fail"]
        ),
        "semantic_mapping_performed": False,
        "reconciliation_test_performed": False,
        "historical_phase_A_D_reinterpreted": False,
        "reference_mode_promotion": False,
        "accounting_readiness_change": False,
        "system_dynamics_activation": False,
        "behavioural_closure_change": False,
        "hard_rules": contract["hard_rules"],
    }
    (OUT / "sectoral_financial_positions_oecd_counterpart_probe.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
