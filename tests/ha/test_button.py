"""Tests for the SkycropHD HDMI switch buttons."""

import pytest

from custom_components.skycrophd_hdmi_switch_infrared.const import (
    SKYCROPHD_HDMI_SWITCH_ADDRESS,
    SkycropHDHdmiSwitchCode,
)
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.components.media_player import (
    ATTR_INPUT_SOURCE,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_SELECT_SOURCE,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant

from .conftest import MEDIA_PLAYER_ENTITY_ID, MockInfraredEmitterEntity


async def press(hass: HomeAssistant, entity_id: str) -> None:
    """Press a button."""
    await hass.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )


async def select_hdmi_1(hass: HomeAssistant) -> None:
    """Select the first input on the media player."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_SELECT_SOURCE,
        {ATTR_ENTITY_ID: MEDIA_PLAYER_ENTITY_ID, ATTR_INPUT_SOURCE: "HDMI 1"},
        blocking=True,
    )


def media_player_source(hass: HomeAssistant) -> str | None:
    """Return the media player's selected input."""
    state = hass.states.get(MEDIA_PLAYER_ENTITY_ID)
    assert state is not None
    return state.attributes.get(ATTR_INPUT_SOURCE)


@pytest.mark.usefixtures("init_integration")
@pytest.mark.parametrize(
    ("entity_id", "code", "clears_source"),
    [
        ("button.skycrophd_hdmi_switch_input_up", SkycropHDHdmiSwitchCode.UP, True),
        ("button.skycrophd_hdmi_switch_input_down", SkycropHDHdmiSwitchCode.DOWN, True),
        ("button.skycrophd_hdmi_switch_arc", SkycropHDHdmiSwitchCode.ARC, False),
    ],
)
async def test_press(
    hass: HomeAssistant,
    mock_emitter: MockInfraredEmitterEntity,
    entity_id: str,
    code: SkycropHDHdmiSwitchCode,
    clears_source: bool,
) -> None:
    """Each button sends its code; relative input keys clear the selected input."""
    await select_hdmi_1(hass)
    await press(hass, entity_id)
    await hass.async_block_till_done()

    sent = mock_emitter.sent_commands[-1]
    assert (sent.address, sent.command) == (SKYCROPHD_HDMI_SWITCH_ADDRESS, code)  # type: ignore[attr-defined]
    assert media_player_source(hass) == (None if clears_source else "HDMI 1")
