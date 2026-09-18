from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VINTAGE = (
    ROOT / "data" / "source_vintages"
    / "accounting-f4-partial-2025-vintage-2026-09-18"
)


def main() -> None:
    source = json.loads((VINTAGE / "source_manifest.json").read_text(encoding="utf-8"))
    encoded = "".join((VINTAGE / source["archive"]).read_text(encoding="ascii").split())
    archive = base64.b64decode(encoded, validate=True)
    digest = hashlib.sha256(archive).hexdigest()
    if digest != source["decoded_archive_sha256"]:
        raise RuntimeError(f"F4 source-vintage SHA mismatch: {digest}")

    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        component = out / "component.json"
        manifest = out / "manifest.json"
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "generate_f4_partial_from_snapshot.py"),
                "--component-output", str(component),
                "--manifest-output", str(manifest),
            ],
            cwd=ROOT,
            check=True,
        )
        generated = json.loads(manifest.read_text(encoding="utf-8"))

    prov = generated["provenance_verification"]
    if prov["phase_A_raw_responses"] != 420:
        raise RuntimeError("Expected 420 retained Phase A raw responses")
    if prov["phase_B_raw_responses"] != 12:
        raise RuntimeError("Expected 12 retained Phase B W1 raw responses")
    if generated["conditional_stock_cells_promoted"]:
        raise RuntimeError("Conditional BNR-zero stock cells must not be promoted")
    if generated["canonical_benchmark_2025_changed"]:
        raise RuntimeError("Partial F4 materialization must not mutate canonical benchmark")
    if generated["behavioural_closure_changed"]:
        raise RuntimeError("Partial F4 materialization must not change behavioural closure")
    print(
        "F4 source vintage verified offline: exact Phase B artifact digest, "
        "420 Phase A raw responses, 12 Phase B W1 raw responses, and all "
        "partial-materialization guards pass."
    )


if __name__ == "__main__":
    main()
