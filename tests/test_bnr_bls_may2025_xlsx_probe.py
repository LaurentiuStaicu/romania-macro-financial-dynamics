from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"model"/"calibration_validation"/"bnr_bls_may2025_xlsx_probe_contract.json"

class BnrBlsMay2025XlsxProbeTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads(P.read_text(encoding="utf-8"))

    def test_two_exact_official_xlsx_urls_are_frozen(self):
        urls=[x["url"] for x in self.c["candidates"]]
        self.assertEqual(len(urls),2)
        self.assertTrue(all(u.endswith(".xlsx") for u in urls))
        self.assertTrue(all("bnr.ro/uploads/" in u for u in urls))

    def test_probe_is_identity_and_access_only(self):
        r=self.c["rules"]
        self.assertTrue(r["compare_candidate_hashes"])
        self.assertTrue(r["no_workbook_parsing_in_live_probe"])
        self.assertTrue(r["no_sheet_selection"])
        self.assertTrue(r["no_value_extraction"])
        h=self.c["hard_rules"]
        self.assertTrue(h["no_parameter_estimation"])
        self.assertTrue(h["no_model_selection"])
        self.assertTrue(h["no_bls_series_construction"])

if __name__=="__main__":
    unittest.main()
