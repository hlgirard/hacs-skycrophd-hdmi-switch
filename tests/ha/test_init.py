"""Tests for setting up the SkycropHD HDMI Switch Infrared integration."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.skycrophd_hdmi_switch_infrared.const import (
    CONF_INFRARED_ENTITY_ID,
    CONF_INFRARED_RECEIVER_ENTITY_ID,
    DOMAIN,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .conftest import EMITTER_ENTITY_ID, MEDIA_PLAYER_ENTITY_ID


@pytest.mark.parametrize("has_receiver", [False, True])
async def test_setup_and_unload(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """The entry loads its entities and unloads cleanly."""
    assert init_integration.state is ConfigEntryState.LOADED
    assert hass.states.get(MEDIA_PLAYER_ENTITY_ID) is not None
    assert hass.states.get("button.skycrophd_hdmi_switch_arc") is not None

    assert await hass.config_entries.async_unload(init_integration.entry_id)
    await hass.async_block_till_done()
    assert init_integration.state is ConfigEntryState.NOT_LOADED


@pytest.mark.usefixtures("infrared_entities")
@pytest.mark.parametrize(
    ("data", "kind"),
    [
        pytest.param(
            {CONF_INFRARED_ENTITY_ID: "infrared.missing"}, "emitter", id="emitter"
        ),
        pytest.param(
            {
                CONF_INFRARED_ENTITY_ID: EMITTER_ENTITY_ID,
                CONF_INFRARED_RECEIVER_ENTITY_ID: "infrared.missing",
            },
            "receiver",
            id="receiver",
        ),
    ],
)
async def test_missing_infrared_entity(
    hass: HomeAssistant, data: dict[str, str], kind: str
) -> None:
    """A missing infrared entity fails setup and raises a repair issue.

    Fixing the entry and reloading it, as Reconfigure does, clears the issue.
    """
    entry = MockConfigEntry(domain=DOMAIN, data=data, title="HDMI switch")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR

    issue_registry = ir.async_get(hass)
    issue_id = f"{kind}_not_found_{entry.entry_id}"
    issue = issue_registry.async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_key == f"{kind}_not_found"
    assert issue.translation_placeholders == {
        "entity_id": "infrared.missing",
        "title": "HDMI switch",
    }
    assert issue.is_fixable is False

    hass.config_entries.async_update_entry(
        entry, data={CONF_INFRARED_ENTITY_ID: EMITTER_ENTITY_ID}
    )
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is None
