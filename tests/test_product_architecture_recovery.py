import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_recovery_keeps_science_frozen_and_behavioural_simulation_no_go():
    contract = load_json("model/registries/product_architecture_recovery.json")
    architecture = load_json("web/public/product-architecture.json")
    snapshot = load_json("web/public/model-stage.json")
    science = contract["scientific_invariance"]
    assert science["validated_behavioural_reference_mechanisms"] == 0
    assert science["alpha_0_6_gate"] == "NO_GO"
    assert science["behavioural_simulator_enabled"] is False
    assert science["no_synthetic_missing_values"] is True
    assert architecture["scientific_state"]["validated_behavioural_reference_mechanisms"] == 0
    assert architecture["scientific_state"]["prospective_monetary_confirmation_unchanged"] is True
    assert snapshot["validation"]["alpha_0_6_gate"] == "NO_GO_FOR_BEHAVIOURAL_SIMULATION"


def test_primary_object_is_flow_of_funds_with_stock_flow_and_bilateral_views():
    architecture = load_json("web/public/product-architecture.json")
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    assert {n["id"] for n in architecture["nodes"]} == {"H", "C", "F", "G", "BNR", "X"}
    assert {l["id"] for l in architecture["layers"]} == {"overview", "real", "fiscal", "financial", "balance", "external", "feedback"}
    assert 'id="stock-view"' in html and 'id="flow-view"' in html
    assert 'id="matrix-view"' in html and 'id="flow-matrix"' in html
    assert "perspectiveMatch" in js and "renderMatrix" in js
    assert sum(1 for e in architecture["edges"] if e.get("is_financial_position")) >= 7
    assert {e.get("instrument") for e in architecture["edges"]} >= {"F2", "F3", "F4"}


def test_stock_and_flow_are_semantically_separated_not_only_styled():
    architecture = load_json("web/public/product-architecture.json")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    classes = {e["accounting_class"] for e in architecture["edges"]}
    assert {"FLOW", "STOCK", "REVALUATION_OTHER_FLOW", "BEHAVIOURAL_CANDIDATE"} <= classes
    assert "e.accounting_class==='STOCK'" in js
    assert "e.accounting_class==='FLOW'" in js
    assert "REVALUATION_OTHER_FLOW" in js
    assert "Stock / balance-sheet position" in js
    assert "Flow / transaction" in js


def test_sector_click_answers_product_questions_without_internal_codes():
    architecture = load_json("web/public/product-architecture.json")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    for n in architecture["nodes"]:
        assert "asset_edges" in n and "liability_edges" in n
        assert n["net_position"]["en"] and n["net_position"]["ro"]
        assert n["vulnerability"]["en"] and n["vulnerability"]["ro"]
    for needle in ("WHO FUNDS IT?", "WHO DOES IT FUND?", "WHAT DOES IT OWN?", "WHAT DOES IT OWE?", "NET FINANCIAL POSITION", "HOW HAS IT CHANGED?", "VULNERABILITY CHANNELS"):
        assert needle in js
    assert "node-code" not in js
    assert "c.textContent=n.id" not in js


def test_relationship_click_exposes_amount_counterparties_evidence_and_candidate_validation():
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    for needle in ("Description", "Direction", "Holder / creditor", "Issuer / debtor", "Instrument", "Amount", "Period", "Evidence status", "Can directly affect", "Limitations", "Evidence"):
        assert needle in js
    for needle in ("Hypothesised sign", "Parameter status", "Validation status", "Required before simulation"):
        assert needle in js
    assert "candidateDetails" in js


def test_normal_frontend_hides_internal_registry_and_alpha_metadata():
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    visible_shell = html.lower()
    for forbidden in ("registry", "file path", "software_version", "test count", "alpha 0.6"):
        assert forbidden not in visible_shell
    assert "map_objects.join" not in js
    assert "displayMappedObjects" in js
    assert "roleLabel" in js


def test_vulnerability_monitor_is_about_romania_not_software_metadata():
    architecture = load_json("web/public/product-architecture.json")
    diagnostics = {d["id"]: d for d in architecture["diagnostics"]}
    required = {"external_imbalance", "niip_external_position", "public_debt_refinancing", "currency_mismatch_sovereign", "household_debt", "nfc_leverage", "bank_sovereign_exposure", "maturity_mismatch", "credit_growth_gap"}
    assert required <= set(diagnostics)
    object_ids = {n["id"] for n in architecture["nodes"]} | {e["id"] for e in architecture["edges"]}
    for d in diagnostics.values():
        for key in ("problem", "definition", "value_trend", "state", "why", "propagation", "source_note", "uncertainty"):
            assert d[key]["en"] and d[key]["ro"]
        assert d["epistemic_status"]
        assert set(d["map_objects"]) <= object_ids
    assert "software_version" not in json.dumps(architecture["diagnostics"])
    assert diagnostics["niip_external_position"]["state"]["en"] == "NOT ASSESSED"
    assert diagnostics["household_debt"]["state"]["en"] == "NOT ASSESSED"


