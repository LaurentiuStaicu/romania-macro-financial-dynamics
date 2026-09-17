import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def count_csv(path: str) -> int:
    with (ROOT / path).open(encoding="utf-8") as fh:
        return sum(1 for _ in csv.DictReader(fh))


def test_infoclar_is_real_reference_web_surface_not_only_design_contract():
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert 'id="model-panel"' in html
    assert 'id="theory-panel"' in html
    assert 'id="dashboard-panel"' in html
    assert 'id="auxiliary-panel"' in html
    assert 'id="system-map"' in html
    assert 'id="layer-toolbar"' in html
    assert 'id="map-inspector"' in html
    assert 'id="diagnostic-cards"' in html
    assert 'id="theory-reader"' in html
    assert 'data-lang="en"' in html and 'data-lang="ro"' in html


def test_web_snapshot_matches_canonical_sector_and_mechanism_registries():
    snapshot = load_json("web/public/model-stage.json")
    sectors = load_json("model/registries/sectors.json")["sectors"]
    mechanisms = load_json("model/empirical_dynamics/mechanism_registry.json")["mechanisms"]
    counts = {status: 0 for status in ("ACTIVATED", "CANDIDATE", "DEFERRED", "REJECTED")}
    for mechanism in mechanisms:
        counts[mechanism["classification"]] += 1

    assert snapshot["software_version"] == "0.5.2a0"
    assert {item["id"] for item in snapshot["sectors"]} == {item["id"] for item in sectors}
    assert snapshot["empirical_dashboard"]["alpha_0_4_mechanism_counts"] == counts
    assert snapshot["product"]["web_is_reference_product"] is True
    assert snapshot["product"]["native_flatpak_status"] == "DEFERRED_NEAR_V1"


def test_web_preserves_validation_recovery_vintage_and_freeze():
    snapshot = load_json("web/public/model-stage.json")
    split = load_json("data/provenance/validation_recovery_split_0.5.1a0.json")
    disposition = load_json("model/calibration_validation/validation_recovery_disposition.json")
    holdout = load_json("model/calibration_validation/validation_recovery_holdout.json")

    dashboard = snapshot["empirical_dashboard"]
    assert dashboard["policy_rate_observations"] == count_csv("data/raw/validation_recovery/policy_rate_bis_monthly.csv")
    assert dashboard["mir_target_observations_each"] == count_csv("data/raw/validation_recovery/household_housing_mir_monthly.csv")
    assert dashboard["calibration_months"] == split["roles"]["calibration"]["months"]
    assert dashboard["structural_selection_months"] == split["roles"]["structural_selection"]["months"]
    assert dashboard["fresh_household_holdout_months"] == holdout["holdout_period"]["n"]
    assert dashboard["validated_behavioural_mechanisms"] == disposition["validated_reference_behavioural_mechanisms"] == 0
    assert snapshot["validation"]["monetary_pass_through"]["form_frozen_in_alpha_0_5_2"] is True
    assert snapshot["validation"]["monetary_pass_through"]["future_confirmation_from"] == "2026-08"
    assert snapshot["stage"]["interactive_simulation_enabled"] is False
    assert snapshot["validation"]["alpha_0_6_gate"] == "NO_GO_FOR_BEHAVIOURAL_SIMULATION"


def test_web_preserves_government_ledger_negative_result_without_proxy_promotion():
    snapshot = load_json("web/public/model-stage.json")
    dashboard = snapshot["empirical_dashboard"]
    government = snapshot["validation"]["government_refinancing"]

    assert dashboard["government_ledger_rows"] == count_csv("data/processed/government_repricing_ledger_0.5.2a0.csv") == 7
    assert dashboard["government_rows_with_opening_outstanding_principal"] == 0
    assert dashboard["government_rows_with_matched_repricing"] == 0
    assert dashboard["government_2024_12_maturing_1y_pct"] == 10.0
    assert dashboard["government_2024_12_refixing_1y_pct"] == 12.0
    assert government["gate_1"] == "FAIL"
    assert government["gate_2"] == "NOT_OPENED"
    assert government["gate_3"] == "NOT_OPENED"
    assert government["estimation_run"] is False
    assert government["eurostat_boundary_used_for_mof_estimation"] is False
    assert government["final_verdict"] == "DEFERRED"


def test_web_exposes_recovery_result_without_claiming_validation():
    snapshot = load_json("web/public/model-stage.json")
    monetary = snapshot["validation"]["monetary_pass_through"]
    assert monetary["household_selection"] == "PASS_TO_FINAL_EVALUATION"
    assert monetary["household_final_holdout"] == "FAIL_VS_PERSISTENCE"
    assert monetary["household_holdout_policy_changes"] == 0
    assert monetary["final_verdict"] == "CANDIDATE"
    assert snapshot["validation"]["government_refinancing"]["final_verdict"] == "DEFERRED"


def test_accessibility_and_adaptive_contract_is_present_in_actual_web_files():
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    css = (ROOT / "web/styles.css").read_text(encoding="utf-8")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    assert 'class="skip-link"' in html
    assert 'aria-live="polite"' in html
    assert 'role="region"' in html
    assert ':focus-visible' in css
    assert '@media (max-width:900px)' in css
    assert '@media (prefers-reduced-motion:reduce)' in css
    assert "event.key === 'Enter'" in js and "event.key === ' '" in js
    assert "selectDiagnostic" in js and "selectMapObject" in js
    assert "NO_GO_FOR_BEHAVIOURAL_SIMULATION" in js
    assert "product-architecture.json" in js and "theory-corpus.json" in js


def test_flatpak_is_not_started_inside_product_recovery_stage():
    assert not (ROOT / "native").exists()
