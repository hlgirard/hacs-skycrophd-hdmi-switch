"""Tests for the SkycropHD HDMI Switch Infrared config flow."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.skycrophd_hdmi_switch_infrared.const import (
    CONF_INFRARED_ENTITY_ID,
    CONF_INFRARED_RECEIVER_ENTITY_ID,
    DEVICE_NAME,
    DOMAIN,
)
from homeassistant.config_entries import (
    SOURCE_USER,
    ConfigEntryState,
    ConfigFlowResult,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import EMITTER_ENTITY_ID, OTHER_EMITTER_ENTITY_ID, RECEIVER_ENTITY_ID

SOURCE_NAMES = {
    "source_1": "Chromecast",
    "source_2": "Kodi",
    "source_3": "Nintendo Switch",
    "source_4": "HDMI Cable",
    "source_5": "Source 5",
}


@pytest.mark.usefixtures("infrared_entities")
@pytest.mark.parametrize(
    "user_input",
    [
        pytest.param({CONF_INFRARED_ENTITY_ID: EMITTER_ENTITY_ID}, id="emitter_only"),
        pytest.param(
            {
                CONF_INFRARED_ENTITY_ID: EMITTER_ENTITY_ID,
                CONF_INFRARED_RECEIVER_ENTITY_ID: RECEIVER_ENTITY_ID,
            },
            id="with_receiver",
        ),
    ],
)
async def test_user_flow(hass: HomeAssistant, user_input: dict[str, str]) -> None:
    """The user step creates an entry with the selected entities."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == DEVICE_NAME
    assert result["data"] == user_input


async def test_no_emitters(hass: HomeAssistant) -> None:
    """The flow aborts when there is no infrared emitter."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_infrared_emitters"


@pytest.mark.usefixtures("infrared_entities")
async def test_already_configured(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The same emitter cannot be configured twice."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_INFRARED_ENTITY_ID: EMITTER_ENTITY_ID}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """The options flow saves the input names and they reach the source list."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {**SOURCE_NAMES, "source_1": "  Chromecast ", "power_on_delay": 3.5},
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert init_integration.options == {**SOURCE_NAMES, "power_on_delay": 3.5}
    assert init_integration.runtime_data.power_on_delay.total_seconds() == 3.5

    state = hass.states.get("media_player.skycrophd_hdmi_switch")
    assert state is not None
    assert state.attributes["source_list"] == list(SOURCE_NAMES.values())


@pytest.mark.parametrize(
    ("names", "error"),
    [
        pytest.param({"source_2": "Chromecast"}, "duplicate_source_name", id="dup"),
        pytest.param({"source_3": "   "}, "empty_source_name", id="empty"),
    ],
)
async def test_options_flow_invalid(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    names: dict[str, str],
    error: str,
) -> None:
    """Duplicate or empty input names are refused."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {**SOURCE_NAMES, **names, "power_on_delay": 2}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}


async def start_reconfigure(
    hass: HomeAssistant, entry: MockConfigEntry
) -> ConfigFlowResult:
    """Start the reconfigure flow of an entry."""
    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    return result


@pytest.mark.parametrize(
    ("has_receiver", "user_input"),
    [
        pytest.param(
            False,
            {
                CONF_INFRARED_ENTITY_ID: OTHER_EMITTER_ENTITY_ID,
                CONF_INFRARED_RECEIVER_ENTITY_ID: RECEIVER_ENTITY_ID,
            },
            id="change_emitter_add_receiver",
        ),
        pytest.param(
            True,
            {CONF_INFRARED_ENTITY_ID: EMITTER_ENTITY_ID},
            id="remove_receiver",
        ),
    ],
)
async def test_reconfigure(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    user_input: dict[str, str],
) -> None:
    """Reconfigure replaces the infrared entities and reloads the entry."""
    result = await start_reconfigure(hass, init_integration)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert dict(init_integration.data) == user_input
    assert init_integration.state is ConfigEntryState.LOADED


async def test_reconfigure_emitter_in_use(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """An emitter already used by another HDMI switch entry is refused."""
    MockConfigEntry(
        domain=DOMAIN, data={CONF_INFRARED_ENTITY_ID: OTHER_EMITTER_ENTITY_ID}
    ).add_to_hass(hass)

    result = await start_reconfigure(hass, init_integration)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_INFRARED_ENTITY_ID: OTHER_EMITTER_ENTITY_ID}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert init_integration.data[CONF_INFRARED_ENTITY_ID] == EMITTER_ENTITY_ID


async def test_reconfigure_no_emitters(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Reconfigure aborts when there is no infrared emitter at all."""
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_infrared_emitters"
