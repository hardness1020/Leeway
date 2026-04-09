"""Path resolution for Leeway configuration and data directories.

Follows XDG-like conventions with ~/.leeway/ as the default base directory.
"""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_BASE_DIR = ".leeway"
_CONFIG_FILE_NAME = "settings.json"


def get_config_dir() -> Path:
    """Return the configuration directory, creating it if needed.

    Resolution order:
    1. AGENTTREE_CONFIG_DIR environment variable
    2. ~/.leeway/
    """
    env_dir = os.environ.get("AGENTTREE_CONFIG_DIR")
    if env_dir:
        config_dir = Path(env_dir)
    else:
        config_dir = Path.home() / _DEFAULT_BASE_DIR

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_file_path() -> Path:
    """Return the path to the main settings file (~/.leeway/settings.json)."""
    return get_config_dir() / _CONFIG_FILE_NAME


def get_data_dir() -> Path:
    """Return the data directory for caches, history, etc.

    Resolution order:
    1. AGENTTREE_DATA_DIR environment variable
    2. ~/.leeway/data/
    """
    env_dir = os.environ.get("AGENTTREE_DATA_DIR")
    if env_dir:
        data_dir = Path(env_dir)
    else:
        data_dir = get_config_dir() / "data"

    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_logs_dir() -> Path:
    """Return the logs directory.

    Resolution order:
    1. AGENTTREE_LOGS_DIR environment variable
    2. ~/.leeway/logs/
    """
    env_dir = os.environ.get("AGENTTREE_LOGS_DIR")
    if env_dir:
        logs_dir = Path(env_dir)
    else:
        logs_dir = get_config_dir() / "logs"

    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_project_config_dir(cwd: str | Path) -> Path:
    """Return the per-project .leeway directory."""
    project_dir = Path(cwd).resolve() / ".leeway"
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir
