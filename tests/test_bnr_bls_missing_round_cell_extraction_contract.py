from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "bnr_bls_missing_round_cell_extraction_contract.json"
)


class BNRBLSMissingRoundCellExtractionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_exact_three_recovered_workbooks_are_frozen(self) -> None:
        files = self.contract["files"]
        self.assertEqual(
            [item["target_quarter"] for item in files],
            ["2023-Q2", "2023-Q3", "2024-Q2"],
        )
        self.assertEqual(len(files), 3)
        self.assertEqual(len({item["sha256"] for item in files}), 3)

    def test_engine_is_pinned_to_retained_legacy_path(self) -> None:
        engine = self.contract["extraction_engine"]
        self.assertEqual(engine["package"], "xlrd")
        self.assertEqual(engine["version"], "2.0.2")
        self.assertEqual(
            engine["distribution_sha256"],
            "ea762c3d29f4cca48d82df517b6d89fbce4db3107f9d78713e48cd321d5c9aa9",
        )

    def test_every_cell_is_serialized_before_semantic_selection(self) -> None:
        rules = self.contract["extraction_rules"]
        self.assertTrue(rules["serialize_every_non_empty_cell"])
        self.assertTrue(rules["preserve_cell_coordinates"])
        self.assertTrue(rules["preserve_cell_type"])
        self.assertTrue(rules["retain_numeric_values_without_rounding"])
        self.assertTrue(rules["no_cell_selection_by_model_outcome"])
        self.assertTrue(rules["no_missing_to_zero"])

    def test_extraction_cannot_mutate_model_facing_state(self) -> None:
        hard = self.contract["hard_rules"]
        self.assertTrue(hard["no_behavioural_variable_selection"])
        self.assertTrue(hard["no_canonical_panel_mutation"])
        self.assertTrue(hard["no_longitudinal_series_materialisation"])
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_holdout_opening"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertTrue(hard["no_behavioural_closure_change"])
        self.assertTrue(hard["offline_source_bytes_only"])

    def test_pass_effect_requires_separate_semantic_review(self) -> None:
        self.assertEqual(
            self.contract["pass_effect"],
            "MISSING_ROUND_CELL_EXTRACTIONS_READY_FOR_EXPLICIT_SEMANTIC_COORDINATE_REVIEW_ONLY",
        )


if __name__ == "__main__":
    unittest.main()
