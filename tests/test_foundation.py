import json
from pathlib import Path

from romania_macro_financial_dynamics import __version__

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_version():
    assert __version__ == "0.5.2a0"


def test_sector_ids_are_unique_and_bilingual():
    sectors = load_json("model/registries/sectors.json")["sectors"]
    ids = [item["id"] for item in sectors]
    assert len(ids) == len(set(ids))
    assert {"H", "C", "F", "G", "X", "BNR"} == set(ids)
    assert all(item["label"]["ro"] and item["label"]["en"] for item in sectors)


def test_financial_instruments_are_unique_and_bilingual():
    instruments = load_json("model/registries/instruments.json")["instruments"]
    ids = [item["id"] for item in instruments]
    assert len(ids) == len(set(ids))
    assert ids == ["F2", "F3", "F4", "F5", "F6", "F7", "F8"]
    assert all(item["label"]["ro"] and item["label"]["en"] for item in instruments)


def test_model_contract_languages_and_benchmark():
    contract = load_json("model/registries/model_contract.json")
    assert contract["registry_version"] == "0.5.1a0"
    assert contract["default_language"] == "en"
    assert contract["supported_languages"] == ["en", "ro"]
    assert contract["benchmark"]["stock_date"] == "2025-12-31"
    assert contract["product_standard"] == {
        "name": "InfoClar Model Suite Design Standard",
        "version": "1.1",
        "scientific_semantics_unchanged": True,
    }
    assert contract["dynamic_core"]["accounting_spine_is_hard_constraint"] is True
    assert contract["empirical_dynamics"]["contract"] == "model/empirical_dynamics/contract.json"
    assert contract["calibration_validation"]["validation_recovery_contract"] == "model/calibration_validation/validation_recovery_contract.json"
    assert contract["calibration_validation"]["validated_reference_behavioural_mechanisms"] == 0
    assert contract["calibration_validation"]["alpha_0_6_behavioural_simulator_gate"] == "NO_GO"
    assert contract["product"]["reference_interface"] == "InfoClar web"
    assert contract["product"]["native_packaging"] == "deferred_near_v1"


def test_product_labels_are_unique_bilingual_and_cover_infoclar_navigation():
    registry = load_json("model/registries/product_labels.json")
    assert registry["default_language"] == "en"
    assert registry["supported_languages"] == ["en", "ro"]
    labels = registry["labels"]
    ids = [item["id"] for item in labels]
    assert len(ids) == len(set(ids))
    required = {
        "understand",
        "system_map",
        "flow_of_funds",
        "dynamics",
        "simulation",
        "scenarios",
        "validation",
        "data_sources",
        "open_app",
        "language",
        "model",
        "theory",
        "learn",
        "dashboard",
        "auxiliary",
        "sources",
        "limitations",
    }
    assert required <= set(ids)
    assert all(item["label"]["ro"] and item["label"]["en"] for item in labels)
