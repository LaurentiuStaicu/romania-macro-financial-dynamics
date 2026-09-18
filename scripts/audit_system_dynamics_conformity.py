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

    check(
        gate["behavioural_closure"][
            "must_not_be_activated_for_methodological_completeness"
        ]
        is True,
        "Conformity gate must prohibit closure for cosmetic methodological completeness",
    )
    check(
        gate["reference_mode_gate"]["required_before_behavioural_closure"] is True,
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
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
