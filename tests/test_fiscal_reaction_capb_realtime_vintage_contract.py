from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "model" / "calibration_validation" / "fiscal_reaction_capb_realtime_vintage_contract.json"
SCRIPT = ROOT / "scripts" / "materialise_fiscal_reaction_capb_realtime_vintages.py"

spec = importlib.util.spec_from_file_location("capb_vintage_materializer", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def make_zip(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, body in files.items():
            archive.writestr(name, body)
    return buffer.getvalue()


class FiscalReactionCapbRealtimeVintageContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.c = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_reopen_scope_is_source_only(self) -> None:
        self.assertEqual(
            self.c["target_series"]["code"],
            "ROM.1.0.319.0.UBLGBPS",
        )
        self.assertFalse(self.c["estimation_authorized"])
        self.assertFalse(self.c["model_selection_authorized"])
        self.assertFalse(self.c["prior_final_evaluation_opening_authorized"])
        self.assertTrue(self.c["hard_rules"]["live_provider_work_manual_only"])
        self.assertTrue(self.c["hard_rules"]["no_later_revision_backfill"])
        self.assertTrue(self.c["hard_rules"]["no_prior_2018_2024_holdout_opening"])

    def test_release_inventory_is_explicit_and_ordered(self) -> None:
        releases = self.c["releases"]
        self.assertGreaterEqual(len(releases), 8)
        dates = [item["release_date"] for item in releases]
        self.assertEqual(dates, sorted(dates))
        self.assertEqual(releases[-1]["id"], "spring_2026")
        self.assertTrue(all(item["source_url"].startswith("https://") for item in releases))

    def test_exact_row_is_recovered_from_nested_zip(self) -> None:
        row = (
            b"ROM.1.0.319.0.UBLGBPS;Romania;meta;"
            b"Structural balance of general government excluding interest;"
            b"(Percentage of potential GDP at current prices);1;2;3\n"
        )
        inner = make_zip({"AMECO17.TXT": b"header\n" + row})
        outer = make_zip({"nested/chapter17.zip": inner})
        result = module.extract_distinct_target_row(
            outer,
            "ROM.1.0.319.0.UBLGBPS",
            max_depth=3,
        )
        self.assertEqual(result["row_bytes"], row)
        self.assertEqual(result["matching_member_count"], 1)
        self.assertEqual(
            result["selected_member_path"],
            "nested/chapter17.zip::AMECO17.TXT",
        )

    def test_byte_identical_duplicate_rows_are_not_ambiguous(self) -> None:
        row = b"ROM.1.0.319.0.UBLGBPS;Romania;x;y;z;1\r\n"
        archive = make_zip({"a.txt": row, "b.txt": row})
        result = module.extract_distinct_target_row(
            archive,
            "ROM.1.0.319.0.UBLGBPS",
        )
        self.assertEqual(result["matching_member_count"], 2)
        self.assertEqual(result["selected_member_path"], "a.txt")
        self.assertEqual(result["row_bytes"], row)

    def test_distinct_duplicate_rows_fail_closed(self) -> None:
        archive = make_zip(
            {
                "a.txt": b"ROM.1.0.319.0.UBLGBPS;Romania;x;y;z;1\n",
                "b.txt": b"ROM.1.0.319.0.UBLGBPS;Romania;x;y;z;2\n",
            }
        )
        with self.assertRaisesRegex(ValueError, "multiple distinct matched rows"):
            module.extract_distinct_target_row(
                archive,
                "ROM.1.0.319.0.UBLGBPS",
            )

    def test_missing_target_fails_closed(self) -> None:
        archive = make_zip({"a.txt": b"OTHER;Romania;x;y;z;1\n"})
        with self.assertRaisesRegex(ValueError, "no exact row found"):
            module.extract_distinct_target_row(
                archive,
                "ROM.1.0.319.0.UBLGBPS",
            )


if __name__ == "__main__":
    unittest.main()
