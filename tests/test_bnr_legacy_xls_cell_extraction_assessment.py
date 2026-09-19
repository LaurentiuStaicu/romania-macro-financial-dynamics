from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"model"/"calibration_validation"/"bnr_legacy_xls_cell_extraction_assessment.json"
VINTAGE=ROOT/"data"/"source_vintages"/"bnr-legacy-xls-cell-extraction-vintage-2026-09-19"

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

class BNRLegacyXLSCellExtractionAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.a=json.loads(P.read_text(encoding="utf-8"))

    def test_exact_artifact_and_engine_are_frozen(self):
        w=self.a["reviewed_workflow"]
        self.assertEqual(w["artifact_id"],10582798806)
        self.assertEqual(
            w["artifact_zip_sha256"],
            "4ba78ffee9504ef919723f7b59db3a34eeec029b03065050035f24492a3de58d",
        )
        engine=self.a["extraction_engine"]
        self.assertEqual(engine["version"],"2.0.2")
        self.assertEqual(
            engine["distribution_sha256"],
            "ea762c3d29f4cca48d82df517b6d89fbce4db3107f9d78713e48cd321d5c9aa9",
        )
        self.assertEqual(len(self.a["expected_files"]),8)

    def test_exact_reviewed_extraction_is_retained_offline(self):
        expected={item["path"] for item in self.a["expected_files"]}
        actual={
            str(path.relative_to(VINTAGE))
            for path in VINTAGE.rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual,expected)
        for item in self.a["expected_files"]:
            path=VINTAGE/item["path"]
            self.assertEqual(path.stat().st_size,item["bytes"])
            self.assertEqual(sha256(path),item["sha256"])

    def test_question_anchor_coordinates_are_stable(self):
        schema=self.a["schema_stability"]
        self.assertTrue(schema["all_seven_workbooks_parsed"])
        self.assertTrue(schema["all_have_two_sheets"])
        self.assertTrue(schema["anchor_coordinates_stable"])
        self.assertEqual(schema["anchors"]["C01"],["A2"])
        self.assertEqual(schema["anchors"]["C05"],["A225"])
        self.assertEqual(schema["anchors"]["P01"],["A2"])
        self.assertEqual(schema["anchors"]["P06"],["A90"])
        self.assertEqual(schema["anchors"]["P13"],["A293"])
        self.assertEqual(schema["anchors"]["P1103"],["A212"])

    def test_pass_does_not_authorize_model_series_or_fit(self):
        effects=self.a["hard_effects"]
        self.assertTrue(effects["legacy_xls_extraction_path_available"])
        self.assertFalse(effects["behavioural_variable_selection"])
        self.assertFalse(effects["longitudinal_series_ready"])
        self.assertFalse(effects["dsti_level_observed"])
        self.assertFalse(effects["parameter_estimation_authorized"])
        self.assertFalse(effects["model_selection_authorized"])
        self.assertFalse(effects["system_dynamics_activation"])
        self.assertFalse(effects["behavioural_closure_change"])

if __name__=="__main__":
    unittest.main()
