"""Load and validate the slideshow TOML config."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(Exception):
    """Raised when the config file is missing or invalid."""


@dataclass
class Config:
    folders: list[Path]
    fullscreen: bool = True
    resolution: tuple[int, int] | None = None
    background: tuple[int, int, int] = (0, 0, 0)
    interval_seconds: float = 8.0
    stagger_seconds: float = 2.0
    rescan_every: int = 20  # re-scan a folder after this many flips


def load_config(path: str | Path) -> Config:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    with path.open("rb") as f:
        data = tomllib.load(f)

    display = data.get("display", {})
    slideshow = data.get("slideshow", {})
    panels = data.get("panels", {})

    folders_raw = panels.get("folders")
    if not isinstance(folders_raw, list) or len(folders_raw) != 4:
        raise ConfigError(
            "[panels].folders must be a list of exactly 4 folder paths"
        )
    folders = [Path(p).expanduser() for p in folders_raw]
    missing = [str(p) for p in folders if not p.is_dir()]
    if missing:
        raise ConfigError("These panel folders do not exist:\n  " + "\n  ".join(missing))

    resolution = display.get("resolution")
    if resolution is not None:
        resolution = (int(resolution[0]), int(resolution[1]))

    background = tuple(display.get("background", [0, 0, 0]))
    if len(background) != 3:
        raise ConfigError("[display].background must be [r, g, b]")

    return Config(
        folders=folders,
        fullscreen=bool(display.get("fullscreen", True)),
        resolution=resolution,
        background=background,  # type: ignore[arg-type]
        interval_seconds=float(slideshow.get("interval_seconds", 8.0)),
        stagger_seconds=float(slideshow.get("stagger_seconds", 2.0)),
        rescan_every=int(slideshow.get("rescan_every", 20)),
    )
