from __future__ import annotations

import json
import sys
from pathlib import Path


def load_json(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: check_json_semantic_equivalence.py RETAINED_JSON REGENERATED_JSON"
        )

    retained_path, regenerated_path = sys.argv[1:]
    retained = load_json(retained_path)
    regenerated = load_json(regenerated_path)

    if retained != regenerated:
        raise SystemExit(
            f"semantic JSON mismatch: {retained_path} != {regenerated_path}"
        )

    print(
        f"semantic JSON match: {retained_path} == {regenerated_path}"
    )


if __name__ == "__main__":
    main()
