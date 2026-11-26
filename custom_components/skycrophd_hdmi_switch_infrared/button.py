"""Button platform for the SkycropHD HDMI Switch Infrared integration."""

from dataclasses import dataclass
from typing import override

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SkycropHDConfigEntry
from .const import (
    SOURCE_RESETTING_CODES,
    SkycropHDHdmiSwitchCode,
    signal_source_unknown,
)
from .entity import SkycropHDIrEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class SkycropHDButtonEntityDescription(ButtonEntityDescription):
    """Describes a SkycropHD HDMI switch button entity."""

    command_code: SkycropHDHdmiSwitchCode


BUTTONS: tuple[SkycropHDButtonEntityDescription, ...] = (
    SkycropHDButtonEntityDescription(
        key="input_up",
        translation_key="input_up",
        command_code=SkycropHDHdmiSwitchCode.UP,
    ),
    SkycropHDButtonEntityDescription(
        key="input_down",
        translation_key="input_down",
        command_code=SkycropHDHdmiSwitchCode.DOWN,
    ),
    SkycropHDButtonEntityDescription(
        key="arc",
        translation_key="arc",
        command_code=SkycropHDHdmiSwitchCode.ARC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SkycropHDConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up SkycropHD HDMI switch buttons from a config entry."""
    async_add_entities(SkycropHDButton(entry, description) for description in BUTTONS)


class SkycropHDButton(SkycropHDIrEntity, ButtonEntity):
    """A button that sends one IR command to the HDMI switch."""

    entity_description: SkycropHDButtonEntityDescription

    def __init__(
        self,
        entry: SkycropHDConfigEntry,
        description: SkycropHDButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(entry, unique_id_suffix=description.key)
        self.entity_description = description

    @override
    async def async_press(self) -> None:
        """Send the button's IR command."""
        code = self.entity_description.command_code
        await self._send_code(code)
        if code in SOURCE_RESETTING_CODES:
            async_dispatcher_send(self.hass, signal_source_unknown(self._entry_id))
