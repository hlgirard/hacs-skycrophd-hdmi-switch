# SkycropHD HDMI Switch Infrared

Home Assistant integration that controls a SkycropHD 5-in/1-out HDMI switch
(with ARC) over infrared. It sends commands through any Home Assistant
`infrared` emitter entity, for example an ESPHome IR proxy. It is modeled on
the core `benq_projector_infrared` integration.

The switch cannot report its state, so the integration assumes it. If you
select an infrared **receiver** during setup, presses on the switch's own
remote update the assumed state too.

## Entities

| Entity | What it does |
| --- | --- |
| `media_player` (device class *receiver*) | Turn on, turn off, select one of the five inputs. Power state and input are assumed and kept across restarts. |
| `switch` *Auto switching* | Auto mode, in which the switch follows the active HDMI source by itself. Assumed state, kept across restarts. |
| `button` *Input up* / *Input down* | Cycle to the neighbouring input. The selected input becomes unknown. |
| `button` *ARC* | ARC key. |

How the switch behaves, and how the integration models it:

- **Input keys are ignored while the switch is off.** If you select an input
  while the switch is assumed off, the integration sends Power on, waits for
  the *power-on delay* (default 2 s), then sends the input key. With a
  receiver, remote keys other than power are ignored while the switch is off.
- **Auto is a toggle.** The *Auto switching* entity only sends the Auto key
  when the requested mode differs from the assumed one. A receiver keeps the
  two in sync when the physical remote is used. Without one, pressing Auto on
  the remote leaves the entity showing the wrong mode until it is pressed
  again.
- **In auto mode the switch changes input by itself, without any IR signal.**
  Input keys don't leave auto mode, so while it is on the media player's
  input is always unknown. The last input you selected shows again once auto
  mode is turned off.
- **The receiver hears the integration's own transmissions.** An IR proxy's
  receiver usually sits next to its emitter and hears each sent code back
  about 150–200 ms later. For 1 second after sending a code, the integration
  ignores one received copy of it. Otherwise toggles like Auto would flip back.
  A second press of the same key on the physical remote still counts.

## Installation

### HACS

1. Add this repository as a custom repository in HACS (category: *Integration*).
2. Install **SkycropHD HDMI Switch Infrared**.
3. Restart Home Assistant.

### Manual

Copy `custom_components/skycrophd_hdmi_switch_infrared` into your Home
Assistant `config/custom_components` directory and restart.

## Configuration

**Settings → Devices & Services → Add Integration → SkycropHD HDMI Switch Infrared**

| Field | Notes |
| --- | --- |
| Infrared emitter | Required. The emitter pointed at the switch. |
| Infrared receiver | Optional. Lets the integration follow the switch's own remote. |

**Configure** (options) names the five inputs ("HDMI 1".."HDMI 5" by default),
for example *Chromecast*, *Kodi*. These names make up the media player's
source list. Renaming an input keeps the current selection.
The options also set the *power-on delay* (0–30 s) described above.

## IR codes

NEC protocol, 38 kHz, address `0x01` (sent with its inverse, `0xFE01` as a
16-bit address). Captured from the original remote:

| Key | Command |
| --- | --- |
| Power on | `0x5C` |
| Power off | `0x1F` |
| Input 1 – 5 | `0x1B`, `0x1E`, `0x0D`, `0x12`, `0x10` |
| Auto | `0x0E` |
| ARC | `0x0F` |
| Up / Down | `0x0C` / `0x05` |

## Development

```bash
make test   # creates .venv (Python 3.14, uv) and runs the Home Assistant test suite
uvx ruff check . && uvx ruff format --check .
```

`requirements-dev.txt` pins `pytest-homeassistant-custom-component`, which pins
an exact Home Assistant release. It also pins `infrared-protocols` to the
version that release's `infrared` component requires.
