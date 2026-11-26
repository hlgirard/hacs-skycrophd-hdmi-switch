"""Common entity for the SkycropHD HDMI Switch Infrared integration."""

from homeassistant.components.infrared import InfraredEmitterConsumerEntity
from homeassistant.helpers.device_registry import DeviceInfo

from . import SkycropHDConfigEntry
from .const import (
    CONF_INFRARED_ENTITY_ID,
    DEVICE_NAME,
    DOMAIN,
    MANUFACTURER,
    SkycropHDHdmiSwitchCode,
)


class SkycropHDIrEntity(InfraredEmitterConsumerEntity):
    """SkycropHD HDMI Switch Infrared base entity."""

    _attr_has_entity_name = True

    def __init__(self, entry: SkycropHDConfigEntry, unique_id_suffix: str) -> None:
        """Initialize the entity."""
        self._entry_id = entry.entry_id
        self._runtime_data = entry.runtime_data
        self._infrared_emitter_entity_id = entry.data[CONF_INFRARED_ENTITY_ID]
        self._attr_unique_id = f"{entry.entry_id}_{unique_id_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=DEVICE_NAME,
            manufacturer=MANUFACTURER,
            model="HDMI switch",
        )

    async def _send_code(self, code: SkycropHDHdmiSwitchCode) -> None:
        """Send an IR command to the HDMI switch."""
        self._runtime_data.expect_echo(code)
        await self._send_command(code.to_command())
