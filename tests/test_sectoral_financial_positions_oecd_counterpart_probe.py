from __future__ import annotations

import unittest

from scripts.audit_oecd_sectoral_financial_positions_counterpart_probe import (
    build_country_key,
    dimension_order_from_structure,
    inspect_csv,
)


class OECDSectoralFinancialPositionsCounterpartProbeLogicTests(unittest.TestCase):
    def test_dimension_order_is_taken_from_sdmx_positions(self) -> None:
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<mes:Structure xmlns:mes="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message"
 xmlns:str="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure">
 <mes:Structures>
  <str:DataStructures>
   <str:DataStructure id="TEST">
    <str:DataStructureComponents>
     <str:DimensionList id="DimensionDescriptor">
      <str:Dimension id="REF_AREA" position="1"/>
      <str:Dimension id="FREQ" position="2"/>
      <str:Dimension id="SECTOR" position="3"/>
      <str:TimeDimension id="TIME_PERIOD" position="4"/>
     </str:DimensionList>
    </str:DataStructureComponents>
   </str:DataStructure>
  </str:DataStructures>
 </mes:Structures>
</mes:Structure>"""
        self.assertEqual(
            dimension_order_from_structure(xml),
            ["REF_AREA", "FREQ", "SECTOR"],
        )

    def test_country_key_leaves_unfrozen_dimensions_wildcarded(self) -> None:
        key = build_country_key(
            ["REF_AREA", "FREQ", "SECTOR", "COUNTERPART_SECTOR", "INSTR_ASSET"],
            reference_area="ROU",
            frequency="Q",
        )
        self.assertEqual(key, "ROU.Q...")

    def test_country_key_works_when_frequency_precedes_reference_area(self) -> None:
        key = build_country_key(
            ["FREQ", "ADJUSTMENT", "REF_AREA", "SECTOR"],
            reference_area="ROU",
            frequency="Q",
        )
        self.assertEqual(key, "Q..ROU.")

    def test_csv_inspection_requires_actual_romania_identity(self) -> None:
        summary = inspect_csv(
            b"REF_AREA,TIME_PERIOD,OBS_VALUE\r\n"
            b"ROU,2025-Q1,1.0\r\n"
            b"ROU,2025-Q2,2.0\r\n"
        )
        self.assertEqual(summary["data_row_count"], 2)
        self.assertTrue(summary["romania_identity_present"])

        absent = inspect_csv(
            b"REF_AREA,TIME_PERIOD,OBS_VALUE\r\n"
            b"AUT,2025-Q1,1.0\r\n"
        )
        self.assertFalse(absent["romania_identity_present"])


if __name__ == "__main__":
    unittest.main()
