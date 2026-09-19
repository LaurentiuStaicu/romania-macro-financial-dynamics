from __future__ import annotations

import csv
import json
import math
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class RemainingReferenceModeBlockerTests(unittest.TestCase):
    def test_refinancing_need_is_observed_without_activating_repricing(self) -> None:
        references = load("model/dynamics/reference_modes.json")
        assessment = load(
            "model/dynamics/government_refinancing_need_reference_assessment.json"
        )
        promotion = load(
            "model/dynamics/government_refinancing_need_promotion_assessment.json"
        )
        mechanisms = load("model/empirical_dynamics/mechanism_registry.json")

        mode = next(
            item for item in references["modes"]
            if item["id"] == "government_refinancing_need"
        )
        mechanism = next(
            item for item in mechanisms["mechanisms"]
            if item["id"] == "government_refinancing_effective_rate"
        )

        self.assertEqual(mode["status"], "OBSERVED_SERIES_AVAILABLE")
        self.assertEqual(
            assessment["verdict"],
            "OBSERVED_SERIES_AVAILABLE_AFTER_HISTORICAL_CONTINUITY_GATE",
        )
        self.assertEqual(
            promotion["verdict"],
            "PROMOTE_TO_OBSERVED_SERIES_AVAILABLE",
        )
        self.assertEqual(
            assessment["current_observed_series"]["observation_count"],
            12,
        )
        self.assertEqual(
            assessment["current_observed_series"]["forecast_or_planned_observations"],
            0,
        )
        self.assertFalse(
            assessment["disposition"]["government_repricing_share_identified"]
        )
        self.assertEqual(mechanism["classification"], "DEFERRED")
        self.assertFalse(mechanism["central_feedback"])

    def test_partial_refinancing_series_preserves_observation_status(self) -> None:
        series_path = (
            ROOT
            / "data"
            / "processed"
            / "government_debt_refinancing_mof_2017_2023.csv"
        )
        with series_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual([row["period"] for row in rows], [str(y) for y in range(2017, 2024)])
        self.assertEqual(len(rows), 7)
        self.assertTrue(
            all(
                math.isfinite(float(row["government_debt_refinancing_bn_ron"]))
                and math.isfinite(float(row["gross_financing_need_bn_ron"]))
                for row in rows
            )
        )
        statuses = [row["observation_status"] for row in rows]
        self.assertEqual(statuses.count("FINAL_ANNUAL_REPORT"), 4)
        self.assertEqual(statuses.count("OPERATIVE_EXECUTION"), 3)
        self.assertNotIn("FORECAST", statuses)

    def test_sectoral_positions_cannot_outrun_accounting_readiness(self) -> None:
        references = load("model/dynamics/reference_modes.json")
        assessment = load(
            "model/dynamics/sectoral_financial_positions_reference_assessment.json"
        )
        accounting = load("model/accounting/accounting_readiness_gate.json")
        model = load("model/registries/model_contract.json")

        mode = next(
            item for item in references["modes"]
            if item["id"] == "sectoral_financial_positions"
        )
        expected = accounting["current_expected_state"]

        self.assertEqual(mode["status"], "PARTIAL_SERIES_AVAILABLE")
        self.assertEqual(
            assessment["verdict"],
            "BLOCKED_BY_CANONICAL_ACCOUNTING_READINESS",
        )
        self.assertEqual(
            assessment["current_state"]["canonical_incomplete_instruments"],
            expected["canonical_incomplete_instruments"],
        )
        self.assertFalse(
            expected["canonical_multi_instrument_stock_initialization_ready"]
        )
        self.assertFalse(
            expected["canonical_full_2025_stock_flow_benchmark_ready"]
        )
        self.assertFalse(
            model["dynamic_core"]["canonical_multi_instrument_stock_initialization_ready"]
        )

    def test_status_readiness_summary_is_derived_from_registry(self) -> None:
        references = load("model/dynamics/reference_modes.json")
        model = load("model/registries/model_contract.json")
        status = (ROOT / "STATUS.md").read_text(encoding="utf-8")

        ready_statuses = set(
            references["closure_readiness_policy"][
                "ready_statuses_for_integrated_quantitative_closure"
            ]
        )
        required = int(model["dynamic_core"]["reference_mode_required_count"])
        ready = sum(
            1
            for item in references["modes"]
            if item["id"] in {
                "policy_rate",
                "household_lending_rate",
                "nfc_lending_rate",
                "credit_stock",
                "credit_flow",
                "government_debt_stock",
                "government_interest_burden",
                "government_refinancing_need",
                "government_effective_interest_rate",
                "sectoral_financial_positions",
            }
            and item["status"] in ready_statuses
        )
        blockers = required - ready
        match = re.search(
            r"Canonical reference-mode readiness: \*\*(\d+)/(\d+) observed; "
            r"(\d+) blockers?\*\*\.",
            status,
        )
        self.assertIsNotNone(match)
        self.assertEqual(
            tuple(map(int, match.groups())),
            (ready, required, blockers),
        )
        self.assertEqual(
            model["dynamic_core"]["reference_mode_ready_count"],
            ready,
        )


    def test_live_reference_refresh_workflows_are_manual_only(self) -> None:
        workflow_paths = [
            ".github/workflows/private-credit-reference-audit.yml",
            ".github/workflows/government-interest-burden-reference-audit.yml",
            ".github/workflows/government-debt-stock-reference-audit.yml",
        ]
        for relative in workflow_paths:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("workflow_dispatch:", text, relative)
            self.assertNotIn("pull_request:", text, relative)
            self.assertIn(
                "retained snapshots/assessments",
                text,
                relative,
            )



    def test_external_refinancing_screening_strengthens_but_does_not_promote(self) -> None:
        assessment = load(
            "model/dynamics/government_refinancing_need_reference_assessment.json"
        )
        screening = load(
            "model/dynamics/government_refinancing_need_external_source_screening.json"
        )
        references = load("model/dynamics/reference_modes.json")

        mode = next(
            item for item in references["modes"]
            if item["id"] == "government_refinancing_need"
        )

        screening_path = (
            assessment["historical_evidence"]["external_source_screening"]
        )
        self.assertEqual(
            screening_path,
            "model/dynamics/government_refinancing_need_external_source_screening.json",
        )
        self.assertEqual(
            mode["external_source_screening"],
            screening_path,
        )
        self.assertEqual(
            screening["scientific_decision"]["verdict"],
            "NO_PROMOTION",
        )
        self.assertEqual(
            screening["scientific_decision"]["retained_status"],
            "PARTIAL_SERIES_AVAILABLE",
        )
        self.assertFalse(screening["synthesis"]["exact_machine_readable_historical_GFN_series_recovered"])
        self.assertEqual(
            screening["synthesis"]["exact_2024_IMF_actual_GFN_pct_GDP"],
            14.1,
        )
        self.assertTrue(
            screening["synthesis"]["ministry_2024_plan_values_are_revision_sensitive"]
        )
        self.assertTrue(
            screening["synthesis"]["ministry_2024_plan_values_include_prefunding"]
        )
        self.assertFalse(screening["synthesis"]["promotion_supported"])
        self.assertEqual(mode["status"], "OBSERVED_SERIES_AVAILABLE")

    def test_refinancing_promotion_preserves_proxy_and_plan_prohibitions(self) -> None:
        contract = load(
            "model/dynamics/government_refinancing_need_promotion_contract.json"
        )
        provenance = load(
            "data/provenance/government_debt_refinancing_mof_2013_2024.json"
        )
        excluded = " ".join(contract["target"]["excludes"]).lower()
        discarded_statuses = {
            item["status"] for item in provenance["discarded_candidates"]
        }

        self.assertIn("gross financing need", excluded)
        self.assertTrue(
            provenance["hard_boundaries"]["no_prefinancing_substitution"]
        )
        self.assertIn("debt maturing within one year", excluded)
        self.assertIn("refixing", excluded)
        self.assertIn("m[t]", excluded)
        self.assertIn("PROJECTION", discarded_statuses)
        self.assertIn("ESTIMATE", discarded_statuses)
        self.assertIn("PLANNED", discarded_statuses)
        self.assertIn("IN_YEAR_REVISED_PLAN", discarded_statuses)
        self.assertTrue(
            provenance["hard_boundaries"]["no_forecasts_in_canonical_series"]
        )
        self.assertTrue(
            provenance["hard_boundaries"]["no_plans_in_canonical_series"]
        )
        self.assertTrue(
            provenance["hard_boundaries"]["no_gross_financing_need_substitution"]
        )
        self.assertTrue(
            provenance["hard_boundaries"]["no_prefinancing_substitution"]
        )



    def test_sectoral_position_internal_recovery_path_is_exhausted_without_promotion(self) -> None:
        references = load("model/dynamics/reference_modes.json")
        assessment = load(
            "model/dynamics/sectoral_financial_positions_reference_assessment.json"
        )
        phase_a = load(
            "model/dynamics/sectoral_financial_positions_strict_gate_assessment.json"
        )
        phase_b = load(
            "model/dynamics/sectoral_financial_positions_aggregate_identity_assessment.json"
        )
        phase_c = load(
            "model/dynamics/sectoral_financial_positions_rounding_consistency_assessment.json"
        )
        phase_d = load(
            "model/dynamics/sectoral_financial_positions_source_discrepancy_assessment.json"
        )

        mode = next(
            item for item in references["modes"]
            if item["id"] == "sectoral_financial_positions"
        )

        self.assertEqual(mode["status"], "PARTIAL_SERIES_AVAILABLE")
        self.assertEqual(
            phase_a["verdict"],
            "STRICT_F2_F8_AGGREGATE_GATE_FAILED_NO_PROMOTION",
        )
        self.assertEqual(
            phase_b["verdict"],
            "AGGREGATE_IDENTITY_GATE_FAILED_STRICT_STOCK_RECONCILIATION_NO_PROMOTION",
        )
        self.assertEqual(
            phase_c["verdict"],
            "SOURCE_PRECISION_GATE_FAILED_NO_PROMOTION",
        )
        self.assertEqual(
            phase_d["verdict"],
            "DIAGNOSTIC_LOCALIZED_RESIDENT_SECTOR_ADDITIVITY_NO_PROMOTION",
        )
        self.assertTrue(
            phase_d["closure_of_internal_recovery_path"][
                "no_further_internal_reinterpretation_justified"
            ]
        )
        self.assertEqual(
            phase_d["disposition"]["further_internal_source_recovery"],
            "FROZEN_UNTIL_REOPEN_TRIGGER",
        )
        self.assertEqual(
            assessment["disposition"]["further_internal_source_recovery"],
            "FROZEN_UNTIL_REOPEN_TRIGGER",
        )
        self.assertEqual(
            mode["post_run_s1n_boundary_diagnostic_status"],
            "EXECUTED_NEGATIVE_NO_REOPEN_EVIDENCE",
        )
        self.assertEqual(
            mode["post_run_s1n_boundary_diagnostic_contract"],
            "model/dynamics/"
            "sectoral_financial_positions_s1n_boundary_diagnostic_contract.json",
        )
        s1n_contract = load(mode["post_run_s1n_boundary_diagnostic_contract"])
        self.assertFalse(s1n_contract["formal_reference_mode_gate"])
        self.assertEqual(
            s1n_contract["result_semantics"]["readiness_count_change"],
            0,
        )
        s1n_assessment = load(
            mode["post_run_s1n_boundary_diagnostic_assessment"]
        )
        self.assertEqual(
            s1n_assessment["verdict"],
            "EXECUTED_NEGATIVE_NO_REOPEN_EVIDENCE_FROM_S1N",
        )
        self.assertEqual(
            s1n_assessment["source_outcome"]["http_404_count"],
            8,
        )
        self.assertEqual(
            s1n_assessment["source_outcome"]["network_error_count"],
            0,
        )
        self.assertFalse(
            s1n_assessment["hard_effects"]["reference_mode_promotion"]
        )
        self.assertEqual(
            s1n_assessment["hard_effects"]["reference_mode_readiness_change"],
            0,
        )
        self.assertEqual(
            phase_d["localization"]["stock"][
                "max_absolute_total_economy_external_residual_million_RON"
            ],
            0.010000000591389835,
        )
        for item in phase_d["localization"]["stock"][
            "phase_C_failing_periods"
        ].values():
            self.assertEqual(item["dominant"], "RESIDENT_SECTOR_ADDITIVITY")



    def test_external_eurostat_probe_is_priority_discovery_only(self) -> None:
        references = load("model/dynamics/reference_modes.json")
        assessment = load(
            "model/dynamics/sectoral_financial_positions_reference_assessment.json"
        )
        screening = load(
            "model/dynamics/sectoral_financial_positions_external_source_screening.json"
        )
        contract = load(
            "model/dynamics/sectoral_financial_positions_eurostat_counterpart_probe_contract.json"
        )
        mode = next(
            item for item in references["modes"]
            if item["id"] == "sectoral_financial_positions"
        )

        self.assertEqual(mode["status"], "PARTIAL_SERIES_AVAILABLE")
        self.assertEqual(
            mode["eurostat_counterpart_discovery_probe_status"],
            "EXECUTED_PASS_SEMANTIC_REVIEW_FAIL_INSTRUMENT_SCOPE",
        )
        self.assertEqual(
            mode["eurostat_counterpart_discovery_probe_effect"],
            "NO_REOPEN; discovery confirmed Romania counterpart data, but frozen semantic review failed because the public instrument set does not cover complete RMD F2-F8.",
        )
        self.assertTrue(
            screening["decision"]["eurostat_counterpart_probe_justified"]
        )
        self.assertFalse(
            screening["decision"]["immediate_reference_mode_reopen_authorized"]
        )
        self.assertFalse(contract["formal_reference_mode_gate"])
        self.assertTrue(contract["hard_rules"]["no_reference_mode_promotion"])
        self.assertTrue(
            contract["hard_rules"]["no_historical_phase_A_D_reinterpretation"]
        )
        self.assertEqual(
            assessment["eurostat_counterpart_discovery_probe"]["status"],
            "EXECUTED_PASS_SEMANTIC_REVIEW_FAIL_INSTRUMENT_SCOPE",
        )
        self.assertFalse(
            assessment["eurostat_counterpart_discovery_probe"][
                "formal_reference_mode_gate"
            ]
        )
        self.assertEqual(
            assessment["eurostat_counterpart_discovery_probe"][
                "raw_response_sha256"
            ],
            "547c9e65c60900aa259ba547efb60faedbaa22e8d8a66e1caed6cbd2cbd189ae",
        )
        self.assertEqual(
            assessment["disposition"]["further_internal_source_recovery"],
            "FROZEN_UNTIL_REOPEN_TRIGGER",
        )


    def test_external_oecd_probe_is_discovery_only_and_cannot_promote(self) -> None:
        references = load("model/dynamics/reference_modes.json")
        assessment = load(
            "model/dynamics/sectoral_financial_positions_reference_assessment.json"
        )
        screening = load(
            "model/dynamics/sectoral_financial_positions_external_source_screening.json"
        )
        contract = load(
            "model/dynamics/sectoral_financial_positions_oecd_counterpart_probe_contract.json"
        )
        mode = next(
            item for item in references["modes"]
            if item["id"] == "sectoral_financial_positions"
        )

        self.assertEqual(mode["status"], "PARTIAL_SERIES_AVAILABLE")
        self.assertEqual(
            mode["external_source_screening"],
            "model/dynamics/sectoral_financial_positions_external_source_screening.json",
        )
        self.assertEqual(
            mode["oecd_counterpart_discovery_probe_status"],
            "PREREGISTERED_MANUAL_NOT_EXECUTED",
        )
        self.assertEqual(
            mode["oecd_counterpart_discovery_probe_effect"],
            "NONE_UNTIL_RETAINED_RESULT_AND_SEPARATE_SEMANTIC_LINEAGE_REVIEW",
        )
        self.assertFalse(
            screening["decision"]["immediate_reference_mode_reopen_authorized"]
        )
        self.assertFalse(
            screening["decision"]["reference_mode_promotion_authorized"]
        )
        self.assertFalse(contract["formal_reference_mode_gate"])
        self.assertTrue(
            contract["hard_rules"]["no_reference_mode_promotion"]
        )
        self.assertTrue(
            contract["hard_rules"]["no_historical_phase_A_D_reinterpretation"]
        )
        self.assertEqual(
            assessment["oecd_counterpart_discovery_probe"]["status"],
            "PREREGISTERED_MANUAL_NOT_EXECUTED",
        )
        self.assertFalse(
            assessment["oecd_counterpart_discovery_probe"][
                "formal_reference_mode_gate"
            ]
        )
        self.assertEqual(
            assessment["disposition"]["further_internal_source_recovery"],
            "FROZEN_UNTIL_REOPEN_TRIGGER",
        )


    def test_exploratory_esa_f1_reaudit_cannot_replace_historical_phase_b(self) -> None:
        references = load("model/dynamics/reference_modes.json")
        historical = load(
            "model/dynamics/sectoral_financial_positions_aggregate_identity_assessment.json"
        )
        exploratory = load(
            "model/dynamics/sectoral_financial_positions_esa_f1_applicability_reaudit_assessment.json"
        )
        review = load(
            "model/dynamics/sectoral_financial_positions_esa_f1_applicability_review.json"
        )
        mode = next(
            item for item in references["modes"]
            if item["id"] == "sectoral_financial_positions"
        )

        self.assertEqual(mode["status"], "PARTIAL_SERIES_AVAILABLE")
        self.assertEqual(
            historical["verdict"],
            "AGGREGATE_IDENTITY_GATE_FAILED_STRICT_STOCK_RECONCILIATION_NO_PROMOTION",
        )
        self.assertEqual(
            exploratory["verdict"],
            "EXPLORATORY_ESA_F1_REAUDIT_RECONCILIATION_FAIL_NO_PROMOTION",
        )
        self.assertFalse(exploratory["formal_reference_mode_gate"])
        self.assertFalse(
            exploratory["disposition"]["historical_phase_B_reinterpreted"]
        )
        self.assertEqual(
            exploratory["disposition"]["readiness_count_change"],
            0,
        )
        self.assertEqual(
            review["exploratory_reaudit"]["formal_gate"],
            False,
        )
        self.assertEqual(
            review["exploratory_reaudit"]["result"],
            "RECONCILIATION_FAIL_NO_PROMOTION",
        )
        self.assertEqual(
            review["next_action"]["status"],
            "NO_FURTHER_INTERNAL_F1_ADAPTATION",
        )



    def test_ecb_quality_context_supports_freeze_without_changing_gate(self) -> None:
        references = load("model/dynamics/reference_modes.json")
        assessment = load(
            "model/dynamics/sectoral_financial_positions_reference_assessment.json"
        )
        context = load(
            "model/dynamics/sectoral_financial_positions_ecb_quality_context.json"
        )
        mode = next(
            item for item in references["modes"]
            if item["id"] == "sectoral_financial_positions"
        )

        expected = "model/dynamics/sectoral_financial_positions_ecb_quality_context.json"
        self.assertEqual(assessment["ecb_quality_context"], expected)
        self.assertEqual(mode["ecb_quality_context"], expected)
        self.assertEqual(mode["status"], "PARTIAL_SERIES_AVAILABLE")
        self.assertEqual(
            context["disposition"]["sectoral_financial_positions_status"],
            "PARTIAL_SERIES_AVAILABLE",
        )
        self.assertEqual(context["disposition"]["readiness_count_change"], 0)
        for value in context["hard_boundaries"].values():
            self.assertTrue(value)
        self.assertIn(
            "cannot promote",
            context["relationship_to_rmd_evidence"]["interpretation"],
        )


    def test_f1_semantics_diagnostic_rejects_zero_refinement_without_promotion(self) -> None:
        references = load("model/dynamics/reference_modes.json")
        diagnostic = load(
            "model/dynamics/sectoral_financial_positions_esa_f1_semantics_diagnostic_assessment.json"
        )
        review = load(
            "model/dynamics/sectoral_financial_positions_esa_f1_applicability_review.json"
        )
        mode = next(
            item for item in references["modes"]
            if item["id"] == "sectoral_financial_positions"
        )

        self.assertEqual(mode["status"], "PARTIAL_SERIES_AVAILABLE")
        self.assertEqual(
            diagnostic["verdict"],
            "EXPLORATORY_DIAGNOSTIC_REJECTS_RESIDENT_F1_LIABILITY_ZERO_NO_PROMOTION",
        )
        self.assertFalse(diagnostic["formal_reference_mode_gate"])
        self.assertEqual(
            diagnostic["corrected_methodological_conclusion"][
                "resident_S12_S121_F1_liability_zero_hypothesis"
            ],
            "REJECTED",
        )
        self.assertEqual(
            diagnostic["disposition"]["readiness_count_change"],
            0,
        )
        self.assertEqual(
            review["proposal_status"],
            "REJECTED_BY_PUBLISHED_QSA_SDR_LIABILITY_DIAGNOSTIC",
        )
        self.assertEqual(
            review["next_action"]["status"],
            "NO_FURTHER_INTERNAL_F1_ADAPTATION",
        )



    def test_promoted_refinancing_series_is_continuous_and_observed_only(self) -> None:
        contract = load(
            "model/dynamics/government_refinancing_need_promotion_contract.json"
        )
        provenance = load(
            "data/provenance/government_debt_refinancing_mof_2013_2024.json"
        )
        series_path = (
            ROOT
            / "data"
            / "processed"
            / "government_debt_refinancing_mof_2013_2024.csv"
        )
        with series_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual([row["period"] for row in rows], [str(y) for y in range(2013, 2025)])
        self.assertEqual(len(rows), 12)
        self.assertGreaterEqual(
            len(rows),
            contract["promotion_criteria"]["minimum_consecutive_completed_calendar_years"],
        )
        accepted = set(contract["accepted_observation_statuses"])
        self.assertTrue(all(row["observation_status"] in accepted for row in rows))
        self.assertTrue(
            all(math.isfinite(float(row["government_debt_refinancing_bn_ron"])) for row in rows)
        )
        self.assertEqual(
            provenance["coverage"]["forecast_or_planned_observations"],
            0,
        )
        self.assertEqual(provenance["definition_bridge"]["status"], "PASS")
        self.assertTrue(
            provenance["hard_boundaries"]["no_gross_financing_need_substitution"]
        )
        by_year = {row["period"]: float(row["government_debt_refinancing_bn_ron"]) for row in rows}
        self.assertEqual(by_year["2015"], 53.0256)
        self.assertEqual(by_year["2016"], 50.8751)
        self.assertEqual(by_year["2023"], 95.8347)
        self.assertEqual(by_year["2024"], 95.6546)



if __name__ == "__main__":
    unittest.main()
