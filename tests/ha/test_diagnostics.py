"""Tests for the SkycropHD HDMI Switch Infrared diagnostics."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant

from .conftest import EMITTER_ENTITY_ID, RECEIVER_ENTITY_ID


@pytest.mark.parametrize(
    ("has_receiver", "entry_options"),
    [(True, {"source_1": "Chromecast", "power_on_delay": 3.0})],
)
async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    init_integration: MockConfigEntry,
) -> None:
    """Diagnostics show the configuration and the assumed state."""
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.skycrophd_hdmi_switch_auto_switching"},
        blocking=True,
    )

    assert await get_diagnostics_for_config_entry(
        hass, hass_client, init_integration
    ) == {
        "entry_data": {
            "infrared_entity_id": EMITTER_ENTITY_ID,
            "infrared_receiver_entity_id": RECEIVER_ENTITY_ID,
        },
        "entry_options": {"source_1": "Chromecast", "power_on_delay": 3.0},
        "runtime": {
            "auto_mode": True,
            "power_on_delay_seconds": 3.0,
            "source_names": {
                "source_1": "Chromecast",
                "source_2": "HDMI 2",
                "source_3": "HDMI 3",
                "source_4": "HDMI 4",
                "source_5": "HDMI 5",
            },
            # The Auto key just sent is still waiting for its receiver echo.
            "pending_echo_count": 1,
        },
    }
