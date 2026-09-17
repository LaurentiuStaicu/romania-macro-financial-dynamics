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
)


def main() -> None:
    for relative in REQUIRED:
        if not (SOURCE / relative).is_file():
            raise SystemExit(f"Missing required web input: {relative}")

    snapshot = json.loads((SOURCE / "public/model-stage.json").read_text(encoding="utf-8"))
    if snapshot["product"]["interface"] != "InfoClar":
        raise SystemExit("Pages build must publish the canonical InfoClar web surface")
    if snapshot["stage"]["interactive_simulation_enabled"] is not False:
        raise SystemExit("Behavioural simulation must remain disabled while the scientific gate is NO-GO")
    if snapshot["validation"]["alpha_0_6_gate"] != "NO_GO_FOR_BEHAVIOURAL_SIMULATION":
        raise SystemExit("Pages build refuses to publish a simulator-ready claim inconsistent with Alpha 0.5.1")

    if DESTINATION.exists():
        shutil.rmtree(DESTINATION)
    shutil.copytree(SOURCE, DESTINATION, ignore=shutil.ignore_patterns("README.md"))
    (DESTINATION / ".nojekyll").write_text("", encoding="utf-8")

    # The project site is served under /romania-macro-financial-dynamics/. All
    # browser assets therefore use document-relative paths; absolute-root paths
    # would break the verified GitHub Pages project-site deployment.
    html = (DESTINATION / "index.html").read_text(encoding="utf-8")
    for forbidden in ('href="/', 'src="/'):
        if forbidden in html:
            raise SystemExit(f"Project-site-incompatible absolute path found: {forbidden}")

    print(f"Built InfoClar Pages artifact at {DESTINATION}")


if __name__ == "__main__":
    main()
