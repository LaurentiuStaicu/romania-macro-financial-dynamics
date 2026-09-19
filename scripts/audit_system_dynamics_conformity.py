from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts.audit_dimensional_consistency import audit_registry
except ModuleNotFoundError:
    # Direct execution via "python scripts/audit_system_dynamics_conformity.py"
    # puts scripts/ rather than the repository root on sys.path.
    from audit_dimensional_consistency import audit_registry

ROOT = Path(__file__).resolve().parents[1]

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

REQUIRED_FEEDBACK_GATE_FIELDS = {
    "requires_equation",
    "requires_units",
    "requires_evidence_status",
    "requires_parameter_source_or_estimation_plan",
    "requires_identifiability_assessment",
    "requires_endogenous_exogenous_classification",
    "requires_polarity_and_loop_path",
    "requires_delay_specification_when_delay_claimed",
    "requires_nonlinearity_documentation_when_present",
    "requires_extreme_condition_test",
    "requires_sensitivity_plan",
    "requires_validation_gate",
    "requires_reference_mode_link",
    "requires_accounting_conservation_preservation",
    "all_requirements_must_pass_before_quantitative_activation",
}

REQUIRED_STRUCTURAL_TESTS = {
    "stock_identity",
    "double_entry_conservation",
    "dimensional_consistency",
    "zero_flow_extreme_condition",
    "finite_large_value_extreme_condition",
    "delay_steady_state",
    "integration_error_convergence",
    "incomplete_empirical_initialization_rejected",
}


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def normalized_link_sign(raw: str) -> int:
    if raw.startswith("+"):
        return 1
    if raw.startswith("-"):
        return -1
    raise RuntimeError(f"Unsupported causal-link sign: {raw!r}")


def path_is_contiguous(path: list[dict[str, str]]) -> bool:
    return bool(path) and all(
        path[index - 1]["to"] == path[index]["from"]
        for index in range(1, len(path))
    )


def path_is_closed(path: list[dict[str, str]]) -> bool:
    return bool(path) and path[-1]["to"] == path[0]["from"]


def implied_loop_polarity(path: list[dict[str, str]]) -> str:
    if not path_is_closed(path):
        raise RuntimeError("Loop polarity is undefined for an open causal path")
    product = 1
    for link in path:
        product *= normalized_link_sign(str(link["sign"]))
    return "reinforcing" if product > 0 else "balancing"


def declared_polarity_base(value: str) -> str | None:
    if value.startswith("reinforcing"):
        return "reinforcing"
    if value.startswith("balancing"):
        return "balancing"
    return None


def reference_mode_readiness(
    references: dict,
    required_modes: set[str],
) -> dict[str, object]:
    modes = references.get("modes", [])
    mode_ids = [str(mode["id"]) for mode in modes]
    if len(mode_ids) != len(set(mode_ids)):
        raise RuntimeError("Reference-mode registry contains duplicate IDs")

    vocabulary = set(references.get("status_vocabulary", []))
    by_id = {str(mode["id"]): mode for mode in modes}
    missing = required_modes - set(by_id)
    if missing:
        raise RuntimeError(
            f"Reference-mode registry missing: {sorted(missing)}"
        )

    policy = references.get("closure_readiness_policy", {})
    ready_statuses = set(
        policy.get(
            "ready_statuses_for_integrated_quantitative_closure",
            [],
        )
    )
    if not ready_statuses:
        raise RuntimeError("Reference-mode closure readiness has no ready statuses")
    if not ready_statuses <= vocabulary:
        raise RuntimeError(
            "Reference-mode ready statuses are outside the declared vocabulary"
        )

    required_exception_fields = set(
        policy.get("qualitative_exception_required_fields", [])
    )
    exceptions = policy.get("current_qualitative_exceptions", [])
    exception_ids: set[str] = set()
    for item in exceptions:
        if not isinstance(item, dict):
            raise RuntimeError(
                "Reference-mode qualitative exceptions must be structured objects"
            )
        missing_fields = required_exception_fields - set(item)
        if missing_fields:
            raise RuntimeError(
                "Reference-mode qualitative exception missing fields: "
                f"{sorted(missing_fields)}"
            )
        exception_id = str(item["id"])
        if exception_id not in required_modes:
            raise RuntimeError(
                f"Qualitative exception targets non-required mode {exception_id}"
            )
        if exception_id in exception_ids:
            raise RuntimeError(
                f"Duplicate qualitative reference-mode exception: {exception_id}"
            )
        if not str(item["validation_basis"]).strip() or not str(
            item["justification"]
        ).strip():
            raise RuntimeError(
                f"Qualitative exception {exception_id} lacks substantive basis"
            )
        exception_ids.add(exception_id)

    ready: list[str] = []
    blockers: list[str] = []
    statuses: dict[str, str] = {}
    for mode_id in sorted(required_modes):
        status = str(by_id[mode_id]["status"])
        if status not in vocabulary:
            raise RuntimeError(
                f"Reference mode {mode_id} has unsupported status {status}"
            )
        statuses[mode_id] = status
        if status in ready_statuses or mode_id in exception_ids:
            ready.append(mode_id)
        else:
            blockers.append(mode_id)

    return {
        "status": "READY" if not blockers else "BLOCKED",
        "ready_modes": ready,
        "blocking_modes": blockers,
        "mode_statuses": statuses,
        "ready_statuses": sorted(ready_statuses),
        "qualitative_exception_ids": sorted(exception_ids),
    }


