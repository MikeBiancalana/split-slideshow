"""Entry point: python -m split_slideshow [config.toml]"""

from __future__ import annotations

import sys

from .app import run
from .config import ConfigError, load_config


def main() -> int:
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.toml"
    try:
        config = load_config(config_path)
    except ConfigError as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 1
    run(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
