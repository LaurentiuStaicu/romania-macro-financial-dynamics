from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "model" / "dynamics" / "unit_registry.json"


def signature(value: dict[str, int]) -> tuple[int, int]:
    return int(value.get("currency", 0)), int(value.get("time", 0))


def multiply(left: tuple[int, int], right: tuple[int, int]) -> tuple[int, int]:
    return left[0] + right[0], left[1] + right[1]


def divide(left: tuple[int, int], right: tuple[int, int]) -> tuple[int, int]:
    return left[0] - right[0], left[1] - right[1]


def audit_registry(registry: dict[str, object]) -> list[str]:
    errors: list[str] = []
    variables = {
        item["id"]: signature(item["signature"])
        for item in registry["variables"]
    }

    expected_variables = {
        "bilateral_financial_position": (1, 0),
        "financial_transaction_period_amount": (1, 0),
        "revaluation_period_amount": (1, 0),
        "other_change_period_amount": (1, 0),
        "financial_transaction_rate": (1, -1),
        "revaluation_rate": (1, -1),
        "other_change_rate": (1, -1),
        "dt": (0, 1),
        "delay_tau": (0, 1),
        "sector_financial_assets": (1, 0),
        "sector_financial_liabilities": (1, 0),
        "sector_net_financial_worth": (1, 0),
        "system_net_financial_worth": (1, 0),
        "safe_ratio": (0, 0),
    }
    for variable, expected in expected_variables.items():
        if variables.get(variable) != expected:
            errors.append(
                f"{variable}: expected signature {expected}, observed {variables.get(variable)}"
            )

    checks = {item["id"]: item for item in registry["equation_checks"]}

    period = checks.get("period_stock_identity")
    if period is None:
        errors.append("period_stock_identity: missing")
    else:
        lhs = signature(period["lhs"])
        for index, term in enumerate(period["rhs_terms"]):
            if signature(term) != lhs:
                errors.append(
                    f"period_stock_identity: rhs term {index} does not match lhs"
                )

    rate = checks.get("rate_stock_identity")
    if rate is None:
        errors.append("rate_stock_identity: missing")
    else:
        lhs = signature(rate["lhs"])
        computed_product = multiply(
            signature(rate["rhs_rate_signature"]),
            signature(rate["dt_signature"]),
        )
        if computed_product != lhs:
            errors.append(
                f"rate_stock_identity: rate*dt {computed_product} does not match lhs {lhs}"
            )
        if signature(rate["product_signature"]) != computed_product:
            errors.append(
                "rate_stock_identity: declared product signature does not match recomputation"
            )

    delay = checks.get("first_order_delay_derivative")
    if delay is None:
        errors.append("first_order_delay_derivative: missing")
    else:
        if delay.get("state_signature") != "same_as_input":
            errors.append(
                "first_order_delay_derivative: state must have same signature as input"
            )
        tau = signature(delay["tau_signature"])
        if tau != variables.get("delay_tau"):
            errors.append(
                "first_order_delay_derivative: tau signature differs from delay_tau variable"
            )
        if divide((1, 0), tau) != (1, -1):
            errors.append(
                "first_order_delay_derivative: dividing a generic currency stock by tau does not yield a rate"
            )
        if delay.get("derivative_signature") != "input_per_year":
            errors.append(
                "first_order_delay_derivative: derivative signature must be input_per_year"
            )

    for check_id, item in checks.items():
        computed_status = "INCONSISTENT" if any(
            error.startswith(f"{check_id}:") for error in errors
        ) else "CONSISTENT"
        if item.get("status") != computed_status:
            errors.append(
                f"{check_id}: declared status {item.get('status')!r} conflicts with recomputed {computed_status}"
            )

    return errors


def main() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    errors = audit_registry(registry)
    if errors:
        raise RuntimeError("Dimensional consistency audit failed:\n- " + "\n- ".join(errors))
    print(json.dumps({
        "status": "PASS",
        "registry": str(REGISTRY.relative_to(ROOT)),
        "checks_recomputed": [
            item["id"] for item in registry["equation_checks"]
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
