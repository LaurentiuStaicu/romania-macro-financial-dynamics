from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "bnr_bls_missing_round_semantic_mapping_contract.json"
)


class BNRBLSMissingRoundSemanticMappingContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_existing_mapping_is_the_only_coordinate_authority(self) -> None:
        inherited = self.contract["inherited_semantic_rules"]
        self.assertTrue(
            inherited["use_mapping_authority_realised_observables_verbatim"]
        )
        self.assertTrue(inherited["use_mapping_authority_sheet_aliases_verbatim"])
        self.assertTrue(inherited["no_new_observable_coordinates"])
        self.assertTrue(inherited["no_model_outcome_based_selection"])

    def test_exact_three_target_rounds_are_reviewed(self) -> None:
        self.assertEqual(
            [item["target_quarter"] for item in self.contract["rounds"]],
            ["2023-Q2", "2023-Q3", "2024-Q2"],
        )

    def test_round_identity_anomalies_are_explicit_not_normalised(self) -> None:
        by_quarter = {
            item["target_quarter"]: item
            for item in self.contract["rounds"]
        }
        self.assertEqual(
            by_quarter["2023-Q2"]["workbook_header"]["raw_value"],
            "31/03/2023",
        )
        self.assertEqual(
            by_quarter["2024-Q2"]["workbook_header"]["raw_value"],
            "31/06/2024",
        )
        for quarter in ("2023-Q2", "2024-Q2"):
            item = by_quarter[quarter]
            self.assertEqual(
                item["round_authority"],
                "OFFICIAL_BNR_PUBLICATION_QUARTER",
            )
            self.assertTrue(
                item["official_publication"]["url"].startswith(
                    "https://www.bnr.ro/"
                )
            )
        rules = self.contract["round_identity_rules"]
        self.assertTrue(rules["preserve_raw_workbook_header"])
        self.assertTrue(
            rules["never_silently_normalise_invalid_or_stale_dates"]
        )

    def test_valid_november_2023_round_keeps_workbook_date_authority(self) -> None:
        item = next(
            row
            for row in self.contract["rounds"]
            if row["target_quarter"] == "2023-Q3"
        )
        self.assertEqual(item["workbook_header"]["raw_value"], "30/09/2023")
        self.assertEqual(item["round_authority"], "WORKBOOK_COMPANIES_A1")

    def test_review_cannot_change_model_state(self) -> None:
        hard = self.contract["hard_rules"]
        self.assertTrue(hard["no_canonical_panel_mutation"])
        self.assertTrue(hard["no_interpolation"])
        self.assertTrue(hard["no_synthetic_quarter_creation"])
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_holdout_opening"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertTrue(hard["no_behavioural_closure_change"])


if __name__ == "__main__":
    unittest.main()
