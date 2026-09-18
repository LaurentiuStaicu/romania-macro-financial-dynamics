from __future__ import annotations

import json
from pathlib import Path

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

    loops = feedback["loops"]
    check(loops, "Feedback registry must contain the candidate feedback architecture")
    for loop in loops:
        check(
            loop["scientific_status"] == "BEHAVIOURAL_CANDIDATE",
            f"{loop['id']} is not explicitly a behavioural candidate",
        )
        check(
            loop["quantitatively_active"] is False,
            f"{loop['id']} is quantitatively active before conformity gates pass",
        )
        check(bool(loop.get("path")), f"{loop['id']} lacks an explicit loop path")
        check(
            bool(loop.get("polarity_hypothesis")),
            f"{loop['id']} lacks a polarity hypothesis",
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

    unit_checks = units["equation_checks"]
    check(
        unit_checks and all(item["status"] == "CONSISTENT" for item in unit_checks),
        "Dimensional-consistency registry contains a failing equation",
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
        "Feedback Architecture": "PASS_AS_QUALITATIVE_CANDIDATE_ARCHITECTURE",
        "Behavioural Closure": "PASS_INACTIVE",
        "Empirical Parameterization": "PARTIAL",
        "Validation": "PARTIAL",
        "complete_endogenous_system_dynamics_model": False,
        "validated_reference_behavioural_mechanisms":
            disposition["validated_reference_behavioural_mechanisms"],
        "candidate_feedback_loops": [loop["id"] for loop in loops],
        "reference_modes_registered": sorted(mode_ids),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
