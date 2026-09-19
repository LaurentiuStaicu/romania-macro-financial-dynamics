from __future__ import annotations

import unittest

from scripts.audit_oecd_sectoral_financial_positions_counterpart_probe import (
    build_country_key,
    classify_flow_result,
    classify_probe_result,
    dimension_order_from_structure,
    has_counterpart_dimension,
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

    def test_counterpart_dimension_is_required_semantically(self) -> None:
        self.assertTrue(
            has_counterpart_dimension(
                ["FREQ", "REF_AREA", "SECTOR", "COUNTERPART_SECTOR", "INSTR_ASSET"]
            )
        )
        self.assertFalse(
            has_counterpart_dimension(
                ["FREQ", "REF_AREA", "SECTOR", "INSTR_ASSET"]
            )
        )

    def test_rate_limit_or_structure_failure_is_indeterminate(self) -> None:
        rule = {
            "each_required_structure_http_status": 200,
            "each_required_http_status": 200,
        }
        rate_limited = {
            "structure_http_status": 200,
            "structure_error": None,
            "structure_parse_error": None,
            "counterpart_dimension_present": True,
            "data_http_status": 429,
            "data_error": "HTTPError:429",
            "csv_header": [],
            "csv_data_row_count": 0,
            "romania_identity_present": False,
        }
        self.assertEqual(
            classify_flow_result(rate_limited, rule),
            "INDETERMINATE",
        )

        structure_failed = {
            **rate_limited,
            "structure_http_status": 500,
            "structure_error": "HTTPError:500",
            "data_http_status": None,
            "data_error": None,
        }
        self.assertEqual(
            classify_flow_result(structure_failed, rule),
            "INDETERMINATE",
        )

    def test_successful_empty_country_csv_is_definitive_negative(self) -> None:
        rule = {
            "each_required_structure_http_status": 200,
            "each_required_http_status": 200,
        }
        empty = {
            "structure_http_status": 200,
            "structure_error": None,
            "structure_parse_error": None,
            "counterpart_dimension_present": True,
            "data_http_status": 200,
            "data_error": None,
            "csv_header": ["REF_AREA", "TIME_PERIOD", "OBS_VALUE"],
            "csv_data_row_count": 0,
            "romania_identity_present": False,
        }
        self.assertEqual(
            classify_flow_result(empty, rule),
            "DEFINITIVE_NEGATIVE",
        )

        malformed_identity = {
            **empty,
            "csv_data_row_count": 2,
            "romania_identity_present": False,
        }
        self.assertEqual(
            classify_flow_result(malformed_identity, rule),
            "INDETERMINATE",
        )

    def test_probe_negative_requires_no_indeterminate_required_flow(self) -> None:
        rule = {
            "required_dataflows": ["stocks_counterpart", "flows_counterpart"],
            "effect_if_pass": "PASS_EFFECT",
            "effect_if_definitive_negative": "NEGATIVE_EFFECT",
            "effect_if_indeterminate": "INDETERMINATE_EFFECT",
        }
        negative = [
            {
                "id": "stocks_counterpart",
                "source_result_state": "PASS",
            },
            {
                "id": "flows_counterpart",
                "source_result_state": "DEFINITIVE_NEGATIVE",
            },
        ]
        self.assertEqual(
            classify_probe_result(negative, rule),
            ("DEFINITIVE_NEGATIVE", "NEGATIVE_EFFECT"),
        )

        mixed = [
            {
                "id": "stocks_counterpart",
                "source_result_state": "DEFINITIVE_NEGATIVE",
            },
            {
                "id": "flows_counterpart",
                "source_result_state": "INDETERMINATE",
            },
        ]
        self.assertEqual(
            classify_probe_result(mixed, rule),
            ("INDETERMINATE", "INDETERMINATE_EFFECT"),
        )

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
