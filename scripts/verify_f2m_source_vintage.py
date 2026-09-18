from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VINTAGE = ROOT / "data" / "source_vintages" / "accounting-f2m-2025-vintage-2026-09-18"


def main() -> None:
    source = json.loads((VINTAGE / "source_manifest.json").read_text(encoding="utf-8"))
    encoded = "".join((VINTAGE / source["archive"]).read_text(encoding="ascii").split())

    import base64
    archive = base64.b64decode(encoded, validate=True)
    digest = hashlib.sha256(archive).hexdigest()
    if digest != source["decoded_archive_sha256"]:
        raise RuntimeError(f"Decoded F2M source SHA-256 mismatch: {digest}")

    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        component = out / "component.json"
        manifest = out / "manifest.json"
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "generate_f2m_component_from_snapshot.py"),
                "--vintage", str(VINTAGE),
                "--component-output", str(component),
                "--manifest-output", str(manifest),
            ],
            cwd=ROOT,
            check=True,
        )
        generated = json.loads(manifest.read_text(encoding="utf-8"))

    raw = generated["raw_provenance_verification"]
    if raw["phase_a1_distinct_series_keys_with_retained_raw"] != 66:
        raise RuntimeError("Expected 66 distinct A1 retained raw series keys")
    if raw["phase_a2_raw_payloads_sha256_verified"] != 6:
        raise RuntimeError("Expected all six A2 raw payload SHA-256 checks to pass")
    if generated["total_F2_status"] != "INCOMPLETE_BLOCKED_BY_F21_CURRENCY":
        raise RuntimeError("F2M verification must not promote total F2")
    if generated["canonical_total_F2_benchmark_changed"]:
        raise RuntimeError("F2M verification must not change canonical total F2")
    if generated["behavioural_closure_changed"]:
        raise RuntimeError("F2M verification must not change behavioural closure")

    print(
        "F2M source vintage verified offline: exact decoded artifact digest, "
        "66 A1 raw keys, 6 A2 raw payload digests, and total-F2/F21 guards all pass."
    )


if __name__ == "__main__":
    main()
