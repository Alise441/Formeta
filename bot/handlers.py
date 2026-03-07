import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import ALLOWED_USER_IDS
from db import repository as repo
from services.llm import analyze_word
from services.anki import generate_deck
from bot.formatters import format_card_telegram
from bot.keyboards import (
    BTN_START_LESSON, BTN_END_LESSON, BTN_EXPORT, BTN_RESUME, BTN_HISTORY,
    idle_keyboard, lesson_active_keyboard, lesson_ended_keyboard,
    card_inline_keyboard, confirm_delete_keyboard,
)

logger = logging.getLogger(__name__)


def _lesson_date(lesson: dict) -> str:
    """Format lesson started_at as dd.mm.yyyy."""
    ts = lesson.get("started_at", "")
    if ts and len(ts) >= 10:
        parts = ts[:10].split("-")  # YYYY-MM-DD
        return f"{parts[2]}.{parts[1]}.{parts[0]}"
    return "?"


def authorized(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
            await update.message.reply_text("У вас нет доступа к этому боту.")
            return
        return await func(update, context)
    return wrapper


@authorized
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lesson = await repo.get_active_lesson()
    if lesson:
        kb = lesson_active_keyboard()
        text = f"{_lesson_date(lesson)} Урок активен. Отправляйте слова!"
    else:
        kb = idle_keyboard()
        text = "Привет! Нажмите «Начать урок», чтобы начать записывать слова."
    await update.message.reply_text(text, reply_markup=kb)


@authorized
async def handle_start_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active = await repo.get_active_lesson()
    if active:
        await update.message.reply_text(
            f"{_lesson_date(active)} Урок уже идёт. Отправляйте слова!",
            reply_markup=lesson_active_keyboard(),
        )
        return
    lesson_id = await repo.create_lesson()
    lesson = await repo.get_active_lesson()
    await update.message.reply_text(
        f"{_lesson_date(lesson)} Урок начат! Отправляйте немецкие слова или фразы.",
        reply_markup=lesson_active_keyboard(),
    )


@authorized
async def handle_end_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lesson = await repo.get_active_lesson()
    if not lesson:
        await update.message.reply_text(
            "Нет активного урока.", reply_markup=idle_keyboard()
        )
        return
    date = _lesson_date(lesson)
    lesson_id = lesson["id"]
    await repo.end_lesson(lesson_id)
    count = await repo.count_lesson_cards(lesson_id)
    cards = await repo.get_lesson_cards(lesson_id)
    word_list = ", ".join(c["base_form"] for c in cards) if cards else "—"
    await update.message.reply_text(
        f"{date} Урок завершён!\n"
        f"Слов: {count}\n"
        f"Слова: {word_list}\n\n"
        f"Нажмите «Экспорт в Anki» для генерации колоды.",
        reply_markup=lesson_ended_keyboard(),
    )


@authorized
async def handle_resume_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lesson = await repo.get_last_ended_lesson()
    if not lesson:
        await update.message.reply_text(
            "Нет завершённых уроков для возобновления.",
            reply_markup=idle_keyboard(),
        )
        return
    await repo.resume_lesson(lesson["id"])
    await update.message.reply_text(
        f"{_lesson_date(lesson)} Урок возобновлён! Отправляйте слова.",
        reply_markup=lesson_active_keyboard(),
    )


@authorized
async def handle_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lesson = await repo.get_last_ended_lesson()
    if not lesson:
        active = await repo.get_active_lesson()
        if active:
            lesson = active
        else:
            await update.message.reply_text(
                "Нет уроков для экспорта.", reply_markup=idle_keyboard()
            )
            return
    cards = await repo.get_lesson_cards(lesson["id"])
    if not cards:
        await update.message.reply_text("В уроке нет карточек.")
        return
    await update.message.reply_text("Генерирую колоду...")
    # Format lesson date as dd.mm
    date_str = lesson["started_at"][:10] if lesson["started_at"] else ""
    if date_str:
        # started_at is ISO format: YYYY-MM-DD...
        parts = date_str.split("-")
        lesson_date = f"{parts[2]}.{parts[1]}"
    else:
        lesson_date = str(lesson["id"])
    filepath = generate_deck(lesson["id"], cards, lesson_date)
    filename = f"formeta_lesson_{lesson_date}.apkg"
    await update.message.reply_document(
        document=open(filepath, "rb"),
        filename=filename,
        caption=f"Anki-колода за {lesson_date} ({len(cards)} карточек)",
    )


@authorized
async def handle_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lessons = await repo.get_recent_lessons(10)
    if not lessons:
        await update.message.reply_text("Уроков пока нет.")
        return
    lines = ["Последние уроки:\n"]
    for lesson in lessons:
        count = await repo.count_lesson_cards(lesson["id"])
        status = "активен" if lesson["status"] == "active" else "завершён"
        date = _lesson_date(lesson)
        lines.append(f"#{lesson['id']} {date} — {count} слов — {status}")
    await update.message.reply_text("\n".join(lines))


@authorized
async def handle_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lesson = await repo.get_active_lesson()
    if not lesson:
        await update.message.reply_text(
            "Сейчас нет активного урока. Нажмите «Начать урок».",
            reply_markup=idle_keyboard(),
        )
        return

    text = update.message.text.strip()
    if not text:
        return

    await update.message.reply_chat_action("typing")

    try:
        data = await analyze_word(text)
    except Exception as e:
        logger.error(f"LLM error for '{text}': {e}")
        await update.message.reply_text(
            f"Ошибка при анализе слова «{text}». Попробуйте ещё раз."
        )
        return

    # Build example dict from LLM response
    example = None
    if data.get("example_de"):
        example = {"de": data["example_de"], "ru": data.get("example_ru", "")}

    card_id = await repo.create_card(
        lesson_id=lesson["id"],
        raw_input=text,
        base_form=data["base_form"],
        word_type=data["word_type"],
        forms=data.get("forms"),
        translation=data["translation"],
        example=example,
        prepositions=data.get("prepositions", []),
        created_by=update.effective_user.username or str(update.effective_user.id),
    )

    card = await repo.get_card(card_id)
    formatted = format_card_telegram(card)
    await update.message.reply_text(
        formatted,
        parse_mode="MarkdownV2",
        reply_markup=card_inline_keyboard(card_id),
    )


async def callback_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    card_id = int(query.data.split(":")[1])
    await query.edit_message_reply_markup(
        reply_markup=confirm_delete_keyboard(card_id)
    )


async def callback_confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    card_id = int(query.data.split(":")[1])
    await repo.delete_card(card_id)
    await query.edit_message_text("Карточка удалена.")


async def callback_cancel_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    card_id = int(query.data.split(":")[1])
    await query.edit_message_reply_markup(
        reply_markup=card_inline_keyboard(card_id)
    )


async def callback_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    card_id = int(query.data.split(":")[1])
    context.user_data["editing_card_id"] = card_id
    card = await repo.get_card(card_id)
    if not card:
        await query.edit_message_text("Карточка не найдена.")
        return
    await query.message.reply_text(
        f"Текущий перевод: {card['translation']}\n\n"
        "Отправьте новый перевод:",
    )


@authorized
async def handle_edit_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    card_id = context.user_data.get("editing_card_id")
    if not card_id:
        return False
    new_translation = update.message.text.strip()
    await repo.update_card_translation(card_id, new_translation)
    context.user_data.pop("editing_card_id", None)
    card = await repo.get_card(card_id)
    formatted = format_card_telegram(card)
    await update.message.reply_text(
        f"Перевод обновлён!\n\n{formatted}",
        parse_mode="MarkdownV2",
        reply_markup=card_inline_keyboard(card_id),
    )
    return True
