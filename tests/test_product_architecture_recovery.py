import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def test_recovery_keeps_science_frozen_and_alpha_0_6_no_go():
    contract = load_json("model/registries/product_architecture_recovery.json")
    architecture = load_json("web/public/product-architecture.json")
    snapshot = load_json("web/public/model-stage.json")
    science = contract["scientific_invariance"]
    assert contract["stage_type"] == "cross_cutting_product_architecture_recovery"
    assert science["validated_behavioural_reference_mechanisms"] == 0
    assert science["alpha_0_6_gate"] == "NO_GO"
    assert science["behavioural_simulator_enabled"] is False
    assert science["no_synthetic_missing_values"] is True
    assert architecture["scientific_state"]["validated_behavioural_reference_mechanisms"] == 0
    assert architecture["scientific_state"]["prospective_monetary_confirmation_unchanged"] is True
    assert snapshot["validation"]["alpha_0_6_gate"] == "NO_GO_FOR_BEHAVIOURAL_SIMULATION"


def test_primary_object_is_flow_of_funds_sectoral_balance_sheet_not_symbolic_six_circles():
    architecture = load_json("web/public/product-architecture.json")
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    assert {n["id"] for n in architecture["nodes"]} == {"H", "C", "F", "G", "BNR", "X"}
    assert {l["id"] for l in architecture["layers"]} == {"overview", "real", "fiscal", "financial", "balance", "external", "feedback"}
    assert len(architecture["edges"]) >= 20
    assert 'id="matrix-view"' in html and 'id="flow-matrix"' in html
    assert "renderMatrix" in js and "Holder / creditor" in js
    assert sum(1 for e in architecture["edges"] if e.get("is_financial_position")) >= 7
    assert {e.get("instrument") for e in architecture["edges"]} >= {"F2", "F3", "F4"}


def test_relationships_distinguish_real_fiscal_positions_transactions_revaluations_and_candidates():
    architecture = load_json("web/public/product-architecture.json")
    edges = architecture["edges"]
    classes = {e["accounting_class"] for e in edges}
    assert {"FLOW", "STOCK", "REVALUATION_OTHER_FLOW", "BEHAVIOURAL_CANDIDATE"} <= classes
    layers = {e["layer"] for e in edges}
    assert {"real", "fiscal", "financial", "balance", "external", "feedback"} <= layers
    for e in edges:
        assert e["definition"]["en"] and e["definition"]["ro"]
        assert e["epistemic_role"]
        assert "value" in e and "period" in e and "unit" in e
        assert e["affects"]
        assert e["limit"]["en"] and e["limit"]["ro"]
        if e["value"] is None:
            assert e["value"] is not 0


def test_sector_click_can_answer_assets_liabilities_counterparties_flows_and_vulnerability():
    architecture = load_json("web/public/product-architecture.json")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    for n in architecture["nodes"]:
        assert "asset_edges" in n and "liability_edges" in n
        assert n["net_position"]["en"] and n["net_position"]["ro"]
        assert n["vulnerability"]["en"] and n["vulnerability"]["ro"]
    for needle in ("Assets / claims represented", "Liabilities / funding represented", "Incoming relations", "Outgoing relations", "Vulnerability channels"):
        assert needle in js


def test_edge_click_exposes_definition_direction_instrument_value_period_source_and_epistemic_role():
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    for needle in ("Definition", "Direction", "Instrument", "Accounting class", "Epistemic role", "Value", "Period", "Unit", "Propagation / affected sectors", "Sources"):
        assert needle in js


def test_vulnerability_monitor_is_about_romania_not_software_metadata():
    architecture = load_json("web/public/product-architecture.json")
    diagnostics = {d["id"]: d for d in architecture["diagnostics"]}
    required = {
        "external_imbalance", "niip_external_position", "public_debt_refinancing",
        "currency_mismatch_sovereign", "household_debt", "nfc_leverage",
        "bank_sovereign_exposure", "maturity_mismatch", "credit_growth_gap",
    }
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
    assert 'id="stress-panel"' in html and "ACCOUNTING / EXPOSURE STRESS" in html
    assert "Not a forecast" in js
    assert "fx_share_revaluation" in js and "rollover_share" in js and "market_value" in js and "bilateral_stock" in js
    assert tests["stress_fx_sovereign"]["exposure_share_pct"] == 53
    assert tests["stress_rollover"]["base_share_pct"] == 10


def test_usefulness_gate_is_wired_end_to_end():
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    # 1 complete circuit trace and layers
    assert 'id="system-map"' in html and 'id="layer-toolbar"' in html
    # 2 who holds whose liabilities
    assert 'id="flow-matrix"' in html and "renderMatrix" in js
    # 3 main imbalances
    assert 'id="diagnostic-cards"' in html
    # 4 imbalance -> explanatory relations
    assert "selectDiagnostic" in js and "map_objects" in js
    # 5 observed/accounting/candidate distinction
    assert "epistemicClass" in js and "Epistemic role" in js
    # 6 accounting stress without forecast
    assert 'id="stress-tests"' in html and "runStress" in js
    # 7 theory without README
    assert 'id="theory-reader"' in html and "showReader" in js
    # 8 concrete system insight supported by evidence cards and inspector
    assert 'id="map-inspector"' in html and 'id="auxiliary-content"' in html


def test_theory_reader_remains_bilingual_complete_and_contextual():
    theory = load_json("web/public/theory-corpus.json")
    chapters = {c["id"]: c for c in theory["chapters"]}
    required = {"money-circuit", "institutional-sectors", "stocks-flows", "flow-of-funds", "bank-money", "credit-deposits", "bnr-monetary-policy", "monetary-transmission", "fiscal-debt", "government-securities", "external-sector", "saving-investment", "assets-liabilities", "feedback-delays", "macro-imbalances", "data-provenance", "calibration-validation", "model-limits"}
    assert required <= set(chapters)
    assert len(chapters) >= 18
    for c in chapters.values():
        assert c["title"]["en"] and c["title"]["ro"]
        assert c["summary"]["en"] and c["summary"]["ro"]
        assert c["sections"]
        for section in c["sections"]:
            assert section["paragraphs"]["en"] and section["paragraphs"]["ro"]
    assert len(theory["glossary"]) >= 8 and len(theory["references"]) >= 5


def test_accessibility_adaptive_layout_and_no_flatpak_regression():
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    css = (ROOT / "web/styles.css").read_text(encoding="utf-8")
    js = (ROOT / "web/app.js").read_text(encoding="utf-8")
    assert 'class="skip-link"' in html
    assert 'aria-live="polite"' in html
    assert ':focus-visible' in css
    assert '@media(max-width:900px)' in css
    assert '@media(prefers-reduced-motion:reduce)' in css
    assert "e.key==='Enter'" in js and "e.key===' '" in js
    assert not (ROOT / "native").exists()
