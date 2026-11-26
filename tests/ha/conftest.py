"""Fixtures for the SkycropHD HDMI Switch Infrared tests."""

from collections.abc import Generator
from typing import override

from infrared_protocols.commands import Command
from infrared_protocols.commands.nec import NECCommand
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    setup_test_component_platform,
)

from custom_components.skycrophd_hdmi_switch_infrared.const import (
    CONF_INFRARED_ENTITY_ID,
    CONF_INFRARED_RECEIVER_ENTITY_ID,
    DEVICE_NAME,
    DOMAIN,
)
from homeassistant.components.infrared import (
    DOMAIN as INFRARED_DOMAIN,
    InfraredEmitterEntity,
    InfraredReceivedSignal,
    InfraredReceiverEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

EMITTER_ENTITY_ID = "infrared.test_emitter"
RECEIVER_ENTITY_ID = "infrared.test_receiver"
OTHER_EMITTER_ENTITY_ID = "infrared.other_emitter"
ENTRY_ID = "01JTEST0000000000000000000"
MEDIA_PLAYER_ENTITY_ID = "media_player.skycrophd_hdmi_switch"


class MockInfraredEmitterEntity(InfraredEmitterEntity):
    """Infrared emitter that records the commands it sends."""

    def __init__(self, entity_id: str = EMITTER_ENTITY_ID) -> None:
        """Initialize the emitter."""
        self.entity_id = entity_id
        self._attr_name = entity_id.removeprefix("infrared.")
        self._attr_unique_id = entity_id
        self.sent_commands: list[Command] = []

    @override
    async def async_send_command(self, command: Command) -> None:
        """Record the command."""
        self.sent_commands.append(command)

    @property
    def sent_codes(self) -> list[tuple[int, int]]:
        """Return (address, command) of each NEC command sent."""
        codes = []
        for command in self.sent_commands:
            assert isinstance(command, NECCommand)
            codes.append((command.address, command.command))
        return codes


class MockInfraredReceiverEntity(InfraredReceiverEntity):
    """Infrared receiver that tests can feed signals into."""

    _attr_name = "Test receiver"

    def __init__(self) -> None:
        """Initialize the receiver."""
        self.entity_id = RECEIVER_ENTITY_ID
        self._attr_unique_id = "test_receiver"

    def receive(self, timings: list[int]) -> None:
        """Simulate receiving a signal."""
        self._handle_received_signal(InfraredReceivedSignal(timings=timings))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Enable loading the custom integration in every test."""
    yield


@pytest.fixture
def mock_emitter() -> MockInfraredEmitterEntity:
    """Return the mock emitter entity."""
    return MockInfraredEmitterEntity()


@pytest.fixture
def mock_receiver() -> MockInfraredReceiverEntity:
    """Return the mock receiver entity."""
    return MockInfraredReceiverEntity()


@pytest.fixture
def other_emitter() -> MockInfraredEmitterEntity:
    """Return a second mock emitter entity."""
    return MockInfraredEmitterEntity(OTHER_EMITTER_ENTITY_ID)


@pytest.fixture
async def infrared_entities(
    hass: HomeAssistant,
    mock_emitter: MockInfraredEmitterEntity,
    other_emitter: MockInfraredEmitterEntity,
    mock_receiver: MockInfraredReceiverEntity,
) -> None:
    """Set up the infrared domain with two mock emitters and a receiver."""
    setup_test_component_platform(
        hass, INFRARED_DOMAIN, [mock_emitter, other_emitter, mock_receiver]
    )
    assert await async_setup_component(
        hass, INFRARED_DOMAIN, {INFRARED_DOMAIN: {"platform": "test"}}
    )
    await hass.async_block_till_done()


@pytest.fixture
def has_receiver() -> bool:
    """Return whether the config entry uses a receiver."""
    return False


@pytest.fixture
def entry_options() -> dict[str, str]:
    """Return the options of the config entry."""
    return {}


@pytest.fixture
def mock_config_entry(
    has_receiver: bool, entry_options: dict[str, str]
) -> MockConfigEntry:
    """Return a config entry for the HDMI switch."""
    data = {CONF_INFRARED_ENTITY_ID: EMITTER_ENTITY_ID}
    if has_receiver:
        data[CONF_INFRARED_RECEIVER_ENTITY_ID] = RECEIVER_ENTITY_ID
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id=ENTRY_ID,
        title=DEVICE_NAME,
        data=data,
        options=entry_options,
    )


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    infrared_entities: None,
    mock_config_entry: MockConfigEntry,
) -> MockConfigEntry:
    """Set up the integration."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry
