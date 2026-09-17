import json
from pathlib import Path

from romania_macro_financial_dynamics import __version__

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_version():
    assert __version__ == "0.2.0a0"


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
    assert contract["default_language"] == "ro"
    assert contract["supported_languages"] == ["ro", "en"]
    assert contract["benchmark"]["stock_date"] == "2025-12-31"


def test_product_labels_are_unique_and_bilingual():
    registry = load_json("model/registries/product_labels.json")
    assert registry["default_language"] == "ro"
    assert registry["supported_languages"] == ["ro", "en"]
    labels = registry["labels"]
    ids = [item["id"] for item in labels]
    assert len(ids) == len(set(ids))
    assert {"understand", "system_map", "flow_of_funds", "dynamics", "simulation", "scenarios", "validation", "data_sources", "open_app", "language"} == set(ids)
    assert all(item["label"]["ro"] and item["label"]["en"] for item in labels)
