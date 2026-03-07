import logging

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes

from config import ALLOWED_USER_IDS, get_lesson_owner, is_teacher, get_teachers
from db import repository as repo
from services.llm import analyze_word
from services.anki import generate_deck
from services.quizlet import generate_quizlet_export
from bot.formatters import format_card_telegram, format_card_editable, parse_card_editable
from bot.keyboards import (
    BTN_START_LESSON, BTN_END_LESSON, BTN_EXPORT, BTN_EXPORT_QUIZLET, BTN_RESUME, BTN_HISTORY, BTN_WORDS,
    idle_keyboard, lesson_active_keyboard, lesson_ended_keyboard,
    card_inline_keyboard, confirm_delete_keyboard,
)

logger = logging.getLogger(__name__)


async def _notify_teachers(context, student_id: int, text: str):
    for teacher_id in get_teachers(student_id):
        try:
            await context.bot.send_message(chat_id=teacher_id, text=text)
        except Exception as e:
            logger.error(f"Failed to notify teacher {teacher_id}: {e}")


async def _notify_partner(context, user_id: int, owner_id: int, text: str, parse_mode=None, reply_markup=None):
    """Notify the other side: if teacher → student, if student → teachers."""
    targets = []
    if is_teacher(user_id):
        targets.append(owner_id)
    else:
        targets.extend(get_teachers(user_id))
    for target in targets:
        try:
            await context.bot.send_message(
                chat_id=target, text=text,
                parse_mode=parse_mode, reply_markup=reply_markup,
            )
        except Exception as e:
            logger.error(f"Failed to notify {target}: {e}")


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
    uid = update.effective_user.id
    owner_id = get_lesson_owner(uid)
    lesson = await repo.get_active_lesson(owner_id)
    if is_teacher(uid):
        if lesson:
            text = f"{_lesson_date(lesson)} Урок активен. Отправляйте слова!"
        else:
            text = "Привет! Сейчас нет активного урока. Вы получите уведомление, когда урок начнётся."
        await update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
        return
    if lesson:
        kb = lesson_active_keyboard()
        text = f"{_lesson_date(lesson)} Урок активен. Отправляйте слова!"
    else:
        kb = idle_keyboard()
        text = "Привет! Нажмите «Начать урок», чтобы начать записывать слова."
    await update.message.reply_text(text, reply_markup=kb)


@authorized
async def handle_start_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner_id = get_lesson_owner(update.effective_user.id)
    active = await repo.get_active_lesson(owner_id)
    if active:
        await update.message.reply_text(
            f"{_lesson_date(active)} Урок уже идёт. Отправляйте слова!",
            reply_markup=lesson_active_keyboard(),
        )
        return
    lesson_id = await repo.create_lesson(owner_id)
    lesson = await repo.get_active_lesson(owner_id)
    await update.message.reply_text(
        f"{_lesson_date(lesson)} Урок начат! Отправляйте немецкие слова или фразы.",
        reply_markup=lesson_active_keyboard(),
    )
    await _notify_teachers(context, owner_id,
        f"{_lesson_date(lesson)} Урок начался! Отправляйте слова.")


@authorized
async def handle_end_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner_id = get_lesson_owner(update.effective_user.id)
    lesson = await repo.get_active_lesson(owner_id)
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
    await _notify_teachers(context, owner_id,
        f"{date} Урок завершён!\nСлов: {count}\nСлова: {word_list}")


@authorized
async def handle_resume_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner_id = get_lesson_owner(update.effective_user.id)
    lesson = await repo.get_last_ended_lesson(owner_id)
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
    await _notify_teachers(context, owner_id,
        f"{_lesson_date(lesson)} Урок возобновлён! Отправляйте слова.")


