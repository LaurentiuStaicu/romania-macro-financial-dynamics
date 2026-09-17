from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
TOKENS = (ROOT / "web/suite-tokens.css").read_text(encoding="utf-8")
STYLES = (ROOT / "web/styles.css").read_text(encoding="utf-8")
HTML = (ROOT / "web/index.html").read_text(encoding="utf-8")


def token(name: str) -> str:
    match = re.search(rf"{re.escape(name)}\s*:\s*([^;]+);", TOKENS)
    assert match, f"missing token {name}"
    return match.group(1).strip()


def test_world3_canonical_base_tokens_are_exact():
    assert "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont" in TOKENS
    assert token("--suite-root-background") == "#f5f6f8"
    assert token("--suite-page-background") == "#f8f9fb"
    assert token("--suite-surface") == "#ffffff"
    assert token("--suite-border") == "#dfe3e8"
    assert token("--suite-text") == "#28313d"
    assert token("--suite-text-muted") == "#687384"
    assert token("--suite-accent") == "#5d5fef"
    assert token("--suite-shadow") == "0 8px 28px rgba(35, 45, 60, 0.08)"
    assert token("--suite-panel-radius") == "14px"
    assert token("--suite-control-radius") == "9px"
    assert token("--suite-header-height") == "76px"
    assert token("--suite-brand-icon-size") == "42px"
    assert token("--suite-title-size") == "18px"
    assert token("--suite-subtitle-size") == "12px"


def test_macro_cannot_reintroduce_legacy_visual_system():
    assert '@import url("suite-tokens.css")' in STYLES
    for legacy in ("#2457d6", "#172033", "#d8dfeb", "0 10px 30px rgba(20,38,70,.08)"):
        assert legacy not in STYLES
    assert "border-radius: 16px" not in STYLES


def test_header_uses_world3_suite_grammar_and_integrated_navigation():
    assert 'class="suite-header"' in HTML
    assert 'class="brand-icon"' in HTML
    assert 'class="header-meta"' in HTML
    assert 'class="language-switch"' in HTML
    assert 'class="primary-nav"' not in HTML
    assert 'width="42" height="42"' in HTML


def test_flow_of_funds_remains_dominant_and_secondary_surfaces_are_progressive():
    assert HTML.index('id="model-panel"') < HTML.index('id="dashboard-panel"')
    assert 'FLOW-OF-FUNDS / SECTORAL BALANCE-SHEET EXPLORER' in HTML
    assert '<details id="theory-panel"' in HTML
    assert '<details id="stress-panel"' in HTML
    assert '<details id="auxiliary-panel"' in HTML
    assert "grid-template-columns: minmax(0, 2.1fr) minmax(320px, 0.8fr)" in STYLES


def test_map_clutter_controls_are_visual_not_semantic_rewrites():
    assert ".edge-label" in STYLES
    assert "opacity: 0" in STYLES
    assert ".edge-group:hover .edge-label" in STYLES
    assert ".edge-group:has(.map-edge.related) .edge-label" in STYLES
    assert ".dimmed { opacity: 0.1 !important; }" in STYLES


def test_vulnerability_monitor_uses_calm_progressive_strip():
    assert "grid-auto-flow: column" in STYLES
    assert "overflow-x: auto" in STYLES
    assert ".diagnostic-card > p:not(.diag-value) { display: none; }" in STYLES
    assert ".diagnostic-card.active > p { display: block; }" in STYLES


def test_responsive_and_dark_mode_tokens_are_present():
    assert "@media (max-width: 1120px)" in STYLES
    assert "@media (max-width: 620px)" in STYLES
    assert "overflow-x: hidden" in STYLES
    assert "@media (prefers-color-scheme: dark)" in TOKENS
    assert "--suite-surface: #20242b" in TOKENS
    assert "--suite-page-background: #171a1f" in TOKENS
    assert "--suite-border: #353b44" in TOKENS
    assert "--suite-text-muted: #a4adba" in TOKENS


def test_scientific_state_is_unchanged_by_visual_recovery():
    architecture = json.loads((ROOT / "web/public/product-architecture.json").read_text(encoding="utf-8"))
    science = architecture["scientific_state"]
    assert science["results_alpha_0_1_to_0_5_2_frozen"] is True
    assert science["alpha_0_6_behavioural_simulator_gate"] == "NO_GO"
    assert science["behavioural_simulation_enabled"] is False
    assert science["validated_behavioural_reference_mechanisms"] == 0
    assert science["prospective_monetary_confirmation_unchanged"] is True
