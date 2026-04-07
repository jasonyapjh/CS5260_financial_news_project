"""
config_loader.py
----------------
Loads and validates the YAML config file.
"""

import yaml
from pathlib import Path


def load_config(path: str = "config/config.yaml") -> dict:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path.resolve()}")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)
