from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class FxInflationExternalPriceControlScreeningTests(unittest.TestCase):
    def test_total_import_world_fallback_is_confirmed_without_opening_calibration(self) -> None:
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
        fallback = screening["preregistered_fallback"]
        self.assertEqual(
            fallback["status"],
            "EXACT_TOTAL_IMPORT_WORLD_UVI_SOURCE_BOUNDARY_CONFIRMED_LIVE",
        )
        self.assertEqual(
            fallback["dataset_identifier"],
            "ext_st_27_2020msbec",
        )
        evidence = fallback["live_product_boundary_probe"]
        self.assertEqual(
            evidence["bclas_bec_codes"],
            ["TOTAL", "INT", "CAP", "CONS", "CONS_TRA"],
        )
        self.assertEqual(evidence["total_ivu_non_null_observations"], 294)
        self.assertEqual(evidence["total_ivu_first_period"], "2002-01")
        self.assertEqual(evidence["total_ivu_last_period"], "2026-06")
        self.assertFalse(screening["disposition"]["calibration_cycle_open"])
        self.assertFalse(
            review["external_price_control_screen"]["calibration_may_open"]
        )

    def test_provider_uvi_boundary_is_fixed_without_inventing_currency_dimension(self) -> None:
        screening = load(
            "model/calibration_validation/"
            "fx_inflation_external_price_control_screening.json"
        )
        limits = screening["methodological_limits"]
        fallback = screening["preregistered_fallback"]
        self.assertFalse(limits["short_term_api_currency_dimension_exposed"])
        self.assertFalse(limits["euro_denomination_selected_before_fit"])
        self.assertIn(
            "do not infer a currency denomination",
            limits["rule_on_currency"].lower(),
        )
        self.assertIn(
            "indicator indic_et = IVU",
            fallback["required_dimensions_before_use"],
        )
        self.assertIn(
            "product bclas_bec = TOTAL",
            fallback["required_dimensions_before_use"],
        )
        self.assertTrue(limits["UVI_is_not_direct_import_price_index"])
        self.assertTrue(limits["composition_effects_possible"])
        self.assertTrue(limits["no_BEC_product_selection_without_new_contract"])
        self.assertFalse(
            limits[
                "member_state_short_term_dataset_may_not_be_relabelled_total_imports"
            ]
        )

    def test_no_geographic_or_proxy_substitution_is_allowed(self) -> None:
        screening = load(
            "model/calibration_validation/"
            "fx_inflation_external_price_control_screening.json"
        )
        limits = screening["methodological_limits"]
        self.assertTrue(
            limits[
                "no_EU_or_euro_area_aggregate_substitution_for_Romania"
            ]
        )
        self.assertTrue(
            limits[
                "no_global_commodity_index_substitution_without_new_contract"
            ]
        )
        self.assertTrue(limits["no_post_fit_control_selection"])


if __name__ == "__main__":
    unittest.main()
