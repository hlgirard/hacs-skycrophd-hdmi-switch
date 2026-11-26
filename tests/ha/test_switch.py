"""Tests for the SkycropHD HDMI switch auto switching entity."""

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from infrared_protocols.commands.nec import NECCommand
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache,
)

from custom_components.skycrophd_hdmi_switch_infrared.const import (
    SKYCROPHD_HDMI_SWITCH_ADDRESS,
    SkycropHDHdmiSwitchCode,
)
from homeassistant.components.media_player import (
    ATTR_INPUT_SOURCE,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_SELECT_SOURCE,
)
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant, State

from .conftest import (
    MEDIA_PLAYER_ENTITY_ID,
    MockInfraredEmitterEntity,
    MockInfraredReceiverEntity,
)

AUTO_ENTITY_ID = "switch.skycrophd_hdmi_switch_auto_switching"


async def set_auto(hass: HomeAssistant, service: str) -> None:
    """Turn auto switching on or off."""
    await hass.services.async_call(
        SWITCH_DOMAIN, service, {ATTR_ENTITY_ID: AUTO_ENTITY_ID}, blocking=True
    )


def auto_state(hass: HomeAssistant) -> str:
    """Return the auto switching entity's state."""
    state = hass.states.get(AUTO_ENTITY_ID)
    assert state is not None
    return state.state


def media_player_source(hass: HomeAssistant) -> str | None:
    """Return the media player's selected input."""
    state = hass.states.get(MEDIA_PLAYER_ENTITY_ID)
    assert state is not None
    return state.attributes.get(ATTR_INPUT_SOURCE)


@pytest.mark.usefixtures("init_integration")
async def test_toggle(
    hass: HomeAssistant, mock_emitter: MockInfraredEmitterEntity
) -> None:
    """Auto is a toggle key, so it is only sent when the mode has to change."""
    assert auto_state(hass) == STATE_OFF
    assert hass.states.get(AUTO_ENTITY_ID).attributes["assumed_state"] is True

    await set_auto(hass, SERVICE_TURN_ON)
    await set_auto(hass, SERVICE_TURN_ON)
    assert auto_state(hass) == STATE_ON
    await set_auto(hass, SERVICE_TURN_OFF)
    assert auto_state(hass) == STATE_OFF

    assert [c.command for c in mock_emitter.sent_commands] == [  # type: ignore[attr-defined]
        SkycropHDHdmiSwitchCode.AUTO,
        SkycropHDHdmiSwitchCode.AUTO,
    ]


@pytest.mark.usefixtures("init_integration")
async def test_source_unknown_in_auto_mode(hass: HomeAssistant) -> None:
    """In auto mode the switch changes input on its own, even after an input key."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_SELECT_SOURCE,
        {ATTR_ENTITY_ID: MEDIA_PLAYER_ENTITY_ID, ATTR_INPUT_SOURCE: "HDMI 2"},
        blocking=True,
    )
    assert media_player_source(hass) == "HDMI 2"

    await set_auto(hass, SERVICE_TURN_ON)
    assert media_player_source(hass) is None

    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_SELECT_SOURCE,
        {ATTR_ENTITY_ID: MEDIA_PLAYER_ENTITY_ID, ATTR_INPUT_SOURCE: "HDMI 3"},
        blocking=True,
    )
    assert media_player_source(hass) is None

    await set_auto(hass, SERVICE_TURN_OFF)
    assert media_player_source(hass) == "HDMI 3"


@pytest.mark.parametrize("has_receiver", [True])
@pytest.mark.usefixtures("init_integration")
async def test_remote_auto_key_toggles(
    hass: HomeAssistant, mock_receiver: MockInfraredReceiverEntity
) -> None:
    """The Auto key on the physical remote toggles the assumed mode."""
    timings = NECCommand(
        address=SKYCROPHD_HDMI_SWITCH_ADDRESS, command=SkycropHDHdmiSwitchCode.AUTO
    ).get_raw_timings()

    mock_receiver.receive(timings)
    await hass.async_block_till_done()
    assert auto_state(hass) == STATE_ON

    mock_receiver.receive(timings)
    await hass.async_block_till_done()
    assert auto_state(hass) == STATE_OFF


async def test_restore(
    hass: HomeAssistant,
    infrared_entities: None,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The assumed mode is restored and applies to the media player."""
    mock_restore_cache(hass, [State(AUTO_ENTITY_ID, STATE_ON)])
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert auto_state(hass) == STATE_ON
    assert mock_config_entry.runtime_data.auto_mode is True


@pytest.mark.parametrize("has_receiver", [True])
@pytest.mark.usefixtures("init_integration")
async def test_own_transmission_echo_ignored(
    hass: HomeAssistant,
    mock_receiver: MockInfraredReceiverEntity,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The receiver hearing our own Auto key back must not toggle the mode again."""
    timings = NECCommand(
        address=SKYCROPHD_HDMI_SWITCH_ADDRESS, command=SkycropHDHdmiSwitchCode.AUTO
    ).get_raw_timings()

    await set_auto(hass, SERVICE_TURN_ON)
    freezer.tick(timedelta(milliseconds=150))
    mock_receiver.receive(timings)
    await hass.async_block_till_done()
    assert auto_state(hass) == STATE_ON

    # Each sent code absorbs one echo: a real press right after still toggles.
    mock_receiver.receive(timings)
    await hass.async_block_till_done()
    assert auto_state(hass) == STATE_OFF


@pytest.mark.parametrize("has_receiver", [True])
@pytest.mark.usefixtures("init_integration")
async def test_echo_window_expires(
    hass: HomeAssistant,
    mock_receiver: MockInfraredReceiverEntity,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A press after the echo window counts, even if the echo never arrived."""
    timings = NECCommand(
        address=SKYCROPHD_HDMI_SWITCH_ADDRESS, command=SkycropHDHdmiSwitchCode.AUTO
    ).get_raw_timings()

    await set_auto(hass, SERVICE_TURN_ON)
    freezer.tick(timedelta(seconds=2))
    mock_receiver.receive(timings)
    await hass.async_block_till_done()
    assert auto_state(hass) == STATE_OFF
