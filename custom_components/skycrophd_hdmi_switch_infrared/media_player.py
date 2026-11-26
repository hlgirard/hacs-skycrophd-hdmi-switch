"""Media player platform for the SkycropHD HDMI Switch Infrared integration."""

import asyncio
from dataclasses import dataclass
import logging
from typing import Any, override

from infrared_protocols.commands.nec import NECCommand

from homeassistant.components.infrared import (
    InfraredReceivedSignal,
    InfraredReceiverConsumerEntity,
)
from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    MediaPlayerDeviceClass,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import ExtraStoredData, RestoreEntity

from . import SkycropHDConfigEntry
from .const import (
    CONF_INFRARED_RECEIVER_ENTITY_ID,
    DOMAIN,
    SKYCROPHD_HDMI_SWITCH_ADDRESS,
    SOURCE_CODES,
    SOURCE_RESETTING_CODES,
    SkycropHDHdmiSwitchCode,
    signal_auto_mode_changed,
    signal_source_unknown,
)
from .entity import SkycropHDIrEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1

CODE_TO_SOURCE_KEY: dict[SkycropHDHdmiSwitchCode, str] = {
    code: key for key, code in SOURCE_CODES.items()
}


@dataclass
class _SkycropHDExtraData(ExtraStoredData):
    """Persisted assumed state of the HDMI switch.

    The source is stored by its option key, not its display name, so renaming
    an input keeps it selected. It is stored apart from the entity state since
    ``MediaPlayerEntity.state_attributes`` drops ``source`` while OFF.
    """

    power_state: MediaPlayerState | None
    source_key: str | None

    @override
    def as_dict(self) -> dict[str, Any]:
        """Serialize for the restore-state store."""
        return {"power_state": self.power_state, "source_key": self.source_key}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SkycropHDConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the SkycropHD HDMI switch media player from a config entry."""
    if receiver_entity_id := entry.data.get(CONF_INFRARED_RECEIVER_ENTITY_ID):
        async_add_entities(
            [SkycropHDMediaPlayerWithReceiver(entry, receiver_entity_id)]
        )
    else:
        async_add_entities([SkycropHDMediaPlayer(entry)])


class SkycropHDMediaPlayer(SkycropHDIrEntity, MediaPlayerEntity, RestoreEntity):
    """SkycropHD HDMI switch media player entity."""

    _attr_name = None
    _attr_assumed_state = True
    _attr_device_class = MediaPlayerDeviceClass.RECEIVER
    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.SELECT_SOURCE
    )

    def __init__(self, entry: SkycropHDConfigEntry) -> None:
        """Initialize the media player."""
        super().__init__(entry, unique_id_suffix="media_player")
        self._source_names = entry.runtime_data.source_names
        self._name_to_key = {name: key for key, name in self._source_names.items()}
        self._attr_source_list = list(self._source_names.values())
        self._source_key: str | None = None

    @property
    @override
    def source(self) -> str | None:
        """Return the display name of the selected input.

        Unknown in auto mode, where the switch changes input on its own.
        """
        if self._source_key is None or self._runtime_data.auto_mode:
            return None
        return self._source_names[self._source_key]

    @property
    @override
    def extra_restore_state_data(self) -> ExtraStoredData:
        """Persist power state and source."""
        return _SkycropHDExtraData(
            power_state=self._attr_state, source_key=self._source_key
        )

    @override
    async def async_added_to_hass(self) -> None:
        """Restore the last assumed state and follow input resets from buttons."""
        await super().async_added_to_hass()

        if (extra := await self.async_get_last_extra_data()) is not None:
            data = extra.as_dict()
            if (power_state := data.get("power_state")) in (
                MediaPlayerState.ON,
                MediaPlayerState.OFF,
            ):
                self._attr_state = MediaPlayerState(power_state)
            if (source_key := data.get("source_key")) in SOURCE_CODES:
                self._source_key = source_key

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, signal_source_unknown(self._entry_id), self._clear_source
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                signal_auto_mode_changed(self._entry_id),
                self.async_write_ha_state,
            )
        )

    @callback
    def _clear_source(self) -> None:
        """Forget the selected input after it was changed relatively."""
        self._source_key = None
        self.async_write_ha_state()

    @override
    async def async_turn_on(self) -> None:
        """Send the discrete power-on command."""
        await self._send_code(SkycropHDHdmiSwitchCode.POWER_ON)
        self._attr_state = MediaPlayerState.ON
        self.async_write_ha_state()

    @override
    async def async_turn_off(self) -> None:
        """Send the discrete power-off command."""
        await self._send_code(SkycropHDHdmiSwitchCode.POWER_OFF)
        self._attr_state = MediaPlayerState.OFF
        self.async_write_ha_state()

    @override
    async def async_select_source(self, source: str) -> None:
        """Select an input."""
        if (key := self._name_to_key.get(source)) is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_source",
                translation_placeholders={
                    "invalid_source": source,
                    "valid_sources": ", ".join(self._attr_source_list or []),
                },
            )
        if self._attr_state is MediaPlayerState.OFF:
            # The switch ignores input keys while off.
            await self.async_turn_on()
            await asyncio.sleep(self._runtime_data.power_on_delay.total_seconds())
        await self._send_code(SOURCE_CODES[key])
        self._source_key = key
        self.async_write_ha_state()


class SkycropHDMediaPlayerWithReceiver(
    SkycropHDMediaPlayer, InfraredReceiverConsumerEntity
):
    """SkycropHD HDMI switch media player that follows the physical remote."""

    def __init__(self, entry: SkycropHDConfigEntry, receiver_entity_id: str) -> None:
        """Initialize the media player with a receiver."""
        super().__init__(entry)
        self._infrared_receiver_entity_id = receiver_entity_id

    @override
    @callback
    def _handle_signal(self, signal: InfraredReceivedSignal) -> None:
        """Update the assumed state from a command sent by the physical remote."""
        nec_command = NECCommand.from_raw_timings(signal.timings)
        if nec_command is None or nec_command.address != SKYCROPHD_HDMI_SWITCH_ADDRESS:
            return

        try:
            code = SkycropHDHdmiSwitchCode(nec_command.command)
        except ValueError:
            _LOGGER.debug(
                "Ignoring unknown SkycropHD infrared command: 0x%02X",
                nec_command.command,
            )
            return

        if self._runtime_data.consume_echo(code):
            _LOGGER.debug("Ignoring echo of sent SkycropHD command: %s", code.name)
            return

        _LOGGER.debug("Received SkycropHD infrared command: %s", code.name)

        if code is SkycropHDHdmiSwitchCode.POWER_ON:
            self._attr_state = MediaPlayerState.ON
        elif code is SkycropHDHdmiSwitchCode.POWER_OFF:
            self._attr_state = MediaPlayerState.OFF
        elif self._attr_state is MediaPlayerState.OFF:
            # The switch ignores every other key while off.
            return
        elif code is SkycropHDHdmiSwitchCode.AUTO:
            # The auto switching entity follows through the dispatcher signal.
            self._runtime_data.set_auto_mode(not self._runtime_data.auto_mode)
            return
        elif (source_key := CODE_TO_SOURCE_KEY.get(code)) is not None:
            self._source_key = source_key
        elif code in SOURCE_RESETTING_CODES:
            self._source_key = None
        else:
            return

        self.async_write_ha_state()
