from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class FxInflationExternalPriceControlScreeningTests(unittest.TestCase):
    def test_fallback_is_preregistered_without_opening_calibration(self) -> None:
        screening = load(
            "model/calibration_validation/"
            "fx_inflation_external_price_control_screening.json"
        )
        review = load(
            "model/calibration_validation/"
            "fx_inflation_pass_through_source_boundary_review.json"
        )
        self.assertEqual(
            screening["preferred_direct_control"]["status"],
            "ROMANIA_COVERAGE_NOT_CONFIRMED",
        )
        self.assertEqual(
            screening["preregistered_fallback"]["status"],
            "SOURCE_FAMILY_CONFIRMED_EXACT_SERIES_CODE_PENDING_MATERIALISATION",
        )
        self.assertFalse(screening["disposition"]["calibration_cycle_open"])
        self.assertFalse(review["external_price_control_screen"]["calibration_may_open"])

    def test_euro_uvi_is_fixed_before_fit_and_ron_uvi_cannot_be_swapped_in(self) -> None:
        screening = load(
            "model/calibration_validation/"
            "fx_inflation_external_price_control_screening.json"
        )
        limits = screening["methodological_limits"]
        fallback = screening["preregistered_fallback"]
        self.assertTrue(limits["euro_denomination_selected_before_fit"])
        self.assertTrue(limits["no_RON_denomination_switch_after_fit"])
        self.assertIn(
            "unit-value index denominated in euro",
            fallback["required_dimensions_before_use"],
        )
        self.assertTrue(limits["UVI_is_not_direct_import_price_index"])
        self.assertTrue(limits["composition_effects_possible"])

    def test_no_geographic_or_proxy_substitution_is_allowed(self) -> None:
        screening = load(
            "model/calibration_validation/"
            "fx_inflation_external_price_control_screening.json"
        )
        limits = screening["methodological_limits"]
        self.assertTrue(limits["no_EU_or_euro_area_aggregate_substitution_for_Romania"])
        self.assertTrue(limits["no_global_commodity_index_substitution_without_new_contract"])
        self.assertTrue(limits["no_post_fit_control_selection"])


if __name__ == "__main__":
    unittest.main()