def empirical_activation_governance(
    contract: dict,
    registry: dict,
    disposition: dict,
) -> dict[str, object]:
    mechanisms = registry.get("mechanisms", [])
    mechanism_ids = [str(item["id"]) for item in mechanisms]
    if len(mechanism_ids) != len(set(mechanism_ids)):
        raise RuntimeError("Empirical mechanism registry contains duplicate IDs")

    vocabulary = set(registry.get("status_vocabulary", []))
    by_id = {str(item["id"]): item for item in mechanisms}
    for mechanism_id, item in by_id.items():
        classification = str(item["classification"])
        if classification not in vocabulary:
            raise RuntimeError(
                f"Empirical mechanism {mechanism_id} has unsupported status "
                f"{classification}"
            )

    contract_activated = set(contract.get("activated_mechanisms", []))
    registry_activated = {
        mechanism_id
        for mechanism_id, item in by_id.items()
        if item["classification"] == "ACTIVATED"
    }
    if contract_activated != registry_activated:
        raise RuntimeError(
            "Empirical contract activated-mechanism list disagrees with registry"
        )

    post = contract.get("post_validation_disposition", {})
    previous = set(post.get("previous_calibration_admissions", []))
    status_map = post.get("current_status_of_previous_admissions", {})
    if set(status_map) != previous:
        raise RuntimeError(
            "Post-validation status map does not cover exactly the previous admissions"
        )
    missing_previous = previous - set(by_id)
    if missing_previous:
        raise RuntimeError(
            "Post-validation governance references unknown mechanisms: "
            f"{sorted(missing_previous)}"
        )
    for mechanism_id, expected_status in status_map.items():
        actual = str(by_id[mechanism_id]["classification"])
        if actual != expected_status:
            raise RuntimeError(
                f"Post-validation status for {mechanism_id} is {actual}, "
                f"expected {expected_status}"
            )
        evidence = by_id[mechanism_id].get(
            "validation_recovery_disposition"
        )
        if not isinstance(evidence, dict):
            raise RuntimeError(
                f"{mechanism_id} lacks explicit validation-recovery disposition"
            )
        if str(evidence.get("status")) != expected_status:
            raise RuntimeError(
                f"{mechanism_id} embedded recovery status disagrees with registry"
            )
        if not str(evidence.get("source", "")).strip():
            raise RuntimeError(
                f"{mechanism_id} recovery disposition lacks a source"
            )

    activated_after = set(
        post.get("activated_mechanisms_after_disposition", [])
    )
    if activated_after != contract_activated:
        raise RuntimeError(
            "Post-validation activated set disagrees with empirical contract"
        )

    validated = int(
        disposition["validated_reference_behavioural_mechanisms"]
    )
    if int(post.get("validated_reference_behavioural_mechanisms", -1)) != validated:
        raise RuntimeError(
            "Empirical post-validation count disagrees with validation disposition"
        )

    active_cycle = bool(post.get("active_calibration_cycle_open"))
    if not active_cycle and contract_activated:
        raise RuntimeError(
            "Closed calibration cycle cannot retain ACTIVATED mechanisms"
        )

    central_feedback = {
        mechanism_id
        for mechanism_id, item in by_id.items()
        if item.get("central_feedback") is True
    }
    if not central_feedback <= registry_activated:
        raise RuntimeError(
            "Only mechanisms in an open ACTIVATED calibration cycle may be "
            "labelled central_feedback"
        )

    return {
        "active_calibration_cycle_open": active_cycle,
        "activated_mechanisms": sorted(registry_activated),
        "previous_calibration_admissions": sorted(previous),
        "current_status_of_previous_admissions": {
            key: status_map[key] for key in sorted(status_map)
        },
        "central_feedback_mechanisms": sorted(central_feedback),
        "validated_reference_behavioural_mechanisms": validated,
    }


