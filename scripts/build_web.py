from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web"
DESTINATION = ROOT / "dist" / "pages"

REQUIRED = (
    "index.html",
    "suite-tokens.css",
    "world3-visual-parity-contract.json",
    "styles.css",
    "app.js",
    "theory-merge.js",
    "anchor-scroll.js",
    "public/icon.svg",
    "public/model-stage.json",
    "public/product-architecture.json",
    "public/theory-corpus.json",
    "public/theory-supplement.json",
)


def main() -> None:
    for relative in REQUIRED:
        if not (SOURCE / relative).is_file():
            raise SystemExit(f"Missing required web input: {relative}")

    snapshot = json.loads((SOURCE / "public/model-stage.json").read_text(encoding="utf-8"))
    architecture = json.loads((SOURCE / "public/product-architecture.json").read_text(encoding="utf-8"))
    theory = json.loads((SOURCE / "public/theory-corpus.json").read_text(encoding="utf-8"))
    supplement = json.loads((SOURCE / "public/theory-supplement.json").read_text(encoding="utf-8"))
    parity = json.loads((SOURCE / "world3-visual-parity-contract.json").read_text(encoding="utf-8"))

    if snapshot["product"]["interface"] != "InfoClar":
        raise SystemExit("Pages build must publish the canonical InfoClar web surface")
    if snapshot["stage"]["interactive_simulation_enabled"] is not False:
        raise SystemExit("Behavioural simulation must remain disabled while the scientific gate is NO-GO")
    if snapshot["validation"]["alpha_0_6_gate"] != "NO_GO_FOR_BEHAVIOURAL_SIMULATION":
        raise SystemExit("Pages build refuses to publish a simulator-ready claim inconsistent with the scientific gate")
    if architecture["stage_type"] != "cross_cutting_product_architecture_recovery":
        raise SystemExit("Pages build requires the Product Architecture Recovery map contract")
    if architecture["scientific_state"]["behavioural_simulation_enabled"] is not False:
        raise SystemExit("Product architecture must not enable behavioural simulation")
    if architecture["scientific_state"]["validated_behavioural_reference_mechanisms"] != 0:
        raise SystemExit("Strict visual recovery cannot alter validated behavioural mechanism count")
    if len(architecture["edges"]) < 20 or len(architecture["layers"]) < 7:
        raise SystemExit("Pages build refuses regression to a symbolic low-information map")
    if len(theory["chapters"]) < 18 or theory["default_language"] != "en":
        raise SystemExit("Pages build requires the base bilingual Theory/Learn corpus")
    supplement_ids = {chapter["id"] for chapter in supplement["chapters"]}
    required_supplement = {"what-is-money", "from-whom-to-whom", "esa-instruments", "sector-households", "sector-nfcs", "sector-financial", "sector-government", "sector-external-niip", "mismatches", "interest-debt-service", "accounting-stress-vs-behaviour", "validation-boundary"}
    if not required_supplement <= supplement_ids:
        raise SystemExit("Pages build requires the complete product-theory supplement")
    if parity["canonical_head"] != "51e236b61a0ec169bc8f28d4f8192e450ab6bd6d" or parity["automatic_dark_mode"] is not False:
        raise SystemExit("Pages build requires the pinned World3 Product Recovery parity contract")

    if DESTINATION.exists():
        shutil.rmtree(DESTINATION)
    shutil.copytree(SOURCE, DESTINATION, ignore=shutil.ignore_patterns("README.md"))
    (DESTINATION / ".nojekyll").write_text("", encoding="utf-8")

    html = (DESTINATION / "index.html").read_text(encoding="utf-8")
    for forbidden in ('href="/', 'src="/'):
        if forbidden in html:
            raise SystemExit(f"Project-site-incompatible absolute path found: {forbidden}")
    if 'class="product-header"' not in html or 'class="question-band"' not in html:
        raise SystemExit("Macro shell must use the World3 Product Recovery header and question-band grammar")

    styles = (DESTINATION / "styles.css").read_text(encoding="utf-8")
    tokens = (DESTINATION / "suite-tokens.css").read_text(encoding="utf-8")
    if '@import url("suite-tokens.css")' not in styles:
        raise SystemExit("Macro must import the strict World3 suite token file")
    if "prefers-color-scheme: dark" in styles or "prefers-color-scheme: dark" in tokens or "color-scheme: light dark" in styles:
        raise SystemExit("Macro-only automatic dark mode is forbidden by the strict World3 parity contract")

    print(f"Built InfoClar Pages artifact at {DESTINATION}")


if __name__ == "__main__":
    main()
