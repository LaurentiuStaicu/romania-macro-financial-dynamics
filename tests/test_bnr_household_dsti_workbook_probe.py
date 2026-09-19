from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"model"/"calibration_validation"/"bnr_household_dsti_workbook_probe_contract.json"
SCRIPT=ROOT/"scripts"/"audit_bnr_household_dsti_workbook_probe.py"

spec=importlib.util.spec_from_file_location("probe",SCRIPT)
module=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

class BnrHouseholdDstiWorkbookProbeTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_exact_official_urls_are_frozen(self):
        urls=[x["url"] for x in self.c["candidate_workbooks"]]
        self.assertEqual(len(urls),7)
        self.assertTrue(all("bnr.ro/" in u for u in urls))
        self.assertTrue(any("2024-5-banklendingsurvey" in u for u in urls))
        self.assertTrue(any("2025-02sondajbls" in u for u in urls))

    def test_binary_signatures_distinguish_spreadsheets_from_html(self):
        self.assertEqual(module.signature(bytes.fromhex("D0CF11E0A1B11AE1")+b"x"),"OLE2_CFBF_D0CF11E0A1B11AE1")
        self.assertEqual(module.signature(b"PK\x03\x04rest"),"ZIP_PK_0304")
        self.assertEqual(module.signature(b"<html>request rejected</html>"),"OTHER")

    def test_no_value_extraction_or_estimation_is_authorized(self):
        rules=self.c["probe_rules"]
        self.assertTrue(rules["no_value_extraction"])
        self.assertTrue(rules["no_chart_digitisation"])
        hard=self.c["hard_rules"]
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_household_consumption_outcome_access"])
        self.assertTrue(hard["no_dsti_semantic_substitution"])

if __name__=="__main__":
    unittest.main()
