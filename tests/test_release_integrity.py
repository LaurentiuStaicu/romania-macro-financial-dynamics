from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path

import romania_macro_financial_dynamics as rmd

ROOT = Path(__file__).resolve().parents[1]


class ReleaseIntegrityTests(unittest.TestCase):
    def test_package_version_matches_pyproject(self) -> None:
        with (ROOT / "pyproject.toml").open("rb") as handle:
            project = tomllib.load(handle)["project"]
        self.assertEqual(project["version"], rmd.__version__)

    def test_package_version_matches_readme_badge(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        match = re.search(r"Version:\s*([0-9]+\.[0-9]+\.[0-9]+)", readme)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), rmd.__version__)

    def test_package_version_matches_citation_metadata(self) -> None:
        citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        match = re.search(r"^version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", citation, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), rmd.__version__)

    def test_hatch_wheel_package_is_explicit(self) -> None:
        with (ROOT / "pyproject.toml").open("rb") as handle:
            config = tomllib.load(handle)
        self.assertEqual(
            config["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"],
            ["src/romania_macro_financial_dynamics"],
        )


if __name__ == "__main__":
    unittest.main()
