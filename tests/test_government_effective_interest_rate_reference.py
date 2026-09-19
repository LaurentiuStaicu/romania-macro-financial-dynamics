from __future__ import annotations

import csv
import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def load_rates(relative: str) -> dict[int, float]:
    with (ROOT / relative).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {int(row["period"]): float(row["average_interest_rate_pct"]) for row in rows}


class GovernmentEffectiveInterestRateReferenceTests(unittest.TestCase):
    def test_series_is_complete_finite_and_matches_legacy_overlap(self) -> None:
        current = load_rates(
            "data/processed/government_debt_average_interest_rate_mof_2014_2023.csv"
        )
        legacy = load_rates(
            "data/processed/government_debt_average_interest_rate_mof_2019_2023.csv"
        )

        self.assertEqual(sorted(current), list(range(2014, 2024)))
        self.assertTrue(all(math.isfinite(value) for value in current.values()))
        for year, value in legacy.items():
            self.assertEqual(current[year], value)

    def test_official_source_overlaps_are_exactly_consistent(self) -> None:
        provenance = load_json(
            "data/provenance/government_debt_average_interest_rate_mof_2014_2023.json"
        )
        current = load_rates(
            "data/processed/government_debt_average_interest_rate_mof_2014_2023.csv"
        )

        seen: dict[int, set[float]] = {}
        for source in provenance["sources"]:
            self.assertEqual(source["institution"], "Romania Ministry of Finance")
            self.assertTrue(source["url"].startswith("https://"))
            for year, value in source["observed"].items():
                seen.setdefault(int(year), set()).add(float(value))

        for year, values in seen.items():
            self.assertEqual(len(values), 1)
            self.assertEqual(current[year], next(iter(values)))

    def test_definition_boundary_prevents_proxy_substitution(self) -> None:
        contract = load_json(
            "model/dynamics/government_effective_interest_rate_reference_contract.json"
        )
        boundary = contract["concept_boundary"]
        rules = contract["hard_rules"]

        self.assertTrue(boundary["source_is_MoF_portfolio_average_interest_rate"])
        self.assertTrue(boundary["not_Eurostat_Maastricht_apparent_cost"])
        self.assertTrue(boundary["not_marginal_sovereign_yield"])
        self.assertTrue(boundary["does_not_identify_repricing_share_m"])
        self.assertTrue(rules["no_quarterly_interpolation"])
        self.assertTrue(rules["no_repricing_parameter_estimation"])
        self.assertFalse(rules["government_refinancing_mechanism_may_change"])
        self.assertFalse(rules["behavioural_closure_may_change"])

    def test_promotion_does_not_activate_government_mechanism(self) -> None:
        assessment = load_json(
            "model/dynamics/government_effective_interest_rate_reference_assessment.json"
        )
        mechanisms = load_json("model/empirical_dynamics/mechanism_registry.json")
        model = load_json("model/registries/model_contract.json")

        mechanism = next(
            item for item in mechanisms["mechanisms"]
            if item["id"] == "government_refinancing_effective_rate"
        )
        self.assertEqual(assessment["verdict"], "PROMOTE_TO_OBSERVED_SERIES_AVAILABLE")
        self.assertEqual(mechanism["classification"], "DEFERRED")
        self.assertFalse(mechanism["central_feedback"])
        self.assertFalse(model["dynamic_core"]["behavioural_closure_active"])
        self.assertGreaterEqual(model["dynamic_core"]["reference_mode_ready_count"], 8)


if __name__ == "__main__":
    unittest.main()
