import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_infoclar_design_tokens_are_versioned_and_accessible():
    tokens = load_json("model/registries/design_tokens.json")
    assert tokens["standard"] == "InfoClar Model Suite Design Standard"
    assert tokens["version"] == "1.1"
    assert tokens["accessibility_target"] == "WCAG 2.2 AA"
    assert tokens["scientific_visuals"]["colour_only_encoding_prohibited"] is True
    assert tokens["scientific_visuals"]["exact_value_view_required"] is True
    assert tokens["interaction"]["focus_must_remain_visible"] is True


def test_workspace_is_asymmetric_2x2_with_required_roles():
    workspace = load_json("model/registries/workspace_contract.json")
    assert workspace["default_language"] == "en"
    assert workspace["supported_languages"] == ["en", "ro"]
    assert workspace["desktop_layout"]["type"] == "asymmetric_2x2"
    assert workspace["desktop_layout"]["columns"] == ["2fr", "1fr"]
    assert workspace["desktop_layout"]["areas"] == [
        ["model", "theory"],
        ["dashboard", "auxiliary"],
    ]
    assert set(workspace["panels"]) == {"model", "theory", "dashboard", "auxiliary"}


def test_small_screen_stack_preserves_model_first_learning_flow():
    workspace = load_json("model/registries/workspace_contract.json")
    responsive = workspace["responsive"]
    assert responsive["small_screen_mode"] == "stack"
    assert responsive["stack_order"] == ["model", "theory", "dashboard", "auxiliary"]
    assert responsive["no_horizontal_page_scroll"] is True


def test_theory_is_context_linked_not_detached():
    workspace = load_json("model/registries/workspace_contract.json")
    requirements = set(workspace["panels"]["theory"]["requirements"])
    assert "context_follows_selected_model_element" in requirements
    assert "deep_links_to_relevant_scientific_objects" in requirements


def test_navigation_uses_canonical_product_labels():
    workspace = load_json("model/registries/workspace_contract.json")
    labels = load_json("model/registries/product_labels.json")
    ids = {item["id"] for item in labels["labels"]}
    assert set(workspace["navigation"]["canonical_sections"]) <= ids
    assert set(workspace["navigation"]["current_stage_enabled"]) <= set(
        workspace["navigation"]["canonical_sections"]
    )


def test_uniformization_cannot_change_scientific_semantics():
    workspace = load_json("model/registries/workspace_contract.json")
    invariance = workspace["scientific_invariance"]
    assert invariance["uniformization_may_change_scientific_results"] is False
    assert invariance["uniformization_may_redefine_accounting_semantics"] is False
    assert invariance["domain_specific_visual_language_is_preserved"] is True
