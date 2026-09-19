from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class FiscalCapbMaterialisationExecutionReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.a = load(
            "model/registries/fiscal_capb_materialisation_execution_readiness_2026_09_19.json"
        )
        self.m = load("model/registries/model_contract.json")

    def test_live_gate_is_ready_but_not_executed(self) -> None:
        self.assertEqual(
            self.a["status"],
            "READY_FOR_MANUAL_LIVE_SOURCE_MATERIALISATION_NOT_YET_EXECUTED",
        )
        state = self.a["execution_state"]
        self.assertTrue(state["live_provider_work_manual_only"])
        self.assertTrue(state["workflow_dispatch_required"])
        self.assertFalse(state["execution_performed"])
        self.assertIsNone(state["workflow_run_id"])
        self.assertFalse(state["retained_source_vintage_created"])
        self.assertFalse(state["retained_artifact_reviewed"])

    def test_manual_gate_has_no_calibration_effect(self) -> None:
        effects = self.a["scientific_effects"]
        self.assertEqual(effects["mechanism_classification"], "DEFERRED")
        self.assertFalse(effects["active_calibration_cycle_open"])
        self.assertFalse(effects["estimation_or_refit_authorized"])
        self.assertFalse(
            effects["prior_final_evaluation_2018_2024_opening_authorized"]
        )
        self.assertFalse(effects["system_dynamics_feedback_activation"])
        self.assertFalse(effects["behavioural_closure_activation"])

    def test_model_contract_does_not_claim_autonomous_execution(self) -> None:
        stage = self.m["scientific_stage"]
        self.assertTrue(stage["selective_reopen_active"])
        self.assertIsNone(stage["active_autonomous_empirical_task"])
        self.assertEqual(
            stage["active_manual_empirical_gate"],
            "FISCAL_PRIMARY_BALANCE_CAPB_REALTIME_VINTAGE_MATERIALISATION",
        )
        self.assertEqual(
            stage["selective_reopen_execution_state"],
            "READY_MANUAL_WORKFLOW_DISPATCH_REQUIRED_NOT_EXECUTED",
        )


if __name__ == "__main__":
    unittest.main()
