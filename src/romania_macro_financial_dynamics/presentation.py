"""Presentation payload builders for the InfoClar v1.1 Dynamic Core surface.

These helpers expose model-specific stock/flow information to future UI layers
without reimplementing scientific equations in JavaScript/TypeScript.
"""

from __future__ import annotations

from math import isfinite
from typing import Mapping

from .accounting import SECTOR_IDS
from .dynamics import PositionKey, sector_balance_sheets, system_net_financial_worth


def build_stock_flow_graph(
    positions: Mapping[PositionKey, float],
    *,
    period: str,
    unit: str = "million_RON",
    scientific_status: str = "DERIVED",
) -> dict:
    """Build the canonical macro-financial graph payload for the central panel."""

    if not period:
        raise ValueError("period is required")

    nodes = [
        {
            "id": sector,
            "kind": "institutional_sector",
            "semantic_role": "holder_and_issuer",
        }
        for sector in SECTOR_IDS
    ]

    edges = []
    for key, value in sorted(positions.items()):
        if not isfinite(value):
            raise ValueError(f"Non-finite graph value for {key}")
        edges.append(
            {
                "id": f"{key.instrument}:{key.issuer}->{key.holder}",
                "kind": "stock_relationship",
                "source": key.issuer,
                "target": key.holder,
                "holder": key.holder,
                "issuer": key.issuer,
                "instrument": key.instrument,
                "value": value,
                "unit": unit,
                "period": period,
                "scientific_status": scientific_status,
                "semantic": "issuer_liability_equals_holder_asset",
            }
        )

    return {
        "view": "macro_financial_stock_flow_network",
        "nodes": nodes,
        "edges": edges,
        "essential_information_requires_hover": False,
        "colour_only_encoding": False,
    }


def build_balance_sheet_dashboard(
    positions: Mapping[PositionKey, float],
    *,
    period: str,
    unit: str = "million_RON",
) -> dict:
    """Build exact-value balance-sheet indicators for the dashboard panel."""

    sheets = sector_balance_sheets(positions)
    rows = []
    for sector in SECTOR_IDS:
        values = sheets[sector]
        rows.append(
            {
                "sector": sector,
                "assets": values["assets"],
                "liabilities": values["liabilities"],
                "net_financial_worth": values["net_financial_worth"],
                "unit": unit,
                "period": period,
            }
        )

    return {
        "view": "balance_sheet_dashboard",
        "rows": rows,
        "system_net_financial_worth": system_net_financial_worth(positions),
        "unit": unit,
        "period": period,
        "conservation_expected": True,
    }


def theory_context(selection_kind: str) -> tuple[str, ...]:
    """Return canonical theory topics for a selected scientific object."""

    mapping = {
        "sector": (
            "definition",
            "accounting_role",
            "dynamic_role",
            "data_scope",
            "limitations",
        ),
        "financial_position": (
            "stock_identity",
            "holder_asset_issuer_liability",
            "instrument_definition",
            "provenance",
            "missing_data_semantics",
        ),
        "transaction_or_change": (
            "stock_flow_distinction",
            "units",
            "period_conversion",
            "source_transformation",
        ),
        "feedback_candidate": (
            "hypothesized_causal_path",
            "evidence_status",
            "why_inactive",
            "activation_requirements",
            "candidate_delays",
        ),
        "delay": (
            "first_order_delay_equation",
            "tau_definition",
            "dimensional_contract",
            "parameter_status",
        ),
    }
    if selection_kind not in mapping:
        raise ValueError(f"Unsupported theory selection kind: {selection_kind}")
    return mapping[selection_kind]


def auxiliary_context(*, object_id: str, scientific_status: str, limitations: list[str]) -> dict:
    """Build auxiliary-panel details without duplicating Theory/Learn prose."""

    if not object_id or not scientific_status:
        raise ValueError("object_id and scientific_status are required")
    return {
        "object_id": object_id,
        "scientific_status": scientific_status,
        "limitations": list(limitations),
        "sections": ("selection_details", "sources", "verification", "limitations"),
    }