@authorized
async def handle_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner_id = get_lesson_owner(update.effective_user.id)
    lesson = await repo.get_last_ended_lesson(owner_id)
    if not lesson:
        active = await repo.get_active_lesson(owner_id)
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
    lesson_date = _get_lesson_date_short(lesson)
    filepath = generate_deck(lesson["id"], cards, lesson_date)
    filename = f"formeta_lesson_{lesson_date}.apkg"
    await update.message.reply_document(
        document=open(filepath, "rb"),
        filename=filename,
        caption=f"Anki-колода за {lesson_date} ({len(cards)} карточек)",
    )


def _get_lesson_date_short(lesson: dict) -> str:
    """Format lesson started_at as dd.mm for filenames."""
    ts = lesson.get("started_at", "")
    if ts and len(ts) >= 10:
        parts = ts[:10].split("-")
        return f"{parts[2]}.{parts[1]}"
    return str(lesson["id"])


@authorized
async def handle_export_quizlet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner_id = get_lesson_owner(update.effective_user.id)
    lesson = await repo.get_last_ended_lesson(owner_id)
    if not lesson:
        active = await repo.get_active_lesson(owner_id)
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
    lesson_date = _get_lesson_date_short(lesson)
    filepath = generate_quizlet_export(lesson["id"], cards, lesson_date)
    await update.message.reply_document(
        document=open(filepath, "rb"),
        filename=f"formeta_quizlet_{lesson_date}.txt",
        caption=f"Quizlet-экспорт за {lesson_date} ({len(cards)} карточек)\n"
                "Откройте Quizlet → Import → вставьте содержимое файла",
    )


@authorized
async def handle_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner_id = get_lesson_owner(update.effective_user.id)
    lessons = await repo.get_recent_lessons(owner_id, 10)
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
async def handle_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner_id = get_lesson_owner(update.effective_user.id)
    lesson = await repo.get_active_lesson(owner_id)
    if not lesson:
        await update.message.reply_text(
            "Нет активного урока.", reply_markup=idle_keyboard()
        )
        return
    cards = await repo.get_lesson_cards(lesson["id"])
    if not cards:
        await update.message.reply_text("В уроке пока нет слов.")
        return
    lines = [f"{_lesson_date(lesson)} — {len(cards)} слов:\n"]
    for c in cards:
        lines.append(f"  {c['base_form']} — {c['translation']}")
    await update.message.reply_text("\n".join(lines))


@authorized
async def handle_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    owner_id = get_lesson_owner(user_id)
    lesson = await repo.get_active_lesson(owner_id)
    if not lesson:
        if is_teacher(user_id):
            await update.message.reply_text(
                "Сейчас нет активного урока. Вы получите уведомление, когда урок начнётся.")
        else:
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
        translation_en=data.get("translation_en", ""),
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

    await _notify_partner(context, user_id, owner_id,
        text=formatted, parse_mode="MarkdownV2",
        reply_markup=card_inline_keyboard(card_id))


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
        "Скопируйте текст карточки выше, отредактируйте и отправьте обратно.",
    )


@authorized
async def handle_edit_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    card_id = context.user_data.get("editing_card_id")
    if not card_id:
        return False
    parsed = parse_card_editable(update.message.text)
    await repo.update_card_full(
        card_id=card_id,
        base_form=parsed["base_form"],
        word_type=parsed["word_type"],
        forms=parsed["forms"],
        translation=parsed["translation"],
        example=parsed.get("example"),
        prepositions=parsed.get("prepositions", []),
    )
    context.user_data.pop("editing_card_id", None)
    card = await repo.get_card(card_id)
    formatted = format_card_telegram(card)
    updated_text = f"Карточка обновлена\\!\n\n{formatted}"
    await update.message.reply_text(
        updated_text,
        parse_mode="MarkdownV2",
        reply_markup=card_inline_keyboard(card_id),
    )
    user_id = update.effective_user.id
    owner_id = get_lesson_owner(user_id)
    await _notify_partner(context, user_id, owner_id,
        text=updated_text, parse_mode="MarkdownV2",
        reply_markup=card_inline_keyboard(card_id))
    return True
