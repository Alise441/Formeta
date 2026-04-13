import json
import os
import logging

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS = {
    "show_translation_en_telegram": False,
    "quizlet_en_only": False,
    "short_regular_verbs": False,
}

SETTINGS_PATH = os.environ.get("USER_SETTINGS_PATH", "settings.json")

_user_settings = {}

try:
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
        _user_settings = {int(uid): settings for uid, settings in raw.items()}
except FileNotFoundError:
    logger.warning(f"Settings file {SETTINGS_PATH} not found, using defaults")
except Exception as e:
    logger.error(f"Failed to load {SETTINGS_PATH}: {e}")


def get_settings(user_id: int) -> dict:
    return {**DEFAULT_SETTINGS, **_user_settings.get(user_id, {})}
