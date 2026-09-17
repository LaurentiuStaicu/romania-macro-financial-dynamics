import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_primary_contract_is_accounting_spine_first_flow_of_funds():
    contract = load_json("web/public/product-contract-v2.json")
    assert contract["primary_object"] == "FLOW_OF_FUNDS_EXPLORER"
    assert contract["accounting_spine_first"] is True
    assert contract["default_perspective"] == "stock"
    assert contract["default_layer"] == "balance"
    assert contract["behavioural_simulation_enabled"] is False
    assert contract["validated_behavioural_reference_mechanisms"] == 0
    assert contract["prospective_monetary_confirmation_unchanged"] is True
    assert contract["flatpak_started"] is False


def test_normal_layers_never_offer_all_relations_at_once():
    contract = load_json("web/public/product-contract-v2.json")
    assert contract["layer_order"] == ["real", "fiscal", "financial", "balance", "external", "feedback"]
    assert "overview" not in contract["layer_order"]
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert "ALL LAYERS" not in html
    assert "TOATE STRATURILE" not in html


def test_stock_and_flow_are_separate_primary_perspectives():
    contract = load_json("web/public/product-contract-v2.json")
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    overrides = (ROOT / "web/product-v2-overrides.css").read_text(encoding="utf-8")
    assert {p["id"] for p in contract["perspectives"]} == {"stock", "flow"}
    assert 'id="stock-tab"' in html and 'id="flow-tab"' in html
    assert "perspectiveClasses" in js and "REVALUATION_OTHER_FLOW" in js
    assert 'id="matrix-tab"' in html and 'id="flow-matrix"' in html
    assert "renderMatrix" in js
    assert "[hidden]" in overrides and "display:none!important" in overrides.replace(" ", "")


def test_sector_explorer_can_answer_all_seven_product_questions_without_internal_codes():
    contract = load_json("web/public/product-contract-v2.json")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    enhancements = (ROOT / "web/product-v2-enhancements.js").read_text(encoding="utf-8")
    expected = {"funded_by", "funds", "owns", "owes", "instrument", "amount", "change"}
    assert expected == {q["id"] for q in contract["sector_questions"]}
    for text in ("WHO FUNDS IT?", "WHO DOES IT FUND?", "WHAT DOES IT OWN?", "WHAT DOES IT OWE?", "MAJOR COUNTERPARTIES"):
        assert text in js
    assert "HOW HAS IT CHANGED?" in enhancements
    assert "No compatible bilateral change series" in enhancements
    assert "node-code" not in js
    assert "n.id" not in js or "node.id" in js  # ids may drive logic but are not rendered as normal labels


def test_relationship_inspector_uses_human_epistemic_labels_and_complete_fields():
    contract = load_json("web/public/product-contract-v2.json")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    assert set(contract["relation_detail_fields"]) == {"description", "amount", "unit", "period", "instrument", "holder", "issuer", "source", "epistemic_status", "limitations"}
    for label in ("Definition", "Holder / creditor", "Issuer / debtor", "Instrument", "Accounting class", "Epistemic role", "Value", "Period", "Unit", "Sources", "Limitations"):
        assert label in js
    for friendly in ("Observed", "Accounting relation", "Conceptual / unquantified", "Behavioural candidate", "Deferred / not identified"):
        assert friendly in js


def test_frontend_hygiene_keeps_alpha_and_implementation_metadata_out_of_normal_html():
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    forbidden = ("Alpha 0.6", "software_version", "registry", "file path", "test count", "implementation software")
    for token in forbidden:
        assert token not in html
    assert 'id="research-provenance"' in html
    assert "Research / technical provenance" in html