def test_benchmarks_are_not_applied_across_incompatible_definitions():
    architecture = load_json("web/public/product-architecture.json")
    diagnostics = {d["id"]: d for d in architecture["diagnostics"]}
    assert diagnostics["external_imbalance"]["benchmark"] is None
    assert "3-year" in diagnostics["external_imbalance"]["source_note"]["en"]
    assert "not applied" in diagnostics["niip_external_position"]["benchmark"]["en"]
    assert diagnostics["currency_mismatch_sovereign"]["benchmark"] is None


def test_accounting_stress_tests_are_mechanical_and_not_behavioural_forecasts():
    architecture = load_json("web/public/product-architecture.json")
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    tests = {s["id"]: s for s in architecture["stress_tests"]}
    assert {"stress_fx_sovereign", "stress_rollover", "stress_security_value", "stress_bilateral_stock"} <= set(tests)
    assert 'id="stress-panel"' in html and "ACCOUNTING / EXPOSURE STRESS TEST" in html
    assert "NOT A FORECAST" in js
    assert "fx_share_revaluation" in js and "rollover_share" in js and "market_value" in js and "bilateral_stock" in js
    assert tests["stress_fx_sovereign"]["exposure_share_pct"] == 53
    assert tests["stress_rollover"]["base_share_pct"] == 10


def test_complete_bilingual_reader_covers_explicit_product_topics():
    base = load_json("web/public/theory-corpus.json")
    supplement = load_json("web/public/theory-supplement.json")
    ids = {c["id"] for c in base["chapters"] + supplement["chapters"]}
    required = {"money-circuit", "institutional-sectors", "stocks-flows", "flow-of-funds", "bank-money", "credit-deposits", "bnr-monetary-policy", "fiscal-debt", "government-securities", "external-sector", "saving-investment", "assets-liabilities", "feedback-delays", "macro-imbalances", "calibration-validation", "model-limits", "what-is-money", "from-whom-to-whom", "esa-instruments", "sector-households", "sector-nfcs", "sector-financial", "sector-government", "sector-external-niip", "mismatches", "interest-debt-service", "accounting-stress-vs-behaviour", "validation-boundary"}
    assert required <= ids
    for c in base["chapters"] + supplement["chapters"]:
        assert c["title"]["en"] and c["title"]["ro"]
        assert c["summary"]["en"] and c["summary"]["ro"]
        for section in c["sections"]:
            assert section["paragraphs"]["en"] and section["paragraphs"]["ro"]
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    assert 'id="open-manual"' in html
    assert "showReader('manual')" in js
    assert "Complete Theory / Learn reader" in js


def test_usefulness_gate_is_wired_end_to_end():
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    # 1 Who funds government? sector liabilities + bilateral matrix
    assert "WHO FUNDS IT?" in js and 'id="flow-matrix"' in html
    # 2 Who holds sector claims? holder/issuer matrix and sector assets
    assert "WHO DOES IT FUND?" in js and "Holder / creditor" in js
    # 3 Net creditor/debtor status where supportable
    assert "NET FINANCIAL POSITION" in js
    # 4 Main imbalances
    assert 'id="diagnostic-cards"' in html
    # 5 Exposed sectors and direct propagation
    assert "Can directly affect" in js and "selectDiagnostic" in js
    # 6 Mechanical shock channel
    assert 'id="stress-tests"' in html and "runStress" in js
    # 7 Observed/accounting vs candidate
    assert "epistemicClass" in js and "roleLabel" in js
    # 8 Explicit simulation boundary
    assert "behavioural simulation remains unavailable" in html


def test_accessibility_adaptive_layout_and_no_flatpak_regression():
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    css = (ROOT / "web/styles.css").read_text(encoding="utf-8")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    assert 'class="skip-link"' in html
    assert 'aria-live="polite"' in html
    assert ':focus-visible' in css
    assert '@media(max-width:900px)' in css
    assert '@media(max-width:560px)' in css
    assert '@media(prefers-reduced-motion:reduce)' in css
    assert "e.key==='Enter'" in js and "e.key===' '" in js
    assert not (ROOT / "native").exists()
