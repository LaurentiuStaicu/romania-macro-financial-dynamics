from __future__ import annotations

import unittest

import scripts.run_corporate_investment_structural_selection as runner


class CorporateInvestmentSelectionRunnerTests(unittest.TestCase):
    def test_runner_prerequisites_are_exact_and_default_execution_is_closed(self):
        contract = runner.load_contract()
        prerequisites = runner.verify_prerequisites(contract)
        self.assertEqual(
            prerequisites["source_sha256"],
            "d8d3765fe9e83bd29620de1d02e914626a5f5e1b4071e005ff138b55f127ba69",
        )
        self.assertFalse(runner.execution_is_authorized(contract))

    def test_selection_reader_never_reads_final_holdout(self):
        contract = runner.load_contract()
        records = runner.read_selection_records(contract)
        self.assertEqual(records[-1]["period"], "2023-Q4")
        self.assertNotIn("2024-Q1", {row["period"] for row in records})

    def test_contract_itself_never_authorizes_final_evaluation(self):
        contract = runner.load_contract()
        self.assertFalse(
            contract["estimation_authorization"]["authorized_by_this_contract"]
        )
        self.assertIn("final_evaluation", contract["windows"])


if __name__ == "__main__":
    unittest.main()
