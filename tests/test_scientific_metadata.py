from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ScientificMetadataTests(unittest.TestCase):
    def test_package_description_respects_current_model_maturity(self) -> None:
        project = tomllib.loads(
            (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )["project"]
        description = str(project["description"]).lower()

        self.assertIn("accounting-constrained", description)
        self.assertIn("stock-flow-consistent dynamic model", description)
        self.assertNotIn("system-dynamics model", description)

    def test_citation_abstract_respects_current_model_maturity(self) -> None:
        citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        match = re.search(r'^abstract:\s*"([^"]+)"\s*$', citation, re.MULTILINE)
        self.assertIsNotNone(match)

        abstract = match.group(1).lower()
        self.assertIn("accounting-constrained", abstract)
        self.assertIn("stock-flow-consistent dynamic research model", abstract)
        self.assertIn(
            "under development toward an endogenous system dynamics reference model",
            abstract,
        )
        self.assertNotIn("system-dynamics research model", abstract)

    def test_readme_keeps_behavioural_closure_boundary_explicit(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()

        self.assertIn("behavioural closure is inactive", readme)
        self.assertIn(
            "not yet a complete endogenous system dynamics model",
            readme,
        )


if __name__ == "__main__":
    unittest.main()
