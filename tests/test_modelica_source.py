"""Static checks on the Modelica source files (no OpenModelica required)."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "modelica" / "ThermalPlant.mo"
TEST_MODEL_PATH = PROJECT_ROOT / "modelica" / "ThermalPlantTest.mo"


def test_thermal_plant_file_exists():
    assert MODEL_PATH.exists()


def test_thermal_plant_test_file_exists():
    assert TEST_MODEL_PATH.exists()


def test_model_contains_expected_name():
    text = MODEL_PATH.read_text()
    assert "model ThermalPlant" in text
    assert "end ThermalPlant;" in text


def test_model_contains_der_temperature():
    text = MODEL_PATH.read_text()
    assert "der(temperature)" in text


def test_model_contains_power_and_ambient():
    text = MODEL_PATH.read_text()
    assert "power" in text
    assert "ambient" in text


def test_model_contains_thermal_equation():
    text = MODEL_PATH.read_text()
    assert "power - (temperature - ambient) / R" in text


def test_model_has_expected_parameters():
    text = MODEL_PATH.read_text()
    assert "R = 0.5" in text
    assert "C = 100.0" in text
    assert "T_start = 25.0" in text


def test_test_model_references_thermal_plant():
    text = TEST_MODEL_PATH.read_text()
    assert "ThermalPlant plant" in text
    assert "powerAfterStep" in text
