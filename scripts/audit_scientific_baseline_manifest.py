from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "model" / "registries" / "scientific_baseline_manifest.json"

REQUIRED_REFERENCE_MODES = {
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

LIVE_MANUAL_WORKFLOWS = [
    ".github/workflows/private-credit-reference-audit.yml",
    ".github/workflows/government-interest-burden-reference-audit.yml",
    ".github/workflows/government-debt-stock-reference-audit.yml",
    ".github/workflows/provenance-audit.yml",
    ".github/workflows/f4-exact-complement-rank-audit.yml",
    ".github/workflows/f5-equity-subcomponent-bridge-audit.yml",
    ".github/workflows/f7-financial-derivatives-coverage-audit.yml",
    ".github/workflows/f8-other-accounts-coverage-audit.yml",
    ".github/workflows/sectoral-financial-positions-reference-audit.yml",
    ".github/workflows/sectoral-financial-positions-aggregate-identity-audit.yml",
    ".github/workflows/sectoral-financial-positions-rounding-consistency-audit.yml",
    ".github/workflows/sectoral-financial-positions-source-discrepancy-audit.yml",
    ".github/workflows/sectoral-financial-positions-esa-f1-applicability-reaudit.yml",
    ".github/workflows/sectoral-financial-positions-s1n-boundary-diagnostic.yml",
    ".github/workflows/sectoral-financial-positions-oecd-counterpart-probe.yml",
    ".github/workflows/sectoral-financial-positions-eurostat-counterpart-probe.yml",
]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    state = manifest["canonical_state"]

    model = load("model/registries/model_contract.json")
    reset = load("model/registries/reset_integrity_contract.json")
    accounting = load("model/accounting/accounting_readiness_gate.json")
    reopen = load("model/accounting/reopen_conditions_registry.json")
    sd = load("model/dynamics/system_dynamics_conformity_gate.json")
    refs = load("model/dynamics/reference_modes.json")
    sectoral_external_screening = load(
        "model/dynamics/sectoral_financial_positions_external_source_screening.json"
    )
    reference_mode_terminal = load(
        "model/dynamics/reference_mode_recovery_terminal_assessment.json"
    )
    bnr_cnf_screening = load(
        "model/dynamics/sectoral_financial_positions_bnr_cnf_source_screening.json"
    )
    bnr_quarterly_s13_screening = load(
        "model/dynamics/sectoral_financial_positions_bnr_quarterly_s13_source_screening.json"
    )
    empirical = load("model/empirical_dynamics/contract.json")
    mechanisms = load("model/empirical_dynamics/mechanism_registry.json")
    readiness = load(
        "model/calibration_validation/mechanism_source_readiness.json"
    )
    mechanism_reopen = load(
        "model/calibration_validation/mechanism_reopen_conditions_registry.json"
    )
    disposition = load(
        "model/calibration_validation/validation_recovery_disposition.json"
    )
    prospective_contract = load(
        "model/calibration_validation/prospective_monetary_confirmation_contract.json"
    )
    prospective_status = load(
        "model/calibration_validation/prospective_monetary_confirmation_status.json"
    )
    stage_terminal = load(
        "model/registries/validation_recovery_stage_terminal_assessment.json"
    )

    # Authority paths must exist and the manifest must be registered centrally.
    for label, relative in manifest["authority"].items():
        check((ROOT / relative).is_file(), f"Missing baseline authority {label}: {relative}")
    check(
        model["scientific_baseline_manifest"]
        == "model/registries/scientific_baseline_manifest.json",
        "Model contract does not register the scientific baseline manifest",
    )
    check(
        reset["scientific_baseline_manifest"]
        == "model/registries/scientific_baseline_manifest.json",
        "Reset integrity contract does not register the scientific baseline manifest",
    )
    check(
        model["calibration_validation"]["mechanism_source_readiness"]
        == "model/calibration_validation/mechanism_source_readiness.json",
        "Model contract does not register mechanism source readiness",
    )
    check(
        model["calibration_validation"]["mechanism_reopen_conditions_registry"]
        == "model/calibration_validation/mechanism_reopen_conditions_registry.json",
        "Model contract does not register mechanism reopen governance",
    )
    check(
        model["dynamic_core"]["reference_mode_recovery_terminal_assessment"]
        == "model/dynamics/reference_mode_recovery_terminal_assessment.json",
        "Model contract does not register terminal reference-mode recovery assessment",
    )
    check(
        model["dynamic_core"]["reference_mode_recovery_stage_status"]
        == reference_mode_terminal["status"],
        "Model contract reference-mode recovery stage status is stale",
    )
    check(
        model["scientific_stage"]["terminal_assessment"]
        == "model/registries/validation_recovery_stage_terminal_assessment.json",
        "Model contract does not register terminal validation-recovery stage",
    )
    check(
        model["scientific_stage"]["status"] == stage_terminal["status"],
        "Model contract scientific-stage status is stale",
    )
    check(
        model["scientific_stage"]["next_operational_state"]
        == stage_terminal["next_operational_state"]["id"],
        "Model contract scientific-stage next state is stale",
    )
    check(
        model["scientific_stage"]["model_complete"] is False,
        "Terminal recovery stage may not claim model completion",
    )
    check(
        model["scientific_stage"]["release_ready"] is False,
        "Terminal recovery stage may not claim release readiness",
    )

    # Accounting state is derived from the canonical accounting gate.
    expected = accounting["current_expected_state"]
    acc = state["accounting"]
    check(
        set(acc["complete_stock_and_flow_instruments"])
        == set(expected["canonical_complete_stock_and_flow_instruments"]),
        "Baseline complete accounting instruments are stale",
    )
    check(
        set(acc["incomplete_instruments"])
        == set(expected["canonical_incomplete_instruments"]),
        "Baseline incomplete accounting instruments are stale",
    )
    check(
        acc["multi_instrument_stock_initialization_ready"]
        is expected["canonical_multi_instrument_stock_initialization_ready"],
        "Baseline stock-initialization readiness is stale",
    )
    check(
        acc["full_2025_stock_flow_benchmark_ready"]
        is expected["canonical_full_2025_stock_flow_benchmark_ready"],
        "Baseline full benchmark readiness is stale",
    )
    check(
        set(reopen["current_incomplete_instruments"])
        == set(acc["incomplete_instruments"]),
        "Accounting reopen registry disagrees with scientific baseline",
    )

    # Reference-mode state is derived from registry vocabulary/policy.
    by_id = {item["id"]: item for item in refs["modes"]}
    check(
        REQUIRED_REFERENCE_MODES <= set(by_id),
        "Reference-mode registry lacks a required baseline mode",
    )
    ready_statuses = set(
        refs["closure_readiness_policy"][
            "ready_statuses_for_integrated_quantitative_closure"
        ]
    )
    ready = sorted(
        mode_id
        for mode_id in REQUIRED_REFERENCE_MODES
        if by_id[mode_id]["status"] in ready_statuses
    )
    blockers = sorted(REQUIRED_REFERENCE_MODES - set(ready))
    ref_state = state["reference_modes"]
    check(ref_state["required_count"] == len(REQUIRED_REFERENCE_MODES), "Baseline reference required count is stale")
    check(ref_state["ready_count"] == len(ready), "Baseline reference ready count is stale")
    check(set(ref_state["ready"]) == set(ready), "Baseline ready reference modes are stale")
    check(set(ref_state["blockers"]) == set(blockers), "Baseline reference blockers are stale")
    check(ref_state["closure_ready"] is (not blockers), "Baseline reference closure flag is stale")
    check(model["dynamic_core"]["reference_mode_ready_count"] == len(ready), "Model reference ready count disagrees with baseline")
    check(model["dynamic_core"]["reference_mode_required_count"] == len(REQUIRED_REFERENCE_MODES), "Model reference required count disagrees with baseline")
    check(
        ref_state["recovery_stage_status"] == reference_mode_terminal["status"],
        "Baseline reference-mode recovery stage status is stale",
    )
    check(
        ref_state["recovery_substage_complete"]
        is reference_mode_terminal["disposition"]["reference_mode_recovery_substage_complete"],
        "Baseline reference-mode recovery completion flag is stale",
    )
    check(
        ref_state["next_operational_state"]
        == reference_mode_terminal["disposition"]["next_operational_state"],
        "Baseline reference-mode next operational state is stale",
    )
    check(
        reference_mode_terminal["required_reference_modes"] == len(REQUIRED_REFERENCE_MODES),
        "Terminal assessment reference-mode required count is stale",
    )
    check(
        reference_mode_terminal["ready_reference_modes"] == len(ready),
        "Terminal assessment ready reference-mode count is stale",
    )
    check(
        reference_mode_terminal["blocker_count"] == len(blockers),
        "Terminal assessment blocker count is stale",
    )
    check(
        reference_mode_terminal["disposition"]["integrated_reference_mode_closure_ready"]
        is (not blockers),
        "Terminal assessment closure-readiness flag is stale",
    )

    sectoral_mode = by_id["sectoral_financial_positions"]
    external_decision = sectoral_external_screening["decision"]
    check(
        ref_state["external_counterpart_screening_state"]
        == external_decision["external_counterpart_recovery_state"],
        "Baseline external counterpart screening state is stale",
    )
    check(
        ref_state["final_blocker_public_source_completion_status"]
        == external_decision["current_public_source_completion_status"],
        "Baseline final blocker public-source completion status is stale",
    )
    check(
        reference_mode_terminal["blocker"]["current_public_source_completion_status"]
        == external_decision["current_public_source_completion_status"],
        "Terminal reference-mode blocker source-completion status is stale",
    )
    check(
        bnr_cnf_screening["verdict"]
        == "OFFICIAL_BNR_SEMANTIC_COUNTERPART_STOCK_EVIDENCE_FOUND_BUT_FREQUENCY_AND_TRANSACTION_HISTORY_FAIL_NO_REOPEN_NO_PROMOTION",
        "BNR CNF screening verdict is stale",
    )
    check(
        bnr_cnf_screening["disposition"]["current_readiness"] == "9/10",
        "BNR CNF screening may not change reference-mode readiness",
    )
    check(
        bnr_cnf_screening["disposition"]["quarterly_boundary_change_authorized"] is False,
        "BNR annual CNF evidence may not relax the quarterly boundary",
    )
    check(
        bnr_quarterly_s13_screening["verdict"]
        == "OFFICIAL_QUARTERLY_S13_FINANCIAL_ACCOUNTS_CONFIRMED_FREQUENCY_PASS_SECTOR_COUNTERPART_CONSOLIDATION_FAIL_NO_REOPEN",
        "BNR quarterly S13 screening verdict is stale",
    )
    check(
        bnr_quarterly_s13_screening["confirmed_semantics"]["quarterly_history_available"] is True,
        "BNR quarterly S13 source must retain its quarterly-history evidence",
    )
    check(
        bnr_quarterly_s13_screening["frozen_rmd_boundary_comparison"]["frequency_pass"] is True,
        "BNR quarterly S13 frequency evidence is stale",
    )
    check(
        bnr_quarterly_s13_screening["frozen_rmd_boundary_comparison"]["sector_scope_pass"] is False,
        "BNR quarterly S13 may not satisfy the full RMD sector boundary",
    )
    check(
        bnr_quarterly_s13_screening["frozen_rmd_boundary_comparison"]["counterpart_structure_pass"] is False,
        "BNR quarterly S13 may not satisfy the full RMD counterpart boundary",
    )
    check(
        bnr_quarterly_s13_screening["frozen_rmd_boundary_comparison"]["consolidation_pass"] is False,
        "BNR quarterly S13 may not satisfy the non-consolidated RMD boundary",
    )
    check(
        ref_state[
            "sectoral_financial_positions_external_counterpart_recovery_state"
        ]
        == sectoral_mode["external_counterpart_recovery_state"],
        "Baseline sectoral-position external reopen policy is stale",
    )
    check(
        external_decision["discovery_priority"] == [],
        "Exhausted external counterpart screening still has an active discovery priority",
    )
    check(
        external_decision["eurostat_exact_historical_extraction_authorized"]
        is False,
        "Eurostat historical extraction must remain unauthorized",
    )
    check(
        external_decision["oecd_exact_historical_extraction_authorized"]
        is False,
        "OECD historical extraction must remain unauthorized",
    )
    check(
        ref_state["external_counterpart_exact_historical_extraction_authorized"]
        is False,
        "Baseline may not authorize exact historical extraction from failed semantic gates",
    )

    # SD topology and closure state.
    sd_state = state["system_dynamics"]
    check(
        sd_state["complete_endogenous_system_dynamics_model"]
        is model["dynamic_core"]["complete_endogenous_system_dynamics_model"],
        "Baseline complete-SD claim is stale",
    )
    check(
        sd_state["behavioural_closure_active"]
        is model["dynamic_core"]["behavioural_closure_active"],
        "Baseline behavioural closure state is stale",
    )
    check(
        set(sd_state["closed_candidate_feedback_loops"])
        == set(sd["feedback_topology_gate"]["closed_loop_candidates"]),
        "Baseline closed feedback candidates are stale",
    )
    check(
        set(sd_state["open_candidate_feedback_chains"])
        == set(sd["feedback_topology_gate"]["open_feedback_chains"]),
        "Baseline open feedback chains are stale",
    )

    # Empirical mechanism/validation state.
    mechanism_by_id = {item["id"]: item for item in mechanisms["mechanisms"]}
    validation = state["empirical_validation"]
    check(
        validation["active_calibration_cycle_open"]
        is empirical["post_validation_disposition"]["active_calibration_cycle_open"],
        "Baseline active calibration-cycle state is stale",
    )
    check(
        validation["activated_mechanisms_count"]
        == len(empirical["activated_mechanisms"]),
        "Baseline activated-mechanism count is stale",
    )
    check(
        validation["validated_reference_behavioural_mechanisms"]
        == disposition["validated_reference_behavioural_mechanisms"],
        "Baseline validated-mechanism count is stale",
    )
    check(
        validation["monetary_pass_through_status"]
        == mechanism_by_id["monetary_policy_lending_rate_pass_through"]["classification"],
        "Baseline monetary mechanism status is stale",
    )
    monetary = mechanism_by_id["monetary_policy_lending_rate_pass_through"]
    check(
        monetary["prospective_confirmation"]["contract"]
        == "model/calibration_validation/prospective_monetary_confirmation_contract.json",
        "Monetary candidate is not bound to the prospective confirmation contract",
    )
    check(
        monetary["prospective_confirmation"]["status"]
        == "model/calibration_validation/prospective_monetary_confirmation_status.json",
        "Monetary candidate is not bound to prospective confirmation status",
    )
    check(
        monetary["prospective_confirmation"]["current_gate_status"]
        == prospective_status["identification_gate"]["status"],
        "Monetary candidate prospective gate status is stale",
    )
    check(
        validation["government_refinancing_effective_rate_status"]
        == mechanism_by_id["government_refinancing_effective_rate"]["classification"],
        "Baseline government mechanism status is stale",
    )
    check(
        validation["prospective_confirmation_status"]
        == prospective_status["identification_gate"]["status"],
        "Baseline prospective-confirmation status is stale",
    )
    check(
        prospective_status["contract"]
        == "model/calibration_validation/prospective_monetary_confirmation_contract.json",
        "Prospective status is not governed by the registered contract",
    )
    check(
        prospective_contract["hard_rules"]["do_not_change_frozen_beta"] is True,
        "Prospective baseline requires frozen beta",
    )

    # Post-screening mechanism readiness is derived from the registry/readiness map.
    readiness_state = state["mechanism_readiness"]
    non_rejected = [
        item
        for item in mechanisms["mechanisms"]
        if item["classification"] != "REJECTED"
    ]
    non_rejected_ids = {item["id"] for item in non_rejected}
    readiness_entries = readiness["mechanisms"]
    readiness_ids = [item["id"] for item in readiness_entries]
    check(
        len(readiness_ids) == len(set(readiness_ids)),
        "Mechanism readiness contains duplicate mechanism IDs",
    )
    check(
        set(readiness_ids) == non_rejected_ids,
        "Mechanism readiness coverage is not exactly the non-rejected registry",
    )

    reopen_entries = mechanism_reopen["mechanisms"]
    check(
        set(reopen_entries) == non_rejected_ids,
        "Mechanism reopen registry coverage is not exactly the non-rejected registry",
    )
    check(
        readiness["mechanism_reopen_conditions_registry"]
        == "model/calibration_validation/mechanism_reopen_conditions_registry.json",
        "Mechanism readiness does not register the canonical reopen-condition registry",
    )
    check(
        readiness["current_next_step"]["reopen_conditions_registry"]
        == "model/calibration_validation/mechanism_reopen_conditions_registry.json",
        "Closed scientific-baseline next step is not bound to the reopen-condition registry",
    )
    source_by_id = {item["id"]: item for item in readiness_entries}
    for mechanism_id, reopen_entry in reopen_entries.items():
        source_entry = source_by_id[mechanism_id]
        check(
            reopen_entry["classification"] == source_entry["classification"],
            f"Mechanism reopen classification is stale: {mechanism_id}",
        )
        check(
            reopen_entry["source_readiness"] == source_entry["source_readiness"],
            f"Mechanism reopen source-readiness state is stale: {mechanism_id}",
        )
        evidence = reopen_entry["governing_evidence"]
        check(
            isinstance(evidence, list) and bool(evidence),
            f"Mechanism reopen entry lacks governing evidence: {mechanism_id}",
        )
        for relative in evidence:
            check(
                (ROOT / relative).is_file(),
                f"Mechanism reopen evidence path is missing for {mechanism_id}: {relative}",
            )
        reopen_when = reopen_entry["reopen_when"]
        check(
            (isinstance(reopen_when, str) and bool(reopen_when.strip()))
            or (
                isinstance(reopen_when, list)
                and bool(reopen_when)
                and all(isinstance(x, str) and x.strip() for x in reopen_when)
            ),
            f"Mechanism reopen trigger is empty: {mechanism_id}",
        )
        non_reopen = reopen_entry["evidence_that_does_not_reopen"]
        check(
            isinstance(non_reopen, list)
            and bool(non_reopen)
            and all(isinstance(x, str) and x.strip() for x in non_reopen),
            f"Mechanism non-reopen boundary is empty: {mechanism_id}",
        )
    check(
        readiness_state["non_rejected_mechanism_count"] == len(non_rejected),
        "Baseline non-rejected mechanism count is stale",
    )
    check(
        readiness_state["readiness_entry_count"] == len(readiness_entries),
        "Baseline readiness-entry count is stale",
    )
    check(
        readiness_state["reopen_registry_entry_count"] == len(reopen_entries),
        "Baseline reopen-registry entry count is stale",
    )
    check(
        readiness_state["all_reopen_conditions_registered"] is True,
        "Baseline must require reopen conditions for every mechanism",
    )
    check(
        readiness_state["reopen_governance_state"]
        == "DECLARED_TRIGGER_REQUIRED_NO_AUTOMATIC_ESTIMATION",
        "Baseline reopen-governance state is stale",
    )

    classification_counts: dict[str, int] = {
        "CANDIDATE": 0,
        "DEFERRED": 0,
        "ACTIVATED": 0,
    }
    for item in non_rejected:
        classification = item["classification"]
        check(
            classification in classification_counts,
            f"Unexpected non-rejected classification: {classification}",
        )
        classification_counts[classification] += 1
    check(
        readiness_state["classification_counts"] == classification_counts,
        "Baseline mechanism classification counts are stale",
    )

    estimation_allowed = [
        item["id"]
        for item in readiness_entries
        if item["estimation_or_refit_allowed"]
    ]
    check(
        readiness_state["estimation_or_refit_allowed_count"]
        == len(estimation_allowed),
        "Baseline estimation/refit authorization count is stale",
    )
    check(
        readiness["global_state"]["active_calibration_cycle_open"]
        is readiness_state["calibration_cycle_open"],
        "Baseline calibration-cycle flag disagrees with readiness registry",
    )
    if not readiness_state["calibration_cycle_open"]:
        check(
            not estimation_allowed,
            "Closed calibration cycle contains estimation/refit authorization",
        )

    priority_counts: dict[str, int] = {}
    for item in readiness_entries:
        group = item["priority_group"]
        priority_counts[group] = priority_counts.get(group, 0) + 1
    check(
        readiness_state["priority_group_counts"] == priority_counts,
        "Baseline readiness priority-group counts are stale",
    )
    check(
        readiness["current_next_step"]["mechanism_id"] == "SCIENTIFIC_BASELINE",
        "Post-screening queue has not advanced to scientific-baseline consolidation",
    )
    check(
        readiness["current_next_step"]["calibration_cycle_open"] is False,
        "Scientific-baseline queue state may not open calibration",
    )
    check(
        readiness_state["current_empirical_queue_state"]
        == "ALL_REGISTERED_MECHANISMS_FROZEN_WAITING_OR_EXPLICITLY_BLOCKED",
        "Baseline empirical queue-state label is stale",
    )
    check(
        all(item["priority_group"] for item in readiness_entries),
        "A mechanism readiness entry lacks an explicit priority/reopen group",
    )
    reopen_governance = mechanism_reopen["governance"]
    check(
        mechanism_reopen["current_baseline_action"]
        == readiness["current_next_step"]["action"],
        "Reopen registry baseline action disagrees with source readiness",
    )
    check(
        mechanism_reopen["current_active_calibration_cycle_open"] is False,
        "Reopen registry may not open calibration at the closed baseline",
    )
    check(
        mechanism_reopen["current_validated_reference_behavioural_mechanisms"] == 0,
        "Reopen registry may not alter validated-mechanism count",
    )
    check(
        reopen_governance["reopen_authorizes_only_the_declared_next_gate"] is True,
        "Reopen registry must constrain reopening to the declared next gate",
    )
    check(
        reopen_governance["reopen_does_not_authorize_automatic_estimation_or_refit"] is True,
        "Reopen registry may not authorize automatic estimation/refit",
    )
    check(
        reopen_governance["reopen_does_not_activate_system_dynamics_feedback"] is True,
        "Reopen registry may not activate System Dynamics feedback",
    )
    check(
        reopen_governance["reopen_does_not_activate_behavioural_closure"] is True,
        "Reopen registry may not activate behavioural closure",
    )

    # Overall validation-recovery stage is terminal only at an evidence-triggered hold.
    stage_state = state["scientific_stage"]
    check(
        stage_state["name"] == stage_terminal["stage_name"],
        "Baseline scientific-stage name is stale",
    )
    check(
        stage_state["status"] == stage_terminal["status"],
        "Baseline scientific-stage status is stale",
    )
    check(
        stage_state["next_operational_state"]
        == stage_terminal["next_operational_state"]["id"],
        "Baseline scientific-stage next operational state is stale",
    )
    check(
        stage_state["active_autonomous_empirical_task"]
        == stage_terminal["next_operational_state"]["active_autonomous_empirical_task"],
        "Baseline active autonomous empirical task is stale",
    )
    check(stage_state["model_complete"] is False, "Stage completion may not imply model completion")
    check(stage_state["release_ready"] is False, "Stage completion may not imply release readiness")

    for label, relative in stage_terminal["authorities"].items():
        check(
            (ROOT / relative).is_file(),
            f"Terminal stage authority is missing {label}: {relative}",
        )

    terminal_accounting = stage_terminal["terminal_state"]["accounting"]
    check(
        set(terminal_accounting["canonical_complete_stock_and_flow_instruments"])
        == set(acc["complete_stock_and_flow_instruments"]),
        "Terminal stage accounting-complete instruments are stale",
    )
    check(
        set(terminal_accounting["incomplete_or_partial_instruments"])
        == set(acc["incomplete_instruments"]),
        "Terminal stage accounting-incomplete instruments are stale",
    )
    check(
        terminal_accounting["full_2025_stock_flow_benchmark_ready"]
        is acc["full_2025_stock_flow_benchmark_ready"],
        "Terminal stage accounting benchmark readiness is stale",
    )
    check(
        terminal_accounting["active_unconditional_recovery_task_remains"] is False,
        "Terminal stage may not retain an unconditional accounting recovery task",
    )

    terminal_refs = stage_terminal["terminal_state"]["reference_modes"]
    check(terminal_refs["required"] == ref_state["required_count"], "Terminal stage reference required count is stale")
    check(terminal_refs["ready"] == ref_state["ready_count"], "Terminal stage reference ready count is stale")
    check(
        terminal_refs["blocker"] in ref_state["blockers"],
        "Terminal stage reference blocker is stale",
    )
    check(
        terminal_refs["integrated_closure_ready"] is ref_state["closure_ready"],
        "Terminal stage reference closure flag is stale",
    )
    check(
        terminal_refs["recovery_stage_status"] == ref_state["recovery_stage_status"],
        "Terminal stage reference recovery status is stale",
    )
    check(
        terminal_refs["active_unconditional_recovery_task_remains"] is False,
        "Terminal stage may not retain an unconditional reference-mode recovery task",
    )

    terminal_mechanisms = stage_terminal["terminal_state"]["behavioural_mechanisms"]
    check(
        terminal_mechanisms["non_rejected_mechanisms"]
        == readiness_state["non_rejected_mechanism_count"],
        "Terminal stage mechanism count is stale",
    )
    check(
        terminal_mechanisms["candidate"] == readiness_state["classification_counts"]["CANDIDATE"],
        "Terminal stage candidate count is stale",
    )
    check(
        terminal_mechanisms["deferred"] == readiness_state["classification_counts"]["DEFERRED"],
        "Terminal stage deferred count is stale",
    )
    check(
        terminal_mechanisms["activated"] == readiness_state["classification_counts"]["ACTIVATED"],
        "Terminal stage activated count is stale",
    )
    check(
        terminal_mechanisms["validated_reference_behavioural_mechanisms"]
        == validation["validated_reference_behavioural_mechanisms"],
        "Terminal stage validated-mechanism count is stale",
    )
    check(
        terminal_mechanisms["estimation_or_refit_allowed"]
        == readiness_state["estimation_or_refit_allowed_count"],
        "Terminal stage estimation/refit authorization is stale",
    )
    check(
        terminal_mechanisms["active_calibration_cycle_open"]
        is readiness_state["calibration_cycle_open"],
        "Terminal stage calibration-cycle state is stale",
    )

    terminal_prospective = stage_terminal["terminal_state"]["prospective_monetary_confirmation"]
    check(
        terminal_prospective["status"] == validation["prospective_confirmation_status"],
        "Terminal stage prospective-confirmation status is stale",
    )
    check(
        terminal_prospective["reserved_response_values_may_be_opened_now"] is False,
        "Terminal stage may not open reserved prospective responses without its event gate",
    )

    terminal_sd = stage_terminal["terminal_state"]["system_dynamics"]
    check(
        terminal_sd["behavioural_closure_active"] is sd_state["behavioural_closure_active"],
        "Terminal stage behavioural-closure state is stale",
    )
    check(
        terminal_sd["complete_endogenous_system_dynamics_model"]
        is sd_state["complete_endogenous_system_dynamics_model"],
        "Terminal stage complete-SD state is stale",
    )
    check(
        terminal_sd["quantitative_feedback_activation_from_stage_completion"] is False,
        "Stage completion may not activate quantitative feedback",
    )

    check(stage_terminal["stage_completion_rule"]["all_currently_admissible_tasks_resolved_or_frozen"] is True, "Terminal stage completion rule is not satisfied")
    check(stage_terminal["stage_completion_rule"]["no_mechanism_estimation_authorized"] is True, "Terminal stage may not authorize mechanism estimation")
    check(stage_terminal["no_release_effect"]["release_or_tag_authorized"] is False, "Terminal stage may not authorize release/tag")
    check(stage_terminal["no_release_effect"]["merge_to_main_authorized_by_this_assessment"] is False, "Terminal stage may not authorize merge to main")
    check(stage_terminal["no_release_effect"]["version_change_authorized"] is False, "Terminal stage may not authorize version change")

    # Live-source refreshes are not canonical reproduction prerequisites.
    source_state = state["source_reproduction"]
    check(source_state["canonical_reproduction_requires_live_network"] is False, "Baseline may not require live network for canonical reproduction")
    check(source_state["live_refreshes_are_new_vintage_evidence"] is True, "Baseline must treat live refresh as new-vintage evidence")
    check(source_state["live_refresh_workflows_manual_only"] is True, "Baseline requires manual-only live refresh workflows")
    for relative in LIVE_MANUAL_WORKFLOWS:
        text = (ROOT / relative).read_text(encoding="utf-8")
        check("workflow_dispatch:" in text, f"Live refresh workflow lacks manual dispatch: {relative}")
        check("pull_request:" not in text, f"Live refresh workflow still runs on pull_request: {relative}")

    report = {
        "baseline_id": manifest["baseline_id"],
        "accounting_complete": acc["complete_stock_and_flow_instruments"],
        "accounting_incomplete": acc["incomplete_instruments"],
        "reference_modes_ready": ref_state["ready_count"],
        "reference_modes_required": ref_state["required_count"],
        "reference_mode_blockers": ref_state["blockers"],
        "reference_mode_recovery_stage_status": ref_state[
            "recovery_stage_status"
        ],
        "reference_mode_next_operational_state": ref_state[
            "next_operational_state"
        ],
        "external_counterpart_screening_state": ref_state[
            "external_counterpart_screening_state"
        ],
        "behavioural_closure_active": sd_state["behavioural_closure_active"],
        "validated_reference_behavioural_mechanisms": validation[
            "validated_reference_behavioural_mechanisms"
        ],
        "prospective_confirmation_status": validation[
            "prospective_confirmation_status"
        ],
        "mechanisms_non_rejected": readiness_state[
            "non_rejected_mechanism_count"
        ],
        "mechanisms_estimation_or_refit_allowed": readiness_state[
            "estimation_or_refit_allowed_count"
        ],
        "mechanism_reopen_registry_entries": readiness_state[
            "reopen_registry_entry_count"
        ],
        "mechanism_reopen_governance_state": readiness_state[
            "reopen_governance_state"
        ],
        "scientific_stage_status": stage_state["status"],
        "scientific_stage_next_operational_state": stage_state[
            "next_operational_state"
        ],
        "mechanism_priority_groups": readiness_state[
            "priority_group_counts"
        ],
        "live_refresh_workflows_manual_only": source_state[
            "live_refresh_workflows_manual_only"
        ],
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
