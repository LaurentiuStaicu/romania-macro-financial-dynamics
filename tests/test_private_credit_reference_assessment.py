from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class PrivateCreditReferenceAssessmentTests(unittest.TestCase):
    def test_retained_snapshot_matches_assessment_and_reference_registry(self) -> None:
        assessment = load(
            "model/dynamics/private_credit_reference_assessment.json"
        )
        snapshot = load(
            "model/dynamics/private_credit_reference_snapshot.json"
        )
        references = load("model/dynamics/reference_modes.json")

        self.assertEqual(
            assessment["verdict"],
            "PROMOTE_BOTH_TO_OBSERVED_SERIES_AVAILABLE",
        )
        self.assertEqual(
            assessment["source_basis"]["workflow_artifact_sha256"],
            snapshot["provenance"]["workflow_artifact_sha256"],
        )
        self.assertEqual(
            snapshot["provenance"]["audit_report_sha256"],
            "b50ecb53130f0a9bd5731487737d14d70a66ebf6688202cf856e5b995630ebdd",
        )

        self.assertEqual(snapshot["coverage"]["credit_stock"]["observations"], 260)
        self.assertEqual(snapshot["coverage"]["credit_flow"]["observations"], 259)
        self.assertEqual(len(snapshot["benchmark_2025"]["credit_stock"]), 12)
        self.assertEqual(len(snapshot["benchmark_2025"]["credit_flow"]), 12)

        modes = {item["id"]: item for item in references["modes"]}
        for mode_id in ("credit_stock", "credit_flow"):
            mode = modes[mode_id]
            self.assertEqual(mode["status"], "OBSERVED_SERIES_AVAILABLE")
            self.assertEqual(mode["time_resolution"], "monthly")
            self.assertEqual(
                mode["assessment"],
                "model/dynamics/private_credit_reference_assessment.json",
            )
            self.assertEqual(
                mode["retained_snapshot"],
                "model/dynamics/private_credit_reference_snapshot.json",
            )

    def test_flow_is_direct_transaction_measure_and_no_feedback_is_activated(self) -> None:
        snapshot = load(
            "model/dynamics/private_credit_reference_snapshot.json"
        )
        feedback = load("model/dynamics/feedback_registry.json")
        model = load("model/registries/model_contract.json")

        self.assertFalse(snapshot["hard_boundary"]["stock_difference_used_as_flow"])
        self.assertFalse(snapshot["hard_boundary"]["gross_new_lending_substitution"])
        self.assertFalse(snapshot["hard_boundary"]["other_financial_sectors_included"])
        self.assertFalse(snapshot["hard_boundary"]["accounting_spine_changed"])

        loops = {item["id"]: item for item in feedback["loops"]}
        self.assertFalse(loops["bank_credit_balance_sheet_loop"]["quantitatively_active"])
        self.assertFalse(loops["monetary_credit_transmission_loop"]["quantitatively_active"])
        self.assertFalse(model["dynamic_core"]["behavioural_closure_active"])
        self.assertGreaterEqual(model["dynamic_core"]["reference_mode_ready_count"], 7)


if __name__ == "__main__":
    unittest.main()
