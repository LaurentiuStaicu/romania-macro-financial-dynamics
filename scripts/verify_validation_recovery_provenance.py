from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "provenance" / "validation_recovery_vintage_status.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def valid_sha256(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(character in "0123456789abcdef" for character in value)


def legacy_attempts(entry: dict[str, object]) -> dict[str, dict[str, object]]:
    manifest_path = ROOT / str(entry["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    attempts = manifest.get("attempts", [])
    expected_count = int(entry["known_raw_sha256_count"])
    if len(attempts) != expected_count:
        raise RuntimeError(
            f"Legacy vintage expected {expected_count} raw hashes, found {len(attempts)}"
        )
    result = {}
    for attempt in attempts:
        digest = attempt.get("sha256")
        if not valid_sha256(digest):
            raise RuntimeError(f"Invalid legacy SHA-256 for {attempt.get('name')}")
        result[str(attempt["name"])] = attempt
    return result


def verify_legacy_hash_only(entry: dict[str, object]) -> None:
    legacy_attempts(entry)
    if entry.get("raw_payloads_materialized_in_repository") is not False:
        raise RuntimeError("HASH_ONLY_LEGACY must not claim retained raw payloads")
    if entry.get("exact_vintage_reproducible_from_release") is not False:
        raise RuntimeError("HASH_ONLY_LEGACY must not claim exact reproducibility")


def verify_partial_raw_recovery(entry: dict[str, object]) -> None:
    historical = legacy_attempts(entry)
    recovery_path = ROOT / str(entry["recovery_manifest"])
    recovery = json.loads(recovery_path.read_text(encoding="utf-8"))
    snapshot_root = recovery_path.parent

    recovered = 0
    unrecovered = 0
    for source in recovery["sources"]:
        name = source["name"]
        if name not in historical:
            raise RuntimeError(f"Recovery manifest contains unknown source: {name}")
        legacy_sha = historical[name]["sha256"]
        if source["legacy_sha256"] != legacy_sha:
            raise RuntimeError(f"Recovery manifest legacy hash drift for {name}")

        if source["status"] == "BYTE_IDENTICAL_RECOVERED":
            path = snapshot_root / source["path"]
            if not path.is_file():
                raise RuntimeError(f"Recovered payload missing: {path}")
            observed = sha256_file(path)
            if observed != legacy_sha:
                raise RuntimeError(
                    f"Recovered payload hash mismatch for {name}: {observed} != {legacy_sha}"
                )
            if source["live_sha256"] != legacy_sha:
                raise RuntimeError(f"Recovered source was not byte-identical: {name}")
            recovered += 1
        elif source["status"] == "NOT_RECOVERED_RAW_HASH_MISMATCH":
            if source.get("path"):
                raise RuntimeError(f"Unrecovered source must not expose a legacy raw path: {name}")
            if source["live_sha256"] == legacy_sha:
                raise RuntimeError(f"Source marked mismatch but hashes are identical: {name}")
            unrecovered += 1
        else:
            raise RuntimeError(f"Unknown recovery status for {name}: {source['status']}")

    if recovered != int(entry["raw_payloads_materialized_in_repository"]):
        raise RuntimeError("Recovered raw payload count does not match registry")
    if unrecovered != int(entry["raw_payloads_not_recovered"]):
        raise RuntimeError("Unrecovered raw payload count does not match registry")
    if recovery["complete_raw_vintage_recovered"] is not False:
        raise RuntimeError("Partial recovery must not claim complete raw recovery")
    if entry["exact_vintage_reproducible_from_repository"] is not False:
        raise RuntimeError("Partial recovery must not claim exact complete vintage reproducibility")


def verify_archived_raw(entry: dict[str, object]) -> None:
    manifest_path = ROOT / str(entry["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    snapshot_root = manifest_path.parent

    for attempt in manifest.get("attempts", []):
        path = snapshot_root / attempt["path"]
        if not path.is_file():
            raise RuntimeError(f"Missing retained raw payload: {path}")
        observed = sha256_file(path)
        if observed != attempt["sha256"]:
            raise RuntimeError(
                f"Raw payload hash mismatch for {attempt['name']}: "
                f"{observed} != {attempt['sha256']}"
            )

    for item in manifest.get("normalized_series", {}).values():
        path = snapshot_root / item["path"]
        if not path.is_file():
            raise RuntimeError(f"Missing normalized payload: {path}")
        observed = sha256_file(path)
        if observed != item["sha256"]:
            raise RuntimeError(f"Normalized payload hash mismatch: {path}")

    fetcher = ROOT / manifest["fetcher_script"]
    if not fetcher.is_file():
        raise RuntimeError(f"Missing fetcher script: {fetcher}")
    if sha256_file(fetcher) != manifest["fetcher_script_sha256"]:
        raise RuntimeError("Fetcher script hash does not match retained vintage manifest")


def main() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    for entry in registry["vintages"]:
        status = entry["status"]
        if status == "HASH_ONLY_LEGACY":
            verify_legacy_hash_only(entry)
        elif status == "PARTIAL_RAW_RECOVERY":
            verify_partial_raw_recovery(entry)
        elif status == "ARCHIVED_RAW_VERIFIED":
            verify_archived_raw(entry)
        else:
            raise RuntimeError(f"Unknown provenance status: {status}")
        print(f"{entry['id']}: {status} verified")


if __name__ == "__main__":
    main()
