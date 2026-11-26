"""Consistency checks for translations and icons."""

import json
from pathlib import Path

import pytest

from custom_components.skycrophd_hdmi_switch_infrared.button import BUTTONS
from custom_components.skycrophd_hdmi_switch_infrared.const import (
    DEFAULT_SOURCE_NAMES,
)

INTEGRATION = (
    Path(__file__).parents[2] / "custom_components" / "skycrophd_hdmi_switch_infrared"
)


def load(name: str) -> dict[str, dict[str, object]]:
    """Load a JSON file of the integration."""
    data: dict[str, dict[str, object]] = json.loads((INTEGRATION / name).read_text())
    return data


def test_english_translation_matches_strings() -> None:
    """translations/en.json is a copy of strings.json."""
    assert load("translations/en.json") == load("strings.json")


@pytest.mark.parametrize("source", ["strings.json", "icons.json"])
def test_entity_translation_keys_present(source: str) -> None:
    """Every entity translation key used in code has a name and an icon."""
    entities = load(source)["entity"]
    assert isinstance(entities, dict)
    assert set(entities["button"]) == {d.translation_key for d in BUTTONS}
    assert set(entities["switch"]) == {"auto_switching"}


def test_translation_keys_used_in_code_present() -> None:
    """Exceptions, issues and option fields referenced by code are translated."""
    strings = load("strings.json")
    for key in ("emitter_not_found", "receiver_not_found", "invalid_source"):
        assert key in strings["exceptions"]
    for key in ("emitter_not_found", "receiver_not_found"):
        assert key in strings["issues"]
    options = strings["options"]
    assert isinstance(options, dict)
    init = options["step"]["init"]
    for key in [*DEFAULT_SOURCE_NAMES, "power_on_delay"]:
        assert key in init["data"]
        assert key in init["data_description"]
