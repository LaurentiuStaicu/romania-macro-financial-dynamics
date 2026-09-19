from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT / "model" / "calibration_validation"
    / "bnr_legacy_xls_cell_extraction_contract.json"
)


class BNRLegacyXLSCellExtractionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.c = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_exact_retained_workbook_set_is_frozen(self) -> None:
        self.assertEqual(len(self.c["files"]), 7)
        self.assertEqual(
            {item["id"] for item in self.c["files"]},
            {
                "bls_2023_feb",
                "bls_2023_may",
                "bls_2024_feb",
                "bls_2024_may",
                "bls_2024_nov",
                "bls_2025_feb",
                "bls_2025_nov",
            },
        )
        for item in self.c["files"]:
            self.assertGreater(item["bytes"], 0)
            self.assertEqual(len(item["sha256"]), 64)

    def test_extractor_is_frozen_to_legacy_xls_engine(self) -> None:
        engine = self.c["extraction_engine"]
        self.assertEqual(engine["package"], "xlrd")
        self.assertEqual(engine["version"], "2.0.2")
        self.assertEqual(engine["allowed_format"], "xls")
        self.assertTrue(engine["distribution_archive_sha256_recorded_at_execution"])

    def test_all_non_empty_cells_are_selected_before_semantic_review(self) -> None:
        rules = self.c["extraction_rules"]
        self.assertTrue(rules["serialize_every_non_empty_cell"])
        self.assertTrue(rules["verify_exact_source_bytes_before_open"])
        self.assertTrue(rules["preserve_cell_coordinates"])
        self.assertTrue(rules["preserve_cell_type"])
        self.assertTrue(rules["no_cell_selection_by_model_outcome"])
        self.assertTrue(rules["no_manual_transcription"])
        self.assertEqual(
            self.c["preregistered_anchor_tokens"],
            ["C01", "C05", "P01", "P06", "P13", "P0303", "P1103"],
        )

    def test_extraction_does_not_open_behavioural_cycle(self) -> None:
        hard = self.c["hard_rules"]
        self.assertTrue(hard["no_behavioural_variable_selection"])
        self.assertTrue(hard["no_longitudinal_series_materialisation"])
        self.assertTrue(hard["no_dsti_level_claim"])
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_model_outcome_access"])
        self.assertTrue(hard["no_holdout_opening"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertTrue(hard["no_behavioural_closure_change"])


if __name__ == "__main__":
    unittest.main()
