from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.audit_system_dynamics_conformity import (
    REQUIRED_REFERENCE_MODES,
    implied_loop_polarity,
    path_is_closed,
    path_is_contiguous,
    empirical_activation_governance,
    reference_mode_readiness,
    validation_recovery_registry_alignment,
)

ROOT = Path(__file__).resolve().parents[1]


class SystemDynamicsConformityTests(unittest.TestCase):
    def test_conformity_gate_passes(self) -> None:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "audit_system_dynamics_conformity.py"),
            ],
            cwd=ROOT,
            check=True,
        )

    def test_loop_polarity_is_computed_from_signed_path(self) -> None:
        reinforcing = [
            {"from": "a", "to": "b", "sign": "+"},
            {"from": "b", "to": "a", "sign": "+_candidate"},
        ]
        balancing = [
            {"from": "a", "to": "b", "sign": "+"},
            {"from": "b", "to": "c", "sign": "-_candidate"},
            {"from": "c", "to": "a", "sign": "+"},
        ]
        self.assertEqual(implied_loop_polarity(reinforcing), "reinforcing")
        self.assertEqual(implied_loop_polarity(balancing), "balancing")

    def test_open_chain_is_not_a_loop(self) -> None:
        path = [
            {"from": "a", "to": "b", "sign": "+"},
            {"from": "b", "to": "c", "sign": "+"},
        ]
        self.assertTrue(path_is_contiguous(path))
        self.assertFalse(path_is_closed(path))
        with self.assertRaises(RuntimeError):
            implied_loop_polarity(path)


    def test_reference_mode_readiness_is_explicitly_blocked(self) -> None:
        references = json.loads(
            (
                ROOT / "model" / "dynamics" / "reference_modes.json"
            ).read_text(encoding="utf-8")
        )
        readiness = reference_mode_readiness(
            references,
            REQUIRED_REFERENCE_MODES,
        )
        self.assertEqual(readiness["status"], "BLOCKED")
        self.assertEqual(
            set(readiness["ready_modes"]),
            {
                "policy_rate",
                "household_lending_rate",
                "nfc_lending_rate",
                "government_debt_stock",
                "government_interest_burden",
            },
        )
        self.assertEqual(
            set(readiness["blocking_modes"]),
            {
                "credit_stock",
                "credit_flow",
                "government_refinancing_need",
                "government_effective_interest_rate",
                "sectoral_financial_positions",
            },
        )

    def test_qualitative_reference_exception_requires_explicit_basis(self) -> None:
        references = json.loads(
            (
                ROOT / "model" / "dynamics" / "reference_modes.json"
            ).read_text(encoding="utf-8")
        )
        mutated = copy.deepcopy(references)
        mutated["closure_readiness_policy"][
            "current_qualitative_exceptions"
        ] = [{"id": "credit_stock"}]
        with self.assertRaises(RuntimeError):
            reference_mode_readiness(
                mutated,
                REQUIRED_REFERENCE_MODES,
            )


    def test_post_recovery_empirical_activation_is_closed(self) -> None:
        contract = json.loads(
            (
                ROOT / "model" / "empirical_dynamics" / "contract.json"
            ).read_text(encoding="utf-8")
        )
        registry = json.loads(
            (
                ROOT / "model" / "empirical_dynamics"
                / "mechanism_registry.json"
            ).read_text(encoding="utf-8")
        )
        disposition = json.loads(
            (
                ROOT / "model" / "calibration_validation"
                / "validation_recovery_disposition.json"
            ).read_text(encoding="utf-8")
        )
        result = empirical_activation_governance(
            contract,
            registry,
            disposition,
        )
        self.assertFalse(result["active_calibration_cycle_open"])
        self.assertEqual(result["activated_mechanisms"], [])
        self.assertEqual(
            result["current_status_of_previous_admissions"],
            {
                "government_refinancing_effective_rate": "DEFERRED",
                "monetary_policy_lending_rate_pass_through": "CANDIDATE",
            },
        )
        self.assertEqual(result["central_feedback_mechanisms"], [])
        self.assertEqual(
            result["validated_reference_behavioural_mechanisms"],
            0,
        )

    def test_closed_cycle_rejects_stale_activated_status(self) -> None:
        contract = json.loads(
            (
                ROOT / "model" / "empirical_dynamics" / "contract.json"
            ).read_text(encoding="utf-8")
        )
        registry = json.loads(
            (
                ROOT / "model" / "empirical_dynamics"
                / "mechanism_registry.json"
            ).read_text(encoding="utf-8")
        )
        disposition = json.loads(
            (
                ROOT / "model" / "calibration_validation"
                / "validation_recovery_disposition.json"
            ).read_text(encoding="utf-8")
        )
        mutated_contract = copy.deepcopy(contract)
        mutated_registry = copy.deepcopy(registry)
        mutated_contract["activated_mechanisms"] = [
            "government_refinancing_effective_rate"
        ]
        mechanism = next(
            item
            for item in mutated_registry["mechanisms"]
            if item["id"] == "government_refinancing_effective_rate"
        )
        mechanism["classification"] = "ACTIVATED"
        with self.assertRaises(RuntimeError):
            empirical_activation_governance(
                mutated_contract,
                mutated_registry,
                disposition,
            )


    def test_registry_matches_frozen_validation_recovery_artifacts(self) -> None:
        registry = json.loads(
            (
                ROOT / "model" / "empirical_dynamics"
                / "mechanism_registry.json"
            ).read_text(encoding="utf-8")
        )
        holdout = json.loads(
            (
                ROOT / "model" / "calibration_validation"
                / "validation_recovery_holdout.json"
            ).read_text(encoding="utf-8")
        )
        selection_freeze = json.loads(
            (
                ROOT / "model" / "calibration_validation"
                / "validation_recovery_selection_freeze.json"
            ).read_text(encoding="utf-8")
        )
        government = json.loads(
            (
                ROOT / "model" / "calibration_validation"
                / "government_repricing_ledger_assessment.json"
            ).read_text(encoding="utf-8")
        )
        result = validation_recovery_registry_alignment(
            registry,
            holdout,
            selection_freeze,
            government,
        )
        self.assertEqual(
            result["monetary_household_status"],
            "CANDIDATE",
        )
        self.assertEqual(
            result["monetary_household_candidate"],
            "delta_policy_contemporaneous",
        )
        self.assertEqual(
            result["monetary_holdout_nonzero_policy_changes"],
            0,
        )
        self.assertIsNone(result["nfc_selected_candidate"])
        self.assertFalse(result["nfc_final_holdout_opened"])
        self.assertEqual(result["government_status"], "DEFERRED")
        self.assertFalse(result["government_candidate_eligibility"])
        self.assertFalse(result["government_estimation_run"])

    def test_old_generic_monetary_form_cannot_reappear(self) -> None:
        registry = json.loads(
            (
                ROOT / "model" / "empirical_dynamics"
                / "mechanism_registry.json"
            ).read_text(encoding="utf-8")
        )
        holdout = json.loads(
            (
                ROOT / "model" / "calibration_validation"
                / "validation_recovery_holdout.json"
            ).read_text(encoding="utf-8")
        )
        selection_freeze = json.loads(
            (
                ROOT / "model" / "calibration_validation"
                / "validation_recovery_selection_freeze.json"
            ).read_text(encoding="utf-8")
        )
        government = json.loads(
            (
                ROOT / "model" / "calibration_validation"
                / "government_repricing_ledger_assessment.json"
            ).read_text(encoding="utf-8")
        )
        mutated = copy.deepcopy(registry)
        monetary = next(
            item
            for item in mutated["mechanisms"]
            if item["id"] == "monetary_policy_lending_rate_pass_through"
        )
        monetary["functional_form"] = (
            "r_lend[t] = r_lend[t-1] + lambda * "
            "(alpha + beta * policy_rate[t] - r_lend[t-1])"
        )
        with self.assertRaises(RuntimeError):
            validation_recovery_registry_alignment(
                mutated,
                holdout,
                selection_freeze,
                government,
            )


if __name__ == "__main__":
    unittest.main()
