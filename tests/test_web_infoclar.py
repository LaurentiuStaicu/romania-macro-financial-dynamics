import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_infoclar_is_real_reference_web_surface_not_only_design_contract():
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert 'id="model-panel"' in html
    assert 'id="theory-panel"' in html
    assert 'id="dashboard-panel"' in html
    assert 'id="auxiliary-panel"' in html
    assert 'public/model-stage.json' not in html  # consumed by app.js, not duplicated inline
    assert 'data-lang="en"' in html and 'data-lang="ro"' in html


def test_web_snapshot_matches_canonical_sector_and_mechanism_registries():
    snapshot = load_json("web/public/model-stage.json")
    sectors = load_json("model/registries/sectors.json")["sectors"]
    mechanisms = load_json("model/empirical_dynamics/mechanism_registry.json")["mechanisms"]
    counts = {status: 0 for status in ("ACTIVATED", "CANDIDATE", "DEFERRED", "REJECTED")}
    for mechanism in mechanisms:
        counts[mechanism["classification"]] += 1

    assert {item["id"] for item in snapshot["sectors"]} == {item["id"] for item in sectors}
    assert snapshot["empirical_dashboard"]["alpha_0_4_mechanism_counts"] == counts
    assert snapshot["product"]["web_is_reference_product"] is True
    assert snapshot["product"]["native_flatpak_status"] == "DEFERRED_NEAR_V1"


def test_web_dashboard_matches_frozen_validation_data_roles_and_dispositions():
    snapshot = load_json("web/public/model-stage.json")
    provenance = load_json("data/provenance/monetary_pass_through_bnr_2024_2025.json")
    disposition = load_json("model/calibration_validation/mechanism_disposition.json")

    dashboard = snapshot["empirical_dashboard"]
    assert dashboard["calibration_months"] == provenance["data_roles"]["calibration"]["observations"]
    assert dashboard["structural_selection_months"] == provenance["data_roles"]["structural_selection"]["observations"]
    assert dashboard["evaluation_holdout_months"] == provenance["data_roles"]["evaluation_holdout"]["observations"]
    assert dashboard["validated_behavioural_mechanisms"] == disposition["validated_reference_behavioural_mechanisms"]
    assert snapshot["stage"]["interactive_simulation_enabled"] is False
    assert snapshot["validation"]["alpha_0_6_gate"] == "NO_GO_FOR_BEHAVIOURAL_SIMULATION"


def test_accessibility_and_adaptive_contract_is_present_in_actual_web_files():
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    css = (ROOT / "web/styles.css").read_text(encoding="utf-8")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    assert 'class="skip-link"' in html
    assert 'aria-live="polite"' in html
    assert ':focus-visible' in css
    assert '@media (max-width: 900px)' in css
    assert "event.key === 'Enter'" in js and "event.key === ' '" in js


def test_flatpak_is_not_started_inside_web_first_stage():
    assert not (ROOT / "native").exists()
