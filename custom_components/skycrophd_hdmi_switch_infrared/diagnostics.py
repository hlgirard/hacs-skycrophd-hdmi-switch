"""Diagnostics for the SkycropHD HDMI Switch Infrared integration."""

from typing import Any

from homeassistant.core import HomeAssistant

from . import SkycropHDConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SkycropHDConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Only entity IDs and input names are stored, so nothing needs redacting.
    """
    runtime_data = entry.runtime_data
    return {
        "entry_data": dict(entry.data),
        "entry_options": dict(entry.options),
        "runtime": {
            "auto_mode": runtime_data.auto_mode,
            "power_on_delay_seconds": runtime_data.power_on_delay.total_seconds(),
            "source_names": dict(runtime_data.source_names),
            "pending_echo_count": runtime_data.pending_echo_count,
        },
    }
