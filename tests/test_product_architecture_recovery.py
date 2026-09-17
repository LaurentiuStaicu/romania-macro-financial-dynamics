import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_recovery_contract_is_cross_cutting_and_science_frozen():
    contract = load_json("model/registries/product_architecture_recovery.json")
    science = contract["scientific_invariance"]
    snapshot = load_json("web/public/model-stage.json")
    architecture = load_json("web/public/product-architecture.json")

    assert contract["stage_type"] == "cross_cutting_product_architecture_recovery"
    assert all(science[key] is True for key in (
        "alpha_0_1_through_0_5_2_results_unchanged",
        "accounting_spine_unchanged",
        "dynamic_core_unchanged",
        "empirical_dynamics_results_unchanged",
        "household_delta_policy_form_frozen_for_prospective_confirmation",
        "no_synthetic_missing_values",
        "no_new_behavioural_mechanism",
    ))
    assert science["validated_behavioural_reference_mechanisms"] == 0
    assert science["alpha_0_6_gate"] == "NO_GO"
    assert science["behavioural_simulator_enabled"] is False
    assert architecture["scientific_state"]["behavioural_simulation_enabled"] is False
    assert snapshot["validation"]["alpha_0_6_gate"] == "NO_GO_FOR_BEHAVIOURAL_SIMULATION"


def test_map_is_not_six_symbolic_nodes_without_semantic_relationships():
    architecture = load_json("web/public/product-architecture.json")
    contract = load_json("model/registries/product_architecture_recovery.json")
    nodes = architecture["nodes"]
    edges = architecture["edges"]
    layers = {layer["id"] for layer in architecture["layers"]}

    assert {node["id"] for node in nodes} == {"H", "C", "F", "G", "BNR", "X"}
    assert layers == {"overview", "real", "fiscal", "financial", "balance", "external", "feedback"}
    assert len(edges) >= 20
    required = {
        "wages", "consumption", "investment", "tax_households", "tax_firms",
        "social_contributions", "transfers", "government_spending", "deposits_households",
        "deposits_firms", "loans_households", "loans_firms", "interest_households",
        "policy_rate", "central_bank_reserves", "government_securities_finance",
        "government_securities_external", "government_refinancing", "exports", "imports",
        "external_financing",
    }
    assert required <= {edge["id"] for edge in edges}
    assert contract["model_panel"]["dominant_surface"] is True
    assert contract["product_principle"] == "overview -> filter/zoom -> details on demand"


def test_every_map_relationship_has_epistemic_semantics_and_missing_values_are_not_fabricated():
    architecture = load_json("web/public/product-architecture.json")
    valid_layers = {layer["id"] for layer in architecture["layers"]} - {"overview"}
    node_ids = {node["id"] for node in architecture["nodes"]}

    for edge in architecture["edges"]:
        assert edge["layer"] in valid_layers
        assert edge["from"] in node_ids and edge["to"] in node_ids
        assert edge["label"]["en"] and edge["label"]["ro"]
        assert edge["definition"]["en"] and edge["definition"]["ro"]
        assert edge["epistemic_role"]
        assert "unit" in edge and "period" in edge and "value" in edge
        assert edge["limit"]["en"] and edge["limit"]["ro"]
        if edge["value"] is None:
            assert edge["value"] is not 0

    by_id = {edge["id"]: edge for edge in architecture["edges"]}
    assert by_id["deposits_households"]["epistemic_role"] == "ACCOUNTING_SPINE_F2_RELATION"
    assert by_id["loans_households"]["epistemic_role"] == "ACCOUNTING_SPINE_F4_RELATION"
    assert by_id["government_securities_external"]["epistemic_role"] == "ACCOUNTING_SPINE_F3_PARTIAL_SOURCE"
    assert by_id["policy_rate"]["epistemic_role"] == "CANDIDATE_EMPIRICAL_MECHANISM"
    assert by_id["government_refinancing"]["epistemic_role"] == "DEFERRED_MECHANISM_OBJECT"


def test_dashboard_is_diagnostic_not_software_metadata():
    architecture = load_json("web/public/product-architecture.json")
    contract = load_json("model/registries/product_architecture_recovery.json")
    diagnostics = architecture["diagnostics"]
    object_ids = {node["id"] for node in architecture["nodes"]} | {edge["id"] for edge in architecture["edges"]}

    assert {item["id"] for item in diagnostics} == {
        "external_imbalance", "fiscal_imbalance", "sovereign_repricing",
        "fx_sovereign_exposure", "monetary_transmission_gap",
    }
    for item in diagnostics:
        for field in ("problem", "why", "direction", "state", "basis", "uncertainty"):
            assert item[field]["en"] and item[field]["ro"]
        assert item["severity_basis"]
        assert item["map_objects"]
        assert set(item["map_objects"]) <= object_ids

    forbidden = set(contract["dashboard_panel"]["forbidden_primary_metrics"])
    assert {"software_version", "alpha_stage", "variable_count", "source_count"} <= forbidden
    assert contract["dashboard_panel"]["dashboard_to_map_link_required"] is True


def test_theory_learn_is_complete_bilingual_contextual_corpus():
    theory = load_json("web/public/theory-corpus.json")
    contract = load_json("model/registries/product_architecture_recovery.json")
    chapters = {chapter["id"]: chapter for chapter in theory["chapters"]}

    assert len(chapters) >= 18
    assert set(contract["theory_panel"]["required_topics"]) <= set(chapters)
    for chapter in chapters.values():
        assert chapter["title"]["en"] and chapter["title"]["ro"]
        assert chapter["summary"]["en"] and chapter["summary"]["ro"]
        assert chapter["sections"]
        for section in chapter["sections"]:
            assert section["paragraphs"]["en"] and section["paragraphs"]["ro"]
    assert len(theory["glossary"]) >= 8
    assert len(theory["references"]) >= 5
    assert contract["theory_panel"]["map_to_theory_link_required"] is True


def test_ui_wires_filters_map_dashboard_theory_and_keyboard_navigation():
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    css = (ROOT / "web/styles.css").read_text(encoding="utf-8")

    assert 'id="layer-toolbar"' in html
    assert 'id="system-map"' in html
    assert 'id="map-inspector"' in html
    assert 'id="diagnostic-cards"' in html
    assert 'id="open-chapter"' in html and 'id="open-glossary"' in html and 'id="open-references"' in html
    assert "visibleEdges" in js
    assert "highlightSets" in js
    assert "selectMapObject" in js
    assert "selectDiagnostic" in js
    assert "relevantChapterId" in js
    assert "scrollIntoView" in js
    assert "event.key === 'Enter'" in js and "event.key === ' '" in js
    assert "aria-pressed" in js
    assert "grid-template-columns:minmax(0,2.25fr)" in css
    assert "@media (max-width:900px)" in css


def test_primary_product_surface_does_not_regress_to_development_metadata():
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    contract = load_json("model/registries/product_architecture_recovery.json")
    assert "stage-label" not in html
    assert "mode-badge" not in html
    assert "Flatpak" not in html
    assert "software_version" not in html
    assert contract["auxiliary_panel"]["development_metadata_on_primary_surface"] is False
    assert not (ROOT / "native").exists()
