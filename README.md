# split-slideshow

Four-panel random slideshow kiosk for a Raspberry Pi 4B. The screen splits into a
2×2 grid; each panel independently pulls random images from its own folder. Images
are scaled to fit while preserving aspect ratio, and any leftover space in a panel is
filled black (letterbox). Built for running a slideshow at an event.

## Features

- 2×2 grid, one folder per panel (subfolders scanned recursively).
- Aspect-ratio-preserving scale with black letterboxing.
- Staggered per-panel timers so panels don't all flip at once.
- Picks up images added to folders while running (periodic re-scan).
- Robust: skips corrupt/unreadable images instead of crashing.
- Empty folder shows a placeholder and keeps polling.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

## Setup

```sh
git clone <repo> split-slideshow
cd split-slideshow
uv sync                       # creates .venv and installs pygame-ce
cp config.example.toml config.toml
$EDITOR config.toml           # set your 4 folder paths
```

## Run

```sh
uv run python -m split_slideshow config.toml
```

Press `Esc` or `Q` to quit. For desktop testing set `fullscreen = false` in the config.

## Configuration

See `config.example.toml`. Key fields:

| Field | Meaning |
|-------|---------|
| `display.fullscreen` | Fullscreen kiosk (`true`) or windowed (`false`) |
| `display.resolution` | `[w, h]`; omit for native desktop resolution |
| `display.background` | `[r, g, b]` letterbox color |
| `slideshow.interval_seconds` | How long each image shows |
| `slideshow.stagger_seconds` | Offset between panel flips |
| `slideshow.rescan_every` | Re-scan a folder after this many flips |
| `slideshow.avoid_recent` | Don't repeat any of the last N images in a panel |
| `panels.folders` | Exactly 4 folder paths (TL, TR, BL, BR) |

## Old Raspberry Pi OS / Raspbian Buster (32-bit, Python 3.7)

On 32-bit Raspbian Buster there are no pygame-ce wheels on PyPI, and the system
SDL2 is too old to build current pygame-ce. Use the system Python 3.7 with the
[piwheels](https://www.piwheels.org) prebuilt wheel (pygame-ce 2.3.2) instead of a
uv-managed interpreter:

```sh
rm -rf .venv
uv venv --python /usr/bin/python3 --python-preference only-system   # 3.7.x
uv sync --python-preference only-system
uv run --python /usr/bin/python3 split-slideshow config.toml
```

The `python_version < '3.9'` markers in `pyproject.toml` automatically select
pygame-ce 2.3.2 from piwheels plus the `tomli` backport (no source build needed).
For best results, run a fully updated 64-bit Raspberry Pi OS where the latest
pygame-ce installs straight from PyPI.

## Run on boot (Raspberry Pi)

Install the project under `/home/pi/split-slideshow`, create `config.toml`, then:

```sh
sudo cp deploy/split-slideshow.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now split-slideshow
```

The unit sets `Restart=always` (auto-respawn on crash) and disables screen blanking
via `xset s off -dpms`. Adjust `User`, paths, and `DISPLAY` in the unit if your setup
differs. Requires the Pi to boot to the desktop (X11) session.

Logs: `journalctl -u split-slideshow -f`.
