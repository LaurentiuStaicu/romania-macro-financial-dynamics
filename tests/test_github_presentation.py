from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_header_matches_infoclar_suite_contract_before_pages_activation():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    header = readme.split("> **Alpha", 1)[0]

    assert '<img src="web/public/icon.svg" width="96" height="96"' in header
    assert '<h1 align="center">Romania Macro-Financial Dynamics</h1>' in header

    # Exactly the three status badges requested for the suite header.
    assert 'badge/Version-0.5.1a0-' in header
    assert 'badge/elementary_OS-Planned-' in header
    assert 'badge/License-MIT-' in header
    for forbidden in (
        'badge/stage-',
        'badge/InfoClar_Web-',
        'badge/behavioural_simulator-',
        'badge/languages-',
        'badge/Flatpak-deferred',
    ):
        assert forbidden not in header

    # Equal-width CTAs; activation happens only after public deployment is verified.
    assert 'width="220" alt="Open Web App — Planned"' in header
    assert 'width="220" alt="Download Flatpak — Planned"' in header
    assert '<a href="https://laurentiustaicu.github.io/romania-macro-financial-dynamics/">' not in header


def test_pages_workflow_separates_build_from_main_only_deployment():
    workflow = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    assert "  build:" in workflow
    assert "  deploy:" in workflow
    assert "needs: build" in workflow
    assert "github.ref == 'refs/heads/main'" in workflow
    assert "actions/upload-pages-artifact@v4" in workflow
    assert "actions/deploy-pages@v4" in workflow
    assert "path: dist/pages" in workflow
    assert "python scripts/build_web.py" in workflow


def test_pages_build_is_reference_web_only_and_simulator_gated():
    build_script = (ROOT / "scripts/build_web.py").read_text(encoding="utf-8")
    assert 'SOURCE = ROOT / "web"' in build_script
    assert 'DESTINATION = ROOT / "dist" / "pages"' in build_script
    assert 'interactive_simulation_enabled' in build_script
    assert 'NO_GO_FOR_BEHAVIOURAL_SIMULATION' in build_script
    assert not (ROOT / "native").exists()
