from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEW = (
    ROOT
    / "model"
    / "calibration_validation"
    / "sovereign_yield_source_vintage_promotion_review.json"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: verify_sovereign_yield_vintage_promotion.py "
            "<artifact_dir> <destination_dir>"
        )

    artifact_dir = Path(sys.argv[1]).resolve()
    destination_dir = Path(sys.argv[2]).resolve()
    review = json.loads(REVIEW.read_text(encoding="utf-8"))

    if review["verdict"] != "PASS_EXACT_REVIEWED_ARTIFACT_ELIGIBLE_FOR_PROMOTION":
        raise RuntimeError("promotion review is not PASS")
    if review["estimation_authorized"]:
        raise RuntimeError("promotion review must not authorize estimation")

    expected = {item["path"]: item for item in review["expected_files"]}
    actual = {
        str(path.relative_to(artifact_dir))
        for path in artifact_dir.rglob("*")
        if path.is_file()
    }
    if actual != set(expected):
        raise RuntimeError(
            f"artifact file set mismatch: missing={sorted(set(expected)-actual)} "
            f"extra={sorted(actual-set(expected))}"
        )

    for relative, meta in expected.items():
        path = artifact_dir / relative
        if path.stat().st_size != meta["bytes"]:
            raise RuntimeError(f"byte-size mismatch: {relative}")
        if sha256(path) != meta["sha256"]:
            raise RuntimeError(f"sha256 mismatch: {relative}")

    manifest = json.loads(
        (artifact_dir / "snapshot_manifest.json").read_text(encoding="utf-8")
    )
    if manifest["snapshot_id"] != review["snapshot_id"]:
        raise RuntimeError("snapshot_id mismatch")
    if (
        manifest["fetcher_script_sha256"]
        != review["provenance"]["fetcher_script_sha256"]
    ):
        raise RuntimeError("fetcher script sha256 mismatch")
    if manifest["canonical_promotion"] != (
        "REQUIRES_EXPLICIT_REPOSITORY_REVIEW_AND_COMMIT"
    ):
        raise RuntimeError("unexpected canonical promotion state")

    if destination_dir.exists():
        raise RuntimeError(f"destination already exists: {destination_dir}")
    destination_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(artifact_dir, destination_dir)

    copied = {
        str(path.relative_to(destination_dir))
        for path in destination_dir.rglob("*")
        if path.is_file()
    }
    if copied != set(expected):
        raise RuntimeError("copied snapshot file set mismatch")

    print(
        json.dumps(
            {
                "snapshot_id": review["snapshot_id"],
                "files_verified": len(expected),
                "destination": str(destination_dir),
                "estimation_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
