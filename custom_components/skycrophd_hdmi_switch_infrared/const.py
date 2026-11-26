"""Constants for the SkycropHD HDMI Switch Infrared integration."""

from datetime import timedelta
from enum import IntEnum, unique

from infrared_protocols.commands import Command
from infrared_protocols.commands.nec import NECCommand

DOMAIN = "skycrophd_hdmi_switch_infrared"
CONF_INFRARED_ENTITY_ID = "infrared_entity_id"
CONF_INFRARED_RECEIVER_ENTITY_ID = "infrared_receiver_entity_id"
CONF_POWER_ON_DELAY = "power_on_delay"
DEVICE_NAME = "SkycropHD HDMI switch"
MANUFACTURER = "SkycropHD"

# Standard NEC address 0x01; the decoder reports it with its inverse as the high byte.
SKYCROPHD_HDMI_SWITCH_ADDRESS = 0xFE01


@unique
class SkycropHDHdmiSwitchCode(IntEnum):
    """SkycropHD HDMI switch IR command codes, captured from its remote."""

    POWER_ON = 0x5C
    POWER_OFF = 0x1F
    SOURCE_1 = 0x1B
    SOURCE_2 = 0x1E
    SOURCE_3 = 0x0D
    SOURCE_4 = 0x12
    SOURCE_5 = 0x10
    AUTO = 0x0E
    ARC = 0x0F
    UP = 0x0C
    DOWN = 0x05

    def to_command(self) -> Command:
        """Build an NEC command for this SkycropHD HDMI switch code."""
        return NECCommand(address=SKYCROPHD_HDMI_SWITCH_ADDRESS, command=self.value)


# Option key of each input's display name, in input order.
SOURCE_CODES: dict[str, SkycropHDHdmiSwitchCode] = {
    "source_1": SkycropHDHdmiSwitchCode.SOURCE_1,
    "source_2": SkycropHDHdmiSwitchCode.SOURCE_2,
    "source_3": SkycropHDHdmiSwitchCode.SOURCE_3,
    "source_4": SkycropHDHdmiSwitchCode.SOURCE_4,
    "source_5": SkycropHDHdmiSwitchCode.SOURCE_5,
}
DEFAULT_SOURCE_NAMES: dict[str, str] = {
    key: f"HDMI {index}" for index, key in enumerate(SOURCE_CODES, start=1)
}

# The receiver hears our own transmissions back about 150-200 ms after sending.
ECHO_WINDOW = timedelta(seconds=1)

# Seconds to wait after power-on before an input key is accepted.
DEFAULT_POWER_ON_DELAY = 2.0

# Relative input keys, after which the selected input is no longer known.
SOURCE_RESETTING_CODES = frozenset(
    {SkycropHDHdmiSwitchCode.UP, SkycropHDHdmiSwitchCode.DOWN}
)


def signal_auto_mode_changed(entry_id: str) -> str:
    """Return the dispatcher signal sent when auto switching is toggled."""
    return f"{DOMAIN}_{entry_id}_auto_mode_changed"


def signal_source_unknown(entry_id: str) -> str:
    """Return the dispatcher signal sent when the selected input becomes unknown."""
    return f"{DOMAIN}_{entry_id}_source_unknown"
