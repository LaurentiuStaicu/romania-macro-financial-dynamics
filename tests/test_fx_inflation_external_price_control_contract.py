from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FxInflationExternalPriceControlContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "calibration_validation"
                / "fx_inflation_external_price_control_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_exact_total_import_world_uvi_boundary_is_frozen(self) -> None:
        control = self.contract["selected_fallback_control"]
        dims = control["exact_dimensions"]
        self.assertEqual(dims["freq"], "M")
        self.assertEqual(dims["stk_flow"], "IMP")
        self.assertEqual(dims["indic_et"], "IVU")
        self.assertEqual(dims["partner"], "WORLD")
        self.assertEqual(dims["bclas_bec"], "TOTAL")
        self.assertEqual(dims["geo"], "RO")
        self.assertEqual(
            control["live_structure_evidence"]["non_null_observations"],
            294,
        )
        self.assertEqual(
            control["live_structure_evidence"]["first_period"],
            "2002-01",
        )

    def test_uvi_is_not_relabelled_as_direct_import_price_index(self) -> None:
        control = self.contract["selected_fallback_control"]
        self.assertEqual(control["role"], "external-price proxy")
        self.assertIn(
            "not relabelled",
            control["conceptual_limit"],
        )
        self.assertIn(
            "no currency dimension",
            control["currency_boundary"],
        )

    def test_contract_does_not_open_estimation_or_closure(self) -> None:
        self.assertFalse(self.contract["estimation_authorized"])
        hard = self.contract["hard_rules"]
        self.assertTrue(hard["no_post_fit_external_price_control_selection"])
        self.assertTrue(hard["no_BEC_subcategory_search"])
        self.assertTrue(hard["no_currency_variant_search"])
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertTrue(hard["no_behavioural_closure_change"])


if __name__ == "__main__":
    unittest.main()
