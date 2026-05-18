import os
import secrets
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _bool_from_env(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_from_env(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _float_from_env(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def default_config():
    return {
        "SECRET_KEY": os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        "DATABASE": os.environ.get("DATABASE", str(BASE_DIR / "database.db")),
        "HOST": os.environ.get("HOST", "0.0.0.0"),
        "PORT": _int_from_env("PORT", 5000),
        "IPPT_API_URL": os.environ.get("IPPT_API_URL", "https://ippt.vercel.app/api"),
        "IPPT_API_TIMEOUT": _float_from_env("IPPT_API_TIMEOUT", 5.0),
        "WORKOUT_TEST_SECONDS": _int_from_env("WORKOUT_TEST_SECONDS", 60),
    }


def is_debug_enabled():
    return _bool_from_env("FLASK_DEBUG", False)
