from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web"
DESTINATION = ROOT / "dist" / "pages"

REQUIRED = (
    "index.html",
    "styles.css",
    "app.js",
    "public/icon.svg",
    "public/model-stage.json",
    "public/product-architecture.json",
    "public/product-contract-v2.json",
    "public/theory-corpus.json",
    "public/theory-corpus-v2.json",
)


def main() -> None:
    for relative in REQUIRED:
        if not (SOURCE / relative).is_file():
            raise SystemExit(f"Missing required web input: {relative}")

    snapshot = json.loads((SOURCE / "public/model-stage.json").read_text(encoding="utf-8"))
    architecture = json.loads((SOURCE / "public/product-architecture.json").read_text(encoding="utf-8"))
    contract = json.loads((SOURCE / "public/product-contract-v2.json").read_text(encoding="utf-8"))
    theory = json.loads((SOURCE / "public/theory-corpus-v2.json").read_text(encoding="utf-8"))

    if snapshot["product"]["interface"] != "InfoClar":
        raise SystemExit("Pages build must publish the canonical InfoClar web surface")
    if snapshot["stage"]["interactive_simulation_enabled"] is not False:
        raise SystemExit("Behavioural simulation must remain disabled while the scientific gate is NO-GO")
    if snapshot["validation"]["alpha_0_6_gate"] != "NO_GO_FOR_BEHAVIOURAL_SIMULATION":
        raise SystemExit("Pages build refuses a behavioural-simulation claim inconsistent with the scientific gate")
    if architecture["stage_type"] != "cross_cutting_product_architecture_recovery":
        raise SystemExit("Pages build requires the Product Architecture Recovery data contract")
    if architecture["scientific_state"]["behavioural_simulation_enabled"] is not False:
        raise SystemExit("Product architecture must not enable behavioural simulation")
    if len(architecture["edges"]) < 20 or len(architecture["layers"]) < 7:
        raise SystemExit("Pages build refuses regression to a symbolic low-information map")

    if contract["primary_object"] != "FLOW_OF_FUNDS_EXPLORER" or not contract["accounting_spine_first"]:
        raise SystemExit("Primary product object must be the Accounting-Spine-first Flow-of-Funds Explorer")
    if contract["default_perspective"] != "stock" or contract["default_layer"] != "balance":
        raise SystemExit("Default product state must begin with the stock/balance-sheet view, not all layers")
    if "overview" in contract["layer_order"]:
        raise SystemExit("Normal product controls must never activate all layers simultaneously")
    if contract["behavioural_simulation_enabled"] is not False or contract["validated_behavioural_reference_mechanisms"] != 0:
        raise SystemExit("Product recovery must not enable behavioural simulation")
    if contract["flatpak_started"] is not False:
        raise SystemExit("Flatpak work is out of scope for Product Architecture Recovery")

    chapter_ids = {chapter["id"] for chapter in theory["chapters"]}
    missing_topics = set(contract["theory_required_topics"]) - chapter_ids
    if missing_topics:
        raise SystemExit(f"Theory/Learn missing required chapters: {sorted(missing_topics)}")
    if theory["default_language"] != "en" or len(theory["chapters"]) < 36:
        raise SystemExit("Pages build requires the complete bilingual Theory/Learn v2 corpus")

    html = (SOURCE / "index.html").read_text(encoding="utf-8")
    for forbidden in ("Alpha 0.6", "software_version", "registry", "test count", "ALL LAYERS"):
        if forbidden in html:
            raise SystemExit(f"Normal frontend contains forbidden implementation/scientific metadata: {forbidden}")
    for required_id in ("stock-tab", "flow-tab", "layer-toolbar", "flow-matrix", "diagnostic-cards", "stress-tests", "theory-reader", "research-provenance"):
        if f'id="{required_id}"' not in html:
            raise SystemExit(f"Missing required product surface: {required_id}")

    if DESTINATION.exists():
        shutil.rmtree(DESTINATION)
    shutil.copytree(SOURCE, DESTINATION, ignore=shutil.ignore_patterns("README.md"))
    (DESTINATION / ".nojekyll").write_text("", encoding="utf-8")

    built_html = (DESTINATION / "index.html").read_text(encoding="utf-8")
    for forbidden in ('href="/', 'src="/'):
        if forbidden in built_html:
            raise SystemExit(f"Project-site-incompatible absolute path found: {forbidden}")

    print(f"Built Flow-of-Funds InfoClar Pages artifact at {DESTINATION}")


if __name__ == "__main__":
    main()