def test_vulnerability_monitor_answers_problem_value_exposure_propagation_evidence_uncertainty():
    architecture = load_json("web/public/product-architecture.json")
    contract = load_json("web/public/product-contract-v2.json")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    required_ids = {
        "external_imbalance", "niip_external_position", "public_debt_refinancing",
        "currency_mismatch_sovereign", "household_debt", "nfc_leverage",
        "bank_sovereign_exposure", "maturity_mismatch", "credit_growth_gap",
    }
    diagnostics = {d["id"]: d for d in architecture["diagnostics"]}
    assert required_ids <= diagnostics.keys()
    assert "WHO IS EXPOSED?" in js and "HOW CAN IT PROPAGATE?" in js and "UNCERTAINTY" in js
    assert "Thresholds or severity labels" in contract["vulnerability_monitor"]["compatibility_rule"]
    assert diagnostics["niip_external_position"]["state"]["en"] == "NOT ASSESSED"
    assert diagnostics["household_debt"]["state"]["en"] == "NOT ASSESSED"


def test_candidate_feedback_records_are_explicitly_not_validated():
    contract = load_json("web/public/product-contract-v2.json")
    feedback = contract["feedback_overrides"]
    assert {"policy_rate", "government_refinancing"} <= feedback.keys()
    for item in feedback.values():
        for key in ("mechanism", "hypothetical_sign", "evidence_status", "parameter_status", "validation_status", "required_before_simulation"):
            assert item[key]["en"] and item[key]["ro"]
        assert "not validated" in item["validation_status"]["en"].lower()


def test_accounting_stress_contract_forbids_behavioural_forecasting():
    contract = load_json("web/public/product-contract-v2.json")
    architecture = load_json("web/public/product-architecture.json")
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert contract["stress_contract"]["forecast"] is False
    assert len(contract["stress_contract"]["allowed"]) == 4
    assert "behavioural feedback simulation" in contract["stress_contract"]["forbidden"]
    assert {s["formula"] for s in architecture["stress_tests"]} >= {"fx_share_revaluation", "rollover_share", "market_value", "bilateral_stock"}
    assert "ACCOUNTING / EXPOSURE STRESS TEST" in html


def test_theory_v2_is_complete_bilingual_and_contextual():
    contract = load_json("web/public/product-contract-v2.json")
    theory = load_json("web/public/theory-corpus-v2.json")
    chapters = {c["id"]: c for c in theory["chapters"]}
    assert len(chapters) >= 36
    assert set(contract["theory_required_topics"]) <= chapters.keys()
    for chapter in chapters.values():
        assert chapter["title"]["en"] and chapter["title"]["ro"]
        assert chapter["summary"]["en"] and chapter["summary"]["ro"]
        assert chapter["sections"]
        for section in chapter["sections"]:
            assert len(section["paragraphs"]["en"]) >= 2
            assert len(section["paragraphs"]["ro"]) >= 2
    assert len(theory["glossary"]) >= 12
    assert len(theory["references"]) >= 8
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    assert "relevantChapterId" in js and "showReader('manual')" in js


def test_usefulness_gate_is_encoded_as_product_contract():
    contract = load_json("web/public/product-contract-v2.json")
    assert contract["usefulness_gate"] == [
        "who_funds_government",
        "who_holds_sector_claims",
        "net_creditor_debtor_when_supported",
        "main_imbalances",
        "exposed_sectors",
        "mechanical_shock_transmission",
        "observed_vs_candidate",
        "simulation_limits",
    ]


def test_visual_audit_is_required_for_desktop_and_mobile_before_merge():
    contract = load_json("web/public/product-contract-v2.json")
    workflow = (ROOT / ".github/workflows/product-visual-audit.yml").read_text(encoding="utf-8")
    capture = (ROOT / "scripts/capture_product_ui.mjs").read_text(encoding="utf-8")
    assert contract["visual_audit"]["required"] is True
    assert contract["visual_audit"]["desktop_viewport"] == {"width": 1440, "height": 1100}
    assert contract["visual_audit"]["mobile_viewport"] == {"width": 390, "height": 844}
    assert {"desktop-matrix", "mobile-matrix"} <= set(contract["visual_audit"]["required_captures"])
    for name in contract["visual_audit"]["required_captures"]:
        assert name in capture
    assert "Stock-only matrix controls are visible in FLOW VIEW" in capture
    assert "playwright" in workflow.lower()
    assert "upload-artifact" in workflow