def main() -> None:
    model = load("model/registries/model_contract.json")
    core = load("model/dynamics/core_contract.json")
    feedback = load("model/dynamics/feedback_registry.json")
    units = load("model/dynamics/unit_registry.json")
    references = load("model/dynamics/reference_modes.json")
    gate = load("model/dynamics/system_dynamics_conformity_gate.json")
    disposition = load(
        "model/calibration_validation/validation_recovery_disposition.json"
    )
    empirical_contract = load("model/empirical_dynamics/contract.json")
    empirical_registry = load("model/empirical_dynamics/mechanism_registry.json")
    accounting_readiness = load("model/accounting/accounting_readiness_gate.json")

    check(
        model["dynamic_core"]["accounting_spine_is_hard_constraint"] is True,
        "Accounting Spine must remain a hard constraint",
    )
    check(
        model["dynamic_core"]["behavioural_closure_active"] is False,
        "Behavioural closure must remain inactive at the current maturity stage",
    )
    check(
        model["dynamic_core"]["complete_endogenous_system_dynamics_model"] is False,
        "Current RMD must not claim complete endogenous System Dynamics status",
    )
    check(
        core["behavioural_closure"]["active"] is False,
        "Core behavioural closure unexpectedly active",
    )
    check(
        model["dynamic_core"]["canonical_multi_instrument_stock_initialization_ready"]
        is False,
        "Canonical multi-instrument stock initialization is not yet empirically ready",
    )
    check(
        model["dynamic_core"]["canonical_full_2025_stock_flow_benchmark_ready"]
        is False,
        "Canonical full stock-flow benchmark is not yet empirically ready",
    )
    check(
        accounting_readiness["hard_rules"][
            "behavioural_closure_may_not_override_accounting_readiness"
        ]
        is True,
        "Behavioural closure must not override incomplete Accounting Spine readiness",
    )

    empirical_governance = empirical_activation_governance(
        empirical_contract,
        empirical_registry,
        disposition,
    )
    check(
        model["empirical_dynamics"]["active_calibration_cycle_open"]
        is empirical_governance["active_calibration_cycle_open"],
        "Model contract active-calibration-cycle state is stale",
    )
    check(
        model["empirical_dynamics"]["activated_mechanisms_count"]
        == len(empirical_governance["activated_mechanisms"]),
        "Model contract activated-mechanism count is stale",
    )
    check(
        model["empirical_dynamics"][
            "validation_disposition_governs_current_status"
        ]
        is True,
        "Current empirical mechanism status must be governed by frozen validation disposition",
    )

    structures = feedback["loops"]
    check(structures, "Feedback registry must contain the candidate feedback architecture")

    delay_registry = {item["id"]: item for item in feedback["delay_candidates"]}
    closed_loop_ids: list[str] = []
    open_chain_ids: list[str] = []

    for structure in structures:
        structure_id = structure["id"]
        status = structure["scientific_status"]
        check(
            status in {"BEHAVIOURAL_CANDIDATE", "BEHAVIOURAL_CANDIDATE_OPEN_CHAIN"},
            f"{structure_id} has unsupported scientific status {status}",
        )
        check(
            structure["quantitatively_active"] is False,
            f"{structure_id} is quantitatively active before conformity gates pass",
        )

        path = structure.get("path")
        check(bool(path), f"{structure_id} lacks an explicit causal path")
        check(
            path_is_contiguous(path),
            f"{structure_id} causal path is not contiguous",
        )

        for link in path:
            normalized_link_sign(str(link["sign"]))

        for delay_id in structure.get("delay_candidates", []):
            check(
                delay_id in delay_registry,
                f"{structure_id} references unknown delay candidate {delay_id}",
            )
            delay = delay_registry[delay_id]
            check(
                delay["active"] is False,
                f"{structure_id} has an active delay before feedback activation",
            )

        if status == "BEHAVIOURAL_CANDIDATE":
            check(
                structure.get("topology_status") == "CLOSED_CANDIDATE_LOOP",
                f"{structure_id} must declare CLOSED_CANDIDATE_LOOP topology",
            )
            check(
                path_is_closed(path),
                f"{structure_id} is labelled as a loop but its path is open",
            )
            declared = declared_polarity_base(
                str(structure.get("polarity_hypothesis", ""))
            )
            check(
                declared is not None,
                f"{structure_id} lacks a reinforcing/balancing polarity hypothesis",
            )
            implied = implied_loop_polarity(path)
            check(
                declared == implied,
                (
                    f"{structure_id} declared polarity {declared!r} conflicts with "
                    f"signed-path polarity {implied!r}"
                ),
            )
            closed_loop_ids.append(structure_id)
        else:
            check(
                structure.get("topology_status") == "OPEN_CHAIN",
                f"{structure_id} open candidate must declare OPEN_CHAIN topology",
            )
            check(
                not path_is_closed(path),
                f"{structure_id} is classified as open but its path is closed",
            )
            check(
                structure.get("polarity_hypothesis") == "not_applicable_until_closed",
                f"{structure_id} must not assign loop polarity before closure",
            )
            check(
                bool(structure.get("activation_blocker")),
                f"{structure_id} open chain lacks an explicit activation blocker",
            )
            open_chain_ids.append(structure_id)

    topology_gate = gate["feedback_topology_gate"]
    check(
        set(topology_gate["closed_loop_candidates"]) == set(closed_loop_ids),
        "Conformity gate closed-loop list does not match feedback registry",
    )
    check(
        set(topology_gate["open_feedback_chains"]) == set(open_chain_ids),
        "Conformity gate open-chain list does not match feedback registry",
    )

    activation = feedback["activation_gate"]
    missing_activation = REQUIRED_FEEDBACK_GATE_FIELDS - set(activation)
    check(
        not missing_activation,
        f"Feedback activation gate missing: {sorted(missing_activation)}",
    )
    check(
        all(activation[field] is True for field in REQUIRED_FEEDBACK_GATE_FIELDS),
        "Every feedback activation requirement must be mandatory",
    )

    delay_state = next(
        stock for stock in core["stocks"]
        if stock["id"] == "generic_first_order_delay_state"
    )
    delay_equation = next(
        equation for equation in core["equations"]
        if equation["id"] == "first_order_delay"
    )
    check(
        delay_state["scientific_status"] == "STRUCTURAL_DYNAMIC_PRIMITIVE",
        "Generic delay state must not be classified as an accounting identity",
    )
    check(
        delay_equation["scientific_status"] == "STRUCTURAL_DYNAMIC_PRIMITIVE",
        "First-order delay equation must not be classified as an accounting identity",
    )

    dimensional_errors = audit_registry(units)
    check(
        not dimensional_errors,
        "Recomputed dimensional-consistency audit failed: "
        + "; ".join(dimensional_errors),
    )

    required_tests = set(core["required_tests"])
    check(
        REQUIRED_STRUCTURAL_TESTS <= required_tests,
        "Dynamic core does not require the full structural test set",
    )
    check(
        core["integration"]["integration_error_test_required"] is True,
        "Numerical integration convergence must remain a required test",
    )

    mode_ids = {mode["id"] for mode in references["modes"]}
    missing_modes = REQUIRED_REFERENCE_MODES - mode_ids
    check(
        not missing_modes,
        f"Reference-mode registry missing: {sorted(missing_modes)}",
    )
    check(
        references["closure_rule"],
        "Reference-mode registry lacks a closure rule",
    )

    reference_readiness = reference_mode_readiness(
        references,
        REQUIRED_REFERENCE_MODES,
    )
    reference_gate = gate["reference_mode_gate"]
    check(
        set(reference_gate["required_variables"]) == REQUIRED_REFERENCE_MODES,
        "Conformity-gate required reference modes differ from the canonical set",
    )
    check(
        set(
            reference_gate[
                "ready_statuses_for_integrated_quantitative_closure"
            ]
        )
        == set(reference_readiness["ready_statuses"]),
        "Conformity-gate ready statuses differ from reference-mode policy",
    )
    check(
        set(reference_gate["qualitative_exceptions_registered"])
        == set(reference_readiness["qualitative_exception_ids"]),
        "Conformity-gate qualitative exceptions differ from registry policy",
    )
    check(
        reference_gate["current_closure_readiness"]
        == reference_readiness["status"],
        "Declared reference-mode closure readiness disagrees with the registry",
    )
    check(
        set(reference_gate["current_ready_variables"])
        == set(reference_readiness["ready_modes"]),
        "Declared ready reference modes disagree with the registry",
    )
    check(
        set(reference_gate["current_blocking_variables"])
        == set(reference_readiness["blocking_modes"]),
        "Declared blocking reference modes disagree with the registry",
    )
    check(
        model["dynamic_core"]["reference_mode_closure_ready"]
        is (reference_readiness["status"] == "READY"),
        "Model contract reference-mode readiness disagrees with the registry",
    )
    check(
        model["dynamic_core"]["reference_mode_ready_count"]
        == len(reference_readiness["ready_modes"]),
        "Model contract reference-mode ready count is stale",
    )
    check(
        model["dynamic_core"]["reference_mode_required_count"]
        == len(REQUIRED_REFERENCE_MODES),
        "Model contract reference-mode required count is stale",
    )

    check(
        gate["behavioural_closure"][
            "must_not_be_activated_for_methodological_completeness"
        ]
        is True,
        "Conformity gate must prohibit closure for cosmetic methodological completeness",
    )
    check(
        reference_gate["required_before_behavioural_closure"] is True,
        "Reference modes must be required before behavioural closure",
    )
    check(
        disposition["validated_reference_behavioural_mechanisms"] == 0,
        "Conformity audit assumptions must be revisited after a reference mechanism validates",
    )

    report = {
        "Accounting / Stock-Flow Core": "PASS_WITH_EMPIRICAL_COMPLETENESS_LIMIT",
        "Canonical Multi-Instrument Stock Initialization": "BLOCKED_INCOMPLETE",
        "Canonical Full 2025 Stock-Flow Benchmark": "BLOCKED_INCOMPLETE",
        "Feedback Architecture": "PASS_WITH_OPEN_CHAIN_EXPLICITLY_BLOCKED",
        "Behavioural Closure": "PASS_INACTIVE",
        "Empirical Parameterization": "PARTIAL",
        "Validation": "PARTIAL",
        "complete_endogenous_system_dynamics_model": False,
        "validated_reference_behavioural_mechanisms":
            disposition["validated_reference_behavioural_mechanisms"],
        "closed_candidate_feedback_loops": closed_loop_ids,
        "open_candidate_feedback_chains": open_chain_ids,
        "reference_modes_registered": sorted(mode_ids),
        "reference_mode_closure_readiness": reference_readiness["status"],
        "reference_mode_ready_variables": reference_readiness["ready_modes"],
        "reference_mode_blocking_variables": reference_readiness["blocking_modes"],
        "empirical_activation_governance": empirical_governance,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
