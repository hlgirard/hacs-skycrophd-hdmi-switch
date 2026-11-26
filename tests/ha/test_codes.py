"""Tests for the SkycropHD HDMI switch code table against recorded captures."""

from infrared_protocols.commands.nec import NECCommand
import pytest

from custom_components.skycrophd_hdmi_switch_infrared.const import (
    SKYCROPHD_HDMI_SWITCH_ADDRESS,
    SkycropHDHdmiSwitchCode,
)

# Pronto exports of the original remote, recorded through the XIAO IR receiver.
CAPTURES: dict[SkycropHDHdmiSwitchCode, str] = {
    SkycropHDHdmiSwitchCode.POWER_ON: (
        "0000 006D 0022 0000 015A 00A9 0018 003E 0018 0013 0018 0013 0018 0013 0018 0013 "
        "0018 0013 0018 0013 0018 0013 0018 0013 0018 003E 0018 003E 0018 003E 0018 003E "
        "0018 003E 0018 003E 0018 003E 0018 0013 0018 0013 0018 003E 0018 003E 0018 003E "
        "0018 0013 0018 003E 0018 0013 0018 003E 0018 003E 0018 0013 0018 0013 0018 0013 "
        "0018 003E 0018 0013 0018 003E 0018 076D"
    ),
    SkycropHDHdmiSwitchCode.SOURCE_2: (
        "0000 006D 0022 0000 015A 00A9 0018 003E 0018 0013 0018 0013 0018 0013 0018 0013 "
        "0018 0013 0018 0013 0018 0013 0018 0013 0018 003E 0018 003E 0018 003E 0018 003E "
        "0018 003E 0018 003E 0018 003E 0018 0013 0018 003E 0018 003E 0018 003E 0018 003E "
        "0018 0013 0018 0013 0018 0013 0018 003E 0018 0013 0018 0013 0018 0013 0018 0013 "
        "0018 003E 0018 003E 0018 003E 0018 076D"
    ),
    SkycropHDHdmiSwitchCode.DOWN: (
        "0000 006D 0022 0000 015A 00A9 0018 003E 0018 0013 0018 0013 0018 0013 0018 0013 "
        "0018 0013 0018 0013 0018 0013 0018 0013 0018 003E 0018 003E 0018 003E 0018 003E "
        "0018 003D 0018 003E 0018 003E 0018 003E 0018 0013 0018 003E 0018 0013 0018 0013 "
        "0018 0013 0018 0013 0018 0013 0018 0013 0018 003E 0018 0013 0018 003E 0018 003E "
        "0018 003D 0018 003E 0018 003E 0018 076D"
    ),
}


def pronto_to_timings(pronto: str) -> list[int]:
    """Convert a raw Pronto code to signed microsecond timings."""
    words = [int(word, 16) for word in pronto.split()]
    unit_us = words[1] * 0.241246
    pairs = words[4:]
    return [
        round(value * unit_us) * (1 if index % 2 == 0 else -1)
        for index, value in enumerate(pairs)
    ]


@pytest.mark.parametrize(
    ("code", "command"),
    [
        pytest.param(SkycropHDHdmiSwitchCode.POWER_ON, 0x5C, id="power_on"),
        pytest.param(SkycropHDHdmiSwitchCode.POWER_OFF, 0x1F, id="power_off"),
        pytest.param(SkycropHDHdmiSwitchCode.SOURCE_1, 0x1B, id="source_1"),
        pytest.param(SkycropHDHdmiSwitchCode.SOURCE_2, 0x1E, id="source_2"),
        pytest.param(SkycropHDHdmiSwitchCode.SOURCE_3, 0x0D, id="source_3"),
        pytest.param(SkycropHDHdmiSwitchCode.SOURCE_4, 0x12, id="source_4"),
        pytest.param(SkycropHDHdmiSwitchCode.SOURCE_5, 0x10, id="source_5"),
        pytest.param(SkycropHDHdmiSwitchCode.AUTO, 0x0E, id="auto"),
        pytest.param(SkycropHDHdmiSwitchCode.ARC, 0x0F, id="arc"),
        pytest.param(SkycropHDHdmiSwitchCode.UP, 0x0C, id="up"),
        pytest.param(SkycropHDHdmiSwitchCode.DOWN, 0x05, id="down"),
    ],
)
def test_code_to_command(code: SkycropHDHdmiSwitchCode, command: int) -> None:
    """Each code builds an NEC command on the switch's address."""
    built = code.to_command()
    assert isinstance(built, NECCommand)
    assert built.address == SKYCROPHD_HDMI_SWITCH_ADDRESS
    assert built.command == command
    assert built.modulation == 38000


def test_address_is_standard_nec() -> None:
    """Address 0x01 with its inverse: identical on the wire to standard NEC 0x01."""
    assert SKYCROPHD_HDMI_SWITCH_ADDRESS & 0xFF == 0x01
    assert SKYCROPHD_HDMI_SWITCH_ADDRESS >> 8 == 0xFE


@pytest.mark.parametrize(
    "code", [pytest.param(code, id=code.name.lower()) for code in CAPTURES]
)
def test_capture_decodes_to_code(code: SkycropHDHdmiSwitchCode) -> None:
    """A recorded capture decodes to the code's address and command."""
    decoded = NECCommand.from_raw_timings(pronto_to_timings(CAPTURES[code]))
    assert decoded is not None
    assert decoded.address == SKYCROPHD_HDMI_SWITCH_ADDRESS
    assert SkycropHDHdmiSwitchCode(decoded.command) is code


@pytest.mark.parametrize(
    "code", [pytest.param(code, id=code.name.lower()) for code in CAPTURES]
)
def test_encoded_frame_matches_capture(code: SkycropHDHdmiSwitchCode) -> None:
    """The encoded frame's bit pattern matches the capture's (marks short, spaces long/short)."""
    captured = pronto_to_timings(CAPTURES[code])[2:66]
    encoded = code.to_command().get_raw_timings()[2:66]
    assert [space < -1000 for space in captured[1::2]] == [
        space < -1000 for space in encoded[1::2]
    ]
