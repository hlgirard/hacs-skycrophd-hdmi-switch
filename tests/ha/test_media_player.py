"""Tests for the SkycropHD HDMI switch media player."""

from unittest.mock import AsyncMock, patch

from infrared_protocols.commands.nec import NECCommand
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache_with_extra_data,
)

from custom_components.skycrophd_hdmi_switch_infrared.const import (
    SKYCROPHD_HDMI_SWITCH_ADDRESS,
    SkycropHDHdmiSwitchCode,
)
from homeassistant.components.media_player import (
    ATTR_INPUT_SOURCE,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_SELECT_SOURCE,
    MediaPlayerState,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import ServiceValidationError

from .conftest import (
    MEDIA_PLAYER_ENTITY_ID,
    MockInfraredEmitterEntity,
    MockInfraredReceiverEntity,
)

NAMED_OPTIONS = {
    "source_1": "Chromecast",
    "source_2": "Kodi",
    "source_3": "Nintendo Switch",
    "source_4": "HDMI Cable",
    "source_5": "Source 5",
}


def sent_codes(emitter: MockInfraredEmitterEntity) -> list[tuple[int, int]]:
    """Return (address, command) of each command the emitter sent."""
    return emitter.sent_codes


def remote_press(
    receiver: MockInfraredReceiverEntity, address: int, command: int
) -> None:
    """Simulate a key press on the physical remote."""
    receiver.receive(NECCommand(address=address, command=command).get_raw_timings())


async def call(hass: HomeAssistant, service: str, **data: str) -> None:
    """Call a media player service on the switch."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        service,
        {ATTR_ENTITY_ID: MEDIA_PLAYER_ENTITY_ID, **data},
        blocking=True,
    )


def state(hass: HomeAssistant) -> State:
    """Return the media player's state."""
    current = hass.states.get(MEDIA_PLAYER_ENTITY_ID)
    assert current is not None
    return current


@pytest.mark.usefixtures("init_integration")
async def test_initial_state(hass: HomeAssistant) -> None:
    """The entity starts unknown, with default input names."""
    current = state(hass)
    assert current.state == STATE_UNKNOWN
    assert current.attributes["assumed_state"] is True
    assert current.attributes["device_class"] == "receiver"
    assert current.attributes["source_list"] == [f"HDMI {i}" for i in range(1, 6)]


@pytest.mark.usefixtures("init_integration")
async def test_turn_on_off(
    hass: HomeAssistant, mock_emitter: MockInfraredEmitterEntity
) -> None:
    """Turning on and off sends the discrete power codes."""
    await call(hass, SERVICE_TURN_ON)
    assert state(hass).state == MediaPlayerState.ON
    await call(hass, SERVICE_TURN_OFF)
    assert state(hass).state == MediaPlayerState.OFF
    assert sent_codes(mock_emitter) == [
        (SKYCROPHD_HDMI_SWITCH_ADDRESS, SkycropHDHdmiSwitchCode.POWER_ON),
        (SKYCROPHD_HDMI_SWITCH_ADDRESS, SkycropHDHdmiSwitchCode.POWER_OFF),
    ]


@pytest.mark.parametrize("entry_options", [NAMED_OPTIONS])
@pytest.mark.usefixtures("init_integration")
async def test_select_source(
    hass: HomeAssistant, mock_emitter: MockInfraredEmitterEntity
) -> None:
    """Selecting a named input sends only its code when the switch is not off."""
    await call(hass, SERVICE_TURN_ON)
    mock_emitter.sent_commands.clear()

    with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
        await call(hass, SERVICE_SELECT_SOURCE, **{ATTR_INPUT_SOURCE: "Kodi"})
    mock_sleep.assert_not_awaited()
    assert state(hass).attributes[ATTR_INPUT_SOURCE] == "Kodi"
    assert sent_codes(mock_emitter) == [
        (SKYCROPHD_HDMI_SWITCH_ADDRESS, SkycropHDHdmiSwitchCode.SOURCE_2)
    ]


@pytest.mark.parametrize("entry_options", [{**NAMED_OPTIONS, "power_on_delay": 3.0}])
@pytest.mark.usefixtures("init_integration")
async def test_select_source_while_off(
    hass: HomeAssistant, mock_emitter: MockInfraredEmitterEntity
) -> None:
    """The switch ignores input keys while off, so it is powered on first."""
    await call(hass, SERVICE_TURN_OFF)
    mock_emitter.sent_commands.clear()

    with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
        await call(hass, SERVICE_SELECT_SOURCE, **{ATTR_INPUT_SOURCE: "Kodi"})
    mock_sleep.assert_awaited_once_with(3.0)
    current = state(hass)
    assert current.state == MediaPlayerState.ON
    assert current.attributes[ATTR_INPUT_SOURCE] == "Kodi"
    assert sent_codes(mock_emitter) == [
        (SKYCROPHD_HDMI_SWITCH_ADDRESS, SkycropHDHdmiSwitchCode.POWER_ON),
        (SKYCROPHD_HDMI_SWITCH_ADDRESS, SkycropHDHdmiSwitchCode.SOURCE_2),
    ]


@pytest.mark.usefixtures("init_integration")
async def test_select_invalid_source(
    hass: HomeAssistant, mock_emitter: MockInfraredEmitterEntity
) -> None:
    """An unknown input is refused without sending anything."""
    with pytest.raises(ServiceValidationError):
        await call(hass, SERVICE_SELECT_SOURCE, **{ATTR_INPUT_SOURCE: "Kodi"})
    assert mock_emitter.sent_commands == []


@pytest.mark.parametrize("entry_options", [NAMED_OPTIONS])
async def test_restore_state(
    hass: HomeAssistant,
    infrared_entities: None,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Power state and input are restored, the input by key across renames."""
    mock_restore_cache_with_extra_data(
        hass,
        [
            (
                State(MEDIA_PLAYER_ENTITY_ID, MediaPlayerState.OFF),
                {"power_state": MediaPlayerState.OFF, "source_key": "source_3"},
            )
        ],
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert state(hass).state == MediaPlayerState.OFF

    await call(hass, SERVICE_TURN_ON)
    assert state(hass).attributes[ATTR_INPUT_SOURCE] == "Nintendo Switch"


@pytest.mark.parametrize(("entry_options", "has_receiver"), [(NAMED_OPTIONS, True)])
@pytest.mark.usefixtures("init_integration")
async def test_receiver_follows_remote(
    hass: HomeAssistant, mock_receiver: MockInfraredReceiverEntity
) -> None:
    """Presses on the physical remote update the assumed state."""
    address = SKYCROPHD_HDMI_SWITCH_ADDRESS
    remote_press(mock_receiver, address, SkycropHDHdmiSwitchCode.POWER_ON)
    await hass.async_block_till_done()
    assert state(hass).state == MediaPlayerState.ON

    remote_press(mock_receiver, address, SkycropHDHdmiSwitchCode.SOURCE_4)
    await hass.async_block_till_done()
    assert state(hass).attributes[ATTR_INPUT_SOURCE] == "HDMI Cable"

    remote_press(mock_receiver, address, SkycropHDHdmiSwitchCode.UP)
    await hass.async_block_till_done()
    assert ATTR_INPUT_SOURCE not in state(hass).attributes

    remote_press(mock_receiver, address, SkycropHDHdmiSwitchCode.SOURCE_1)
    await hass.async_block_till_done()
    assert state(hass).attributes[ATTR_INPUT_SOURCE] == "Chromecast"

    remote_press(mock_receiver, address, SkycropHDHdmiSwitchCode.POWER_OFF)
    await hass.async_block_till_done()
    assert state(hass).state == MediaPlayerState.OFF

    # The switch ignores input keys while off.
    remote_press(mock_receiver, address, SkycropHDHdmiSwitchCode.SOURCE_2)
    remote_press(mock_receiver, address, SkycropHDHdmiSwitchCode.AUTO)
    await hass.async_block_till_done()
    remote_press(mock_receiver, address, SkycropHDHdmiSwitchCode.POWER_ON)
    await hass.async_block_till_done()
    assert state(hass).attributes[ATTR_INPUT_SOURCE] == "Chromecast"


@pytest.mark.parametrize("has_receiver", [True])
@pytest.mark.usefixtures("init_integration")
@pytest.mark.parametrize(
    ("address", "command"),
    [
        pytest.param(0x3000, SkycropHDHdmiSwitchCode.POWER_ON, id="other_address"),
        pytest.param(SKYCROPHD_HDMI_SWITCH_ADDRESS, 0x99, id="unknown_command"),
        pytest.param(
            SKYCROPHD_HDMI_SWITCH_ADDRESS, SkycropHDHdmiSwitchCode.ARC, id="arc"
        ),
    ],
)
async def test_receiver_ignores(
    hass: HomeAssistant,
    mock_receiver: MockInfraredReceiverEntity,
    address: int,
    command: int,
) -> None:
    """Other devices' codes, unknown codes and ARC leave the state alone."""
    remote_press(mock_receiver, address, command)
    await hass.async_block_till_done()
    assert state(hass).state == STATE_UNKNOWN
