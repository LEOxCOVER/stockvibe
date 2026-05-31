"""
Configuración de StockVibe: modo local (SQLite) o remoto (API en la nube).
"""
import json
import os
import sys

CONFIG_FILENAME = "stockvibe_config.json"


def _config_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _config_path():
    return os.path.join(_config_dir(), CONFIG_FILENAME)


def load_config():
    path = _config_path()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(data):
    path = _config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def get_mode():
    """'local' o 'remote'."""
    env = os.environ.get("STOCKVIBE_MODE", "").strip().lower()
    if env in ("local", "remote"):
        return env
    cfg = load_config()
    mode = str(cfg.get("mode", "local")).strip().lower()
    return mode if mode in ("local", "remote") else "local"


def is_remote():
    return get_mode() == "remote"


def get_api_url():
    env = os.environ.get("STOCKVIBE_API_URL", "").strip()
    if env:
        return env.rstrip("/")
    cfg = load_config()
    return str(cfg.get("api_url", "")).strip().rstrip("/")


def get_api_key():
    env = os.environ.get("STOCKVIBE_API_KEY", "").strip()
    if env:
        return env
    cfg = load_config()
    return str(cfg.get("api_key", "")).strip()
