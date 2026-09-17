from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
TOKENS = (ROOT / "web/suite-tokens.css").read_text(encoding="utf-8")
STYLES = (ROOT / "web/styles.css").read_text(encoding="utf-8")
HTML = (ROOT / "web/index.html").read_text(encoding="utf-8")
CONTRACT = json.loads((ROOT / "web/world3-visual-parity-contract.json").read_text(encoding="utf-8"))


def token(name: str) -> str:
    match = re.search(rf"{re.escape(name)}\s*:\s*([^;]+);", TOKENS)
    assert match, f"missing token {name}"
    return match.group(1).strip()


def test_parity_contract_is_pinned_to_world3_product_recovery():
    assert CONTRACT["canonical_repository"] == "LaurentiuStaicu/world3-empirical-flatpak"
    assert CONTRACT["canonical_pr"] == 10
    assert CONTRACT["canonical_branch"] == "product/world3-usefulness-recovery"
    assert CONTRACT["canonical_head"] == "51e236b61a0ec169bc8f28d4f8192e450ab6bd6d"
    assert CONTRACT["canonical_file"] == "web/src/style.css"
    assert CONTRACT["automatic_dark_mode"] is False


def test_world3_product_recovery_shared_primitives_are_exact():
    p = CONTRACT["shared_primitives"]
    assert p["font_family"] in TOKENS
    mapping = {
        "root_background": "--suite-root-background",
        "page_background": "--suite-page-background",
        "surface": "--suite-surface",
        "text": "--suite-text",
        "muted_text": "--suite-text-muted",
        "border": "--suite-border",
        "link": "--suite-link",
        "shadow": "--suite-shadow",
        "panel_radius": "--suite-panel-radius",
        "control_radius": "--suite-control-radius",
        "control_border": "--suite-control-border",
        "control_hover": "--suite-control-hover",
        "language_active": "--suite-control-active",
        "language_active_text": "--suite-control-active-text",
        "header_height": "--suite-header-height",
        "header_gap": "--suite-header-gap",
        "brand_gap": "--suite-brand-gap",
        "brand_icon_size": "--suite-brand-icon-size",
        "title_size": "--suite-title-size",
        "subtitle_size": "--suite-subtitle-size",
        "main_max_width": "--suite-main-max-width",
        "primary_panel_gap": "--suite-primary-gap",
        "question_band_min_height": "--suite-question-min-height",
        "question_band_margin_bottom": "--suite-question-margin-bottom",
        "mobile_brand_icon_size": "--suite-mobile-brand-icon-size",
        "mobile_primary_radius": "--suite-mobile-panel-radius",
    }
    for contract_key, token_name in mapping.items():
        assert token(token_name) == p[contract_key], f"{contract_key} drifted from World3"
    assert f"{token('--suite-header-padding-y')} {token('--suite-header-padding-x')}" == p["header_padding"]
    assert f"{token('--suite-main-padding-y')} {token('--suite-main-padding-x')} {token('--suite-main-padding-bottom')}" == p["main_padding"]
    assert f"{token('--suite-mobile-header-padding-y')} {token('--suite-mobile-header-padding-x')}" == p["mobile_header_padding"]
    assert f"{token('--suite-mobile-main-padding-y')} {token('--suite-mobile-main-padding-x')} {token('--suite-mobile-main-padding-bottom')}" == p["mobile_main_padding"]


def test_macro_cannot_reintroduce_old_suite_or_macro_dark_mode():
    assert '@import url("suite-tokens.css")' in STYLES
    for legacy in (
        "#2457d6", "#172033", "#d8dfeb", "#28313d", "#f5f6f8", "#dfe3e8",
        "0 8px 28px rgba(35, 45, 60, 0.08)", "76px"
    ):
        assert legacy not in STYLES
        assert legacy not in TOKENS
    assert "color-scheme: light dark" not in STYLES
    assert "prefers-color-scheme: dark" not in STYLES
    assert "prefers-color-scheme: dark" not in TOKENS


def test_header_is_world3_product_recovery_component_grammar():
    assert 'class="product-header"' in HTML
    assert 'class="brand"' in HTML
    assert 'class="lang"' in HTML
    assert 'class="quiet"' in HTML
    assert 'class="suite-header"' not in HTML
    assert 'header-meta' not in HTML
    assert 'nav-chip' not in HTML
    assert 'width="42" height="42"' in HTML
    assert "min-height:var(--suite-header-height)" in STYLES
    assert "gap:var(--suite-header-gap)" in STYLES


def test_page_shell_matches_world3_product_recovery_grammar():
    assert 'class="question-band"' in HTML
    assert "max-width:var(--suite-main-max-width)" in STYLES
    assert "padding:var(--suite-main-padding-y) var(--suite-main-padding-x) var(--suite-main-padding-bottom)" in STYLES
    assert "box-shadow:var(--suite-shadow)" in STYLES
    assert "border-radius:var(--suite-panel-radius)" in STYLES
    assert "grid-template-columns:minmax(0,3fr) minmax(270px,1fr)" in STYLES


def test_flow_of_funds_function_and_progressive_disclosure_are_preserved():
    assert HTML.index('id="model-panel"') < HTML.index('id="dashboard-panel"')
    assert 'FLOW-OF-FUNDS / SECTORAL BALANCE-SHEET EXPLORER' in HTML
    for id_ in ("stock-view", "flow-view", "matrix-tab", "layer-toolbar", "system-map", "map-inspector", "flow-matrix"):
        assert f'id="{id_}"' in HTML
    assert '<details id="theory-panel"' in HTML
    assert '<details id="stress-panel"' in HTML
    assert '<details id="auxiliary-panel"' in HTML


def test_semantic_overlays_do_not_redefine_suite_chrome():
    for semantic in ("--risk-high", "--risk-moderate", "--risk-low", "--flow-observed", "--flow-conceptual", "--flow-candidate"):
        assert semantic in STYLES
    for forbidden_redefinition in ("--suite-page-background:", "--suite-surface:", "--suite-text:", "--suite-border:", "--suite-shadow:"):
        assert forbidden_redefinition not in STYLES


def test_responsive_grammar_matches_world3_product_recovery_breakpoints():
    compact = STYLES.replace(" ", "")
    assert "@media(max-width:1180px)" in compact
    assert "@media(max-width:980px)" in compact
    assert "@media(max-width:680px)" in compact
    assert "@media(max-width:420px)" in compact
    assert "overflow-x:clip" in compact
    assert "@media(prefers-reduced-motion:reduce)" in compact


def test_scientific_state_is_unchanged_by_strict_visual_recovery():
    architecture = json.loads((ROOT / "web/public/product-architecture.json").read_text(encoding="utf-8"))
    science = architecture["scientific_state"]
    assert science["results_alpha_0_1_to_0_5_2_frozen"] is True
    assert science["alpha_0_6_behavioural_simulator_gate"] == "NO_GO"
    assert science["behavioural_simulation_enabled"] is False
    assert science["validated_behavioural_reference_mechanisms"] == 0
    assert science["prospective_monetary_confirmation_unchanged"] is True
