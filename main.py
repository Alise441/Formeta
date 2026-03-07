import logging

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, is_teacher
from db.models import init_db
from bot.keyboards import (
    BTN_START_LESSON, BTN_END_LESSON, BTN_EXPORT, BTN_EXPORT_QUIZLET, BTN_RESUME, BTN_HISTORY, BTN_WORDS,
    BTN_START_SESSION, BTN_END_SESSION, BTN_RESUME_SESSION,
)
from bot.handlers import (
    cmd_start,
    handle_start_lesson,
    handle_start_session,
    handle_end_lesson,
    handle_resume_lesson,
    handle_resume_session,
    handle_export,
    handle_export_quizlet,
    handle_history,
    handle_words,
    handle_word,
    handle_edit_reply,
    callback_delete,
    callback_confirm_delete,
    callback_cancel_delete,
    callback_edit,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


async def text_router(update, context):
    """Route text messages: button labels → handlers, other text → word processing."""
    text = update.message.text

    # Check if user is in edit mode
    if context.user_data.get("editing_card_id"):
        handled = await handle_edit_reply(update, context)
        if handled:
            return

    # Teachers only send words — no button routing
    if is_teacher(update.effective_user.id):
        await handle_word(update, context)
        return

    routes = {
        BTN_START_LESSON: handle_start_lesson,
        BTN_START_SESSION: handle_start_session,
        BTN_END_LESSON: handle_end_lesson,
        BTN_END_SESSION: handle_end_lesson,
        BTN_EXPORT: handle_export,
        BTN_EXPORT_QUIZLET: handle_export_quizlet,
        BTN_RESUME: handle_resume_lesson,
        BTN_RESUME_SESSION: handle_resume_session,
        BTN_HISTORY: handle_history,
        BTN_WORDS: handle_words,
    }

    handler = routes.get(text)
    if handler:
        await handler(update, context)
    else:
        await handle_word(update, context)


async def post_init(application):
    await init_db()


def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    app.add_handler(CallbackQueryHandler(callback_edit, pattern=r"^edit:"))
    app.add_handler(CallbackQueryHandler(callback_delete, pattern=r"^delete:"))
    app.add_handler(CallbackQueryHandler(callback_confirm_delete, pattern=r"^confirm_delete:"))
    app.add_handler(CallbackQueryHandler(callback_cancel_delete, pattern=r"^cancel_delete:"))

    logging.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
