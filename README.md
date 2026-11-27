# SkycropHD HDMI Switch Infrared

Home Assistant integration that controls a SkycropHD 5-in/1-out HDMI switch
(with ARC) over infrared. It sends commands through any Home Assistant
`infrared` emitter entity, for example an ESPHome IR proxy.

The switch cannot report its state, so the integration assumes it from the
commands it sends. If you also select an infrared **receiver**, presses on the
switch's own remote update the assumed state too.

## Supported devices

- **SkycropHD 5×1 HDMI switch with ARC** and its IR remote. The codes are NEC
  at 38 kHz, address `0x01` (see [IR codes](#ir-codes)).
- Other HDMI switches that use the same remote codes should work too. Many
  unbranded 5×1 switches share this code set.
- You need an infrared emitter that Home Assistant exposes as an `infrared`
  entity, such as an ESPHome IR proxy. A receiver is optional.

## Supported functions

| Entity | What it does |
| --- | --- |
| Media player (device class *receiver*) | Turn on, turn off, select one of the five inputs by name. Power state and input are assumed and kept across restarts. |
| Switch *Auto switching* | Auto mode, in which the switch follows the active HDMI source by itself. Assumed state, kept across restarts. |
| Button *Input up* / *Input down* | Cycle to the neighbouring input. The selected input becomes unknown. |
| Button *ARC* | Sends the ARC key. |

The integration also provides **diagnostics** (download them from the device
page) and **repair issues** when its emitter or receiver disappears.

## Installation

### HACS

1. Add this repository as a custom repository in HACS (category: *Integration*).
2. Install **SkycropHD HDMI Switch Infrared**.
3. Restart Home Assistant.

### Manual

Copy `custom_components/skycrophd_hdmi_switch_infrared` into your Home
Assistant `config/custom_components` directory and restart.

## Configuration

[![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=skycrophd_hdmi_switch_infrared)

Or go to **Settings → Devices & services → Add integration → SkycropHD HDMI
Switch Infrared**.

### Setup parameters

| Field | Notes |
| --- | --- |
| Infrared emitter | Required. The emitter pointed at the switch. One HDMI switch per emitter. |
| Infrared receiver | Optional. Lets the integration follow the switch's own remote. |

To change the emitter or receiver later, open the entry's menu and choose
**Reconfigure**. You don't need to remove the device. Leave the receiver empty
to stop following the remote.

### Options

Choose **Configure** on the entry.

| Option | Default | Notes |
| --- | --- | --- |
| Input 1 – 5 name | `HDMI 1` … `HDMI 5` | Names in the media player's source list. They must be unique and not empty. Renaming an input keeps it selected. |
| Power-on delay | 2 s (0–30) | Wait after Power on before sending an input key, when an input is selected while the switch is off. |

## Examples

Select an input from a script field whose options match the input names:

```yaml
fields:
  hdmi_input:
    selector:
      select:
        options: [Chromecast, Nintendo Switch, HDMI cable]
    default: Chromecast
sequence:
  - action: media_player.select_source
    target:
      entity_id: media_player.living_room_skycrophd_hdmi_switch
    data:
      source: "{{ hdmi_input }}"
```

## Known limitations

- **The state is assumed.** The switch reports nothing. If it is controlled in
  a way the integration can't see (the button on the switch itself, or the
  remote with no receiver), the shown state can be wrong until the next
  command.
- **Input keys are ignored while the switch is off.** If you select an input
  while the switch is assumed off, the integration sends Power on, waits for
  the power-on delay, then sends the input key. With a receiver, remote keys
  other than power are ignored while the switch is off.
- **Auto is a toggle.** The *Auto switching* entity only sends the Auto key
  when the requested mode differs from the assumed one. Without a receiver,
  pressing Auto on the remote leaves the entity showing the wrong mode until
  Auto is pressed again.
- **In auto mode the switch changes input by itself, without any IR signal.**
  Input keys don't leave auto mode, so while it is on, the media player's
  input is always unknown. The last input you selected shows again once auto
  mode is turned off.

## Troubleshooting

- **Nothing happens when a command is sent.** Check the emitter is pointed at
  the switch and is available (the entities become unavailable when it isn't).
  The emitter entity's state shows when it last sent something.
- **The state follows the remote in the wrong way, or Auto flips back.** Turn
  on debug logging. Received keys and ignored echoes are logged:

  ```yaml
  logger:
    logs:
      custom_components.skycrophd_hdmi_switch_infrared: debug
  ```

  Or use **Enable debug logging** on the integration page.
- **The first input after power-on is missed.** Increase the power-on delay in
  the options.
- **A repair issue says the emitter or receiver is missing.** The entity was
  removed or renamed. Choose **Reconfigure** and select the current one.
- When reporting a problem, attach the **diagnostics** from the device page.

## Removing the integration

This integration follows standard integration removal. No extra steps are
required.

1. Go to **Settings → Devices & services** and select **SkycropHD HDMI Switch
   Infrared**.
2. Open the entry's menu and select **Delete**.

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
make check      # lint + typecheck + test; creates .venv (Python 3.14, uv) on first run
make test       # pytest with coverage, fails under 95%
make lint       # ruff check + ruff format --check
make typecheck  # mypy --strict on the integration
```

`requirements-dev.txt` pins `pytest-homeassistant-custom-component`, which pins
an exact Home Assistant release. It also pins `infrared-protocols` to the
version that release's `infrared` component requires. CI runs these checks plus
hassfest and HACS validation on every push. The integration tracks its rules
in `quality_scale.yaml`.
