DEFAULT_SETTINGS = {
    "show_translation_en_telegram": False,
    "quizlet_en_only": False,
}

USER_SETTINGS = {
    USER_ID_2: {
        "show_translation_en_telegram": True,
        "quizlet_en_only": True,
    },
}


def get_settings(user_id: int) -> dict:
    return {**DEFAULT_SETTINGS, **USER_SETTINGS.get(user_id, {})}
