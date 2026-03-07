from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

# Button labels (used for matching in handlers)
BTN_START_LESSON = "Начать урок"
BTN_END_LESSON = "Завершить урок"
BTN_EXPORT = "Экспорт в Anki"
BTN_RESUME = "Возобновить урок"
BTN_HISTORY = "История"
BTN_WORDS = "Слова урока"
BTN_EXPORT_QUIZLET = "Экспорт в Quizlet"
BTN_START_SESSION = "Начать сессию"
BTN_END_SESSION = "Завершить сессию"
BTN_RESUME_SESSION = "Возобновить сессию"


def idle_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[BTN_START_LESSON, BTN_START_SESSION], [BTN_HISTORY]],
        resize_keyboard=True,
    )


def lesson_active_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[BTN_WORDS, BTN_END_LESSON]],
        resize_keyboard=True,
    )


def session_active_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[BTN_WORDS, BTN_END_SESSION]],
        resize_keyboard=True,
    )


def lesson_ended_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[BTN_EXPORT, BTN_EXPORT_QUIZLET], [BTN_RESUME, BTN_HISTORY], [BTN_START_LESSON, BTN_START_SESSION]],
        resize_keyboard=True,
    )


def session_ended_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[BTN_EXPORT, BTN_EXPORT_QUIZLET], [BTN_RESUME_SESSION, BTN_HISTORY], [BTN_START_LESSON, BTN_START_SESSION]],
        resize_keyboard=True,
    )


def card_inline_keyboard(card_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Редактировать", callback_data=f"edit:{card_id}"),
            InlineKeyboardButton("Удалить", callback_data=f"delete:{card_id}"),
        ]
    ])


def confirm_delete_keyboard(card_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Да, удалить", callback_data=f"confirm_delete:{card_id}"),
            InlineKeyboardButton("Отмена", callback_data=f"cancel_delete:{card_id}"),
        ]
    ])
