# LEDMatrix Flip Clock

A minimal animated flip clock plugin for [ChuckBuilds/LEDMatrix](https://github.com/ChuckBuilds/LEDMatrix), designed around a **128x32** LED matrix.

## Layout

The display is split into two restrained areas:

- **Left:** large `HH:MM` time.
- **Right:** compact date rail showing weekday, day/month, and year.
- A subtle vertical divider separates time and date.
- Only digits that actually change perform the split-flap animation.

Example:

```text
┌────────────────────────────────┐
│  23:59              │ SAT      │
│                     │ 24 OCT   │
│                     │ 2026     │
└────────────────────────────────┘
```

At a normal minute boundary, changed digits collapse toward their horizontal hinge and the new digit unfolds. Hour changes therefore animate the hour digits as required, while unchanged digits remain still.

## Installation

From your LEDMatrix development checkout:

```bash
git clone https://github.com/jakejayeden/ledmatrix-flip-clock.git ../ledmatrix-flip-clock
cd LEDMatrix
./scripts/dev/dev_plugin_setup.sh link flip-clock ../ledmatrix-flip-clock
```

For a production installation, place/clone this repository in the LEDMatrix plugin repository directory (normally `plugin-repos/`) according to your LEDMatrix configuration.

## Configuration

| Setting | Default | Purpose |
| --- | --- | --- |
| `enabled` | `true` | Enables the plugin |
| `use_24_hour` | `true` | Use 24-hour instead of 12-hour time |
| `show_weekday` | `true` | Show the weekday in the date rail |
| `date_uppercase` | `true` | Render abbreviated date labels uppercase |
| `animation_ms` | `420` | Total flip animation duration |
| `animation_frames` | `7` | Number of animation frames |
| `display_duration` | `60` | Normal LEDMatrix display duration |

The clock uses the host system's local time via Python `datetime.now()`. Set the Raspberry Pi/system timezone correctly and daylight-saving changes will follow the host configuration.

## Display sizing

The plugin reads `display_manager.width` and `display_manager.height` rather than hard-coding the physical matrix dimensions. The layout is specifically tuned for 128x32, while retaining basic scaling behavior for other sizes.

## Requirements

- ChuckBuilds/LEDMatrix 2.x
- Pillow, already used by LEDMatrix
- DejaVu fonts are preferred; the plugin falls back to Pillow's default font if unavailable

## Notes

The animation is intentionally short and only runs across a normal minute boundary. If the plugin has not been displayed for more than 90 seconds, it jumps directly to the current time instead of animating from stale time.
