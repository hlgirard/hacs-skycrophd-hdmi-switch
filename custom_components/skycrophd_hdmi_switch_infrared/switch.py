"""Switch platform for the SkycropHD HDMI Switch Infrared integration."""

from typing import Any, override

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import SkycropHDConfigEntry
from .const import SkycropHDHdmiSwitchCode, signal_auto_mode_changed
from .entity import SkycropHDIrEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SkycropHDConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the SkycropHD HDMI switch auto switching entity."""
    async_add_entities([SkycropHDAutoSwitch(entry)])


class SkycropHDAutoSwitch(SkycropHDIrEntity, SwitchEntity, RestoreEntity):
    """Auto switching mode, toggled by the switch's Auto key.

    In auto mode the switch follows the active HDMI source on its own, even
    after an input key, until Auto is pressed again.
    """

    _attr_assumed_state = True
    _attr_translation_key = "auto_switching"

    def __init__(self, entry: SkycropHDConfigEntry) -> None:
        """Initialize the auto switching entity."""
        super().__init__(entry, unique_id_suffix="auto_switching")

    @property
    @override
    def is_on(self) -> bool:
        """Return whether auto switching is on."""
        return self._runtime_data.auto_mode

    @override
    async def async_added_to_hass(self) -> None:
        """Restore the last assumed mode and follow changes from the remote."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            self._runtime_data.set_auto_mode(last_state.state == STATE_ON)
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                signal_auto_mode_changed(self._entry_id),
                self.async_write_ha_state,
            )
        )

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn auto switching on."""
        await self._set_auto_mode(True)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn auto switching off."""
        await self._set_auto_mode(False)

    async def _set_auto_mode(self, auto_mode: bool) -> None:
        """Send the Auto toggle key if the mode differs from the assumed one."""
        if auto_mode is self._runtime_data.auto_mode:
            return
        await self._send_code(SkycropHDHdmiSwitchCode.AUTO)
        self._runtime_data.set_auto_mode(auto_mode)
