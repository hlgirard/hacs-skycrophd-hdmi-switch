"""SkycropHD HDMI Switch Infrared integration for Home Assistant."""

from datetime import datetime, timedelta

from homeassistant.components.infrared import async_get_emitters, async_get_receivers
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .const import (
    CONF_INFRARED_ENTITY_ID,
    CONF_INFRARED_RECEIVER_ENTITY_ID,
    CONF_POWER_ON_DELAY,
    DEFAULT_POWER_ON_DELAY,
    DEFAULT_SOURCE_NAMES,
    DOMAIN,
    ECHO_WINDOW,
    SkycropHDHdmiSwitchCode,
    signal_auto_mode_changed,
)

PLATFORMS = [Platform.BUTTON, Platform.MEDIA_PLAYER, Platform.SWITCH]


class SkycropHDRuntimeData:
    """Runtime data for a SkycropHD HDMI switch config entry.

    Auto switching is tracked at the device level: the auto switch entity sets
    it and the media player reads it, because in auto mode the switch changes
    input on its own without emitting anything.

    Codes sent by any entity are remembered for a moment so the receiver's echo
    of them is not taken for a press on the physical remote, which would undo
    toggles such as Auto.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        *,
        source_names: dict[str, str],
        power_on_delay: timedelta,
    ) -> None:
        """Initialize the runtime data."""
        self._hass = hass
        self._entry_id = entry_id
        # Display name of each input, keyed by its option key (source_1..source_5).
        self.source_names = source_names
        self.power_on_delay = power_on_delay
        self.auto_mode = False
        self._expected_echoes: list[tuple[SkycropHDHdmiSwitchCode, datetime]] = []

    @callback
    def expect_echo(self, code: SkycropHDHdmiSwitchCode) -> None:
        """Remember a code that is about to be sent, so its echo can be ignored."""
        self._expected_echoes.append((code, dt_util.utcnow() + ECHO_WINDOW))

    @property
    def pending_echo_count(self) -> int:
        """Return how many sent codes still wait for their echo."""
        now = dt_util.utcnow()
        return sum(1 for _, deadline in self._expected_echoes if deadline > now)

    @callback
    def consume_echo(self, code: SkycropHDHdmiSwitchCode) -> bool:
        """Return whether a received code is the echo of one just sent.

        Each sent code absorbs at most one received copy, so a genuine press of
        the same key on the physical remote right after still counts.
        """
        now = dt_util.utcnow()
        self._expected_echoes = [
            (sent, deadline)
            for sent, deadline in self._expected_echoes
            if deadline > now
        ]
        for index, (sent, _) in enumerate(self._expected_echoes):
            if sent is code:
                del self._expected_echoes[index]
                return True
        return False

    @callback
    def set_auto_mode(self, auto_mode: bool) -> None:
        """Set whether auto switching is on and notify the entities."""
        if auto_mode is self.auto_mode:
            return
        self.auto_mode = auto_mode
        async_dispatcher_send(self._hass, signal_auto_mode_changed(self._entry_id))


type SkycropHDConfigEntry = ConfigEntry[SkycropHDRuntimeData]


def _issue_id(kind: str, entry: SkycropHDConfigEntry) -> str:
    """Return the repair issue ID for a missing infrared entity of an entry."""
    return f"{kind}_not_found_{entry.entry_id}"


@callback
def _infrared_entity_exists(hass: HomeAssistant, entity_id: str, kind: str) -> bool:
    """Return whether an emitter or receiver entity is still known."""
    known = async_get_emitters(hass) if kind == "emitter" else async_get_receivers(hass)
    return er.async_get(hass).async_get(entity_id) is not None or entity_id in known


async def async_setup_entry(hass: HomeAssistant, entry: SkycropHDConfigEntry) -> bool:
    """Set up SkycropHD HDMI Switch Infrared from a config entry."""
    for kind, conf_key in (
        ("emitter", CONF_INFRARED_ENTITY_ID),
        ("receiver", CONF_INFRARED_RECEIVER_ENTITY_ID),
    ):
        entity_id: str | None = entry.data.get(conf_key)
        if entity_id is None or _infrared_entity_exists(hass, entity_id, kind):
            ir.async_delete_issue(hass, DOMAIN, _issue_id(kind, entry))
            continue
        placeholders = {"entity_id": entity_id, "title": entry.title}
        ir.async_create_issue(
            hass,
            DOMAIN,
            _issue_id(kind, entry),
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key=f"{kind}_not_found",
            translation_placeholders=placeholders,
        )
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key=f"{kind}_not_found",
            translation_placeholders=placeholders,
        )

    entry.runtime_data = SkycropHDRuntimeData(
        hass,
        entry.entry_id,
        source_names={
            key: entry.options.get(key) or default
            for key, default in DEFAULT_SOURCE_NAMES.items()
        },
        power_on_delay=timedelta(
            seconds=entry.options.get(CONF_POWER_ON_DELAY, DEFAULT_POWER_ON_DELAY)
        ),
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SkycropHDConfigEntry) -> bool:
    """Unload a SkycropHD HDMI Switch Infrared config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
