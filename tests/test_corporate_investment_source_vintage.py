from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VINTAGE = (
    ROOT
    / "data"
    / "source_vintages"
    / "corporate-investment-source-family-vintage-2026-09-19"
)
REVIEW = (
    ROOT
    / "model"
    / "calibration_validation"
    / "corporate_investment_source_vintage_promotion_review.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CorporateInvestmentSourceVintageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = json.loads(REVIEW.read_text(encoding="utf-8"))
        self.manifest = json.loads(
            (VINTAGE / "snapshot_manifest.json").read_text(encoding="utf-8")
        )

    def test_exact_reviewed_artifact_is_retained_offline(self) -> None:
        expected = {item["path"] for item in self.review["expected_files"]}
        actual = {
            str(path.relative_to(VINTAGE))
            for path in VINTAGE.rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual, expected)
        for item in self.review["expected_files"]:
            path = VINTAGE / item["path"]
            self.assertEqual(path.stat().st_size, item["bytes"])
            self.assertEqual(sha256(path), item["sha256"])

    def test_manifest_preserves_four_independent_source_lineages(self) -> None:
        self.assertEqual(
            self.manifest["snapshot_id"],
            "corporate-investment-source-family-vintage-2026-09-19",
        )
        self.assertEqual(
            self.manifest["materializer_script_sha256"],
            "3e024fd8989d569e601e1a412df1ac2e278b2b0b55c81022129d746300508f5e",
        )
        outputs = {
            item["source_id"]: item
            for item in self.manifest["normalized_outputs"]
        }
        self.assertEqual(outputs["nfc_gfcf"]["rows"], 109)
        self.assertEqual(outputs["nfc_investment_grants"]["rows"], 109)
        self.assertEqual(outputs["nfc_investment_rate"]["rows"], 106)
        self.assertEqual(
            outputs["nfc_new_business_lending_rate"]["rows"],
            88,
        )
        self.assertTrue(
            all(item["transformations"] == [] for item in outputs.values())
        )

    def test_vintage_does_not_choose_target_or_authorize_estimation(self) -> None:
        hard = self.manifest["hard_boundaries"]
        self.assertTrue(hard["no_target_choice"])
        self.assertTrue(hard["no_demand_proxy_choice"])
        self.assertTrue(hard["no_rate_aggregation_choice"])
        self.assertTrue(hard["no_real_rate_deflator_choice"])
        self.assertTrue(hard["no_eu_origin_inference"])
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertTrue(hard["no_behavioural_closure_change"])


if __name__ == "__main__":
    unittest.main()
