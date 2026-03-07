import json
from datetime import datetime

import aiosqlite
from config import DB_PATH


def _connect():
    """Return a context manager for DB connection with Row factory."""
    return aiosqlite.connect(DB_PATH)


# --- Lessons ---

async def create_lesson() -> int:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("INSERT INTO lessons DEFAULT VALUES")
        await db.commit()
        return cursor.lastrowid


async def get_active_lesson() -> dict | None:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM lessons WHERE status = 'active' ORDER BY id DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def end_lesson(lesson_id: int):
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "UPDATE lessons SET status = 'ended', ended_at = ? WHERE id = ?",
            (datetime.now().isoformat(), lesson_id),
        )
        await db.commit()


async def resume_lesson(lesson_id: int):
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "UPDATE lessons SET status = 'active', ended_at = NULL WHERE id = ?",
            (lesson_id,),
        )
        await db.commit()


async def get_last_ended_lesson() -> dict | None:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM lessons WHERE status = 'ended' ORDER BY ended_at DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_recent_lessons(limit: int = 10) -> list[dict]:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM lessons ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# --- Cards ---

async def create_card(
    lesson_id: int,
    raw_input: str,
    base_form: str,
    word_type: str,
    forms: dict | None,
    translation: str,
    examples: list[str] | None,
    created_by: str | None,
) -> int:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """INSERT INTO cards
               (lesson_id, raw_input, base_form, word_type, forms, translation, examples, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                lesson_id,
                raw_input,
                base_form,
                word_type,
                json.dumps(forms, ensure_ascii=False) if forms else None,
                translation,
                json.dumps(examples, ensure_ascii=False) if examples else None,
                created_by,
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def get_card(card_id: int) -> dict | None:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        card = dict(row)
        card["forms"] = json.loads(card["forms"]) if card["forms"] else {}
        card["examples"] = json.loads(card["examples"]) if card["examples"] else []
        return card


async def get_lesson_cards(lesson_id: int) -> list[dict]:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM cards WHERE lesson_id = ? ORDER BY id", (lesson_id,)
        )
        rows = await cursor.fetchall()
        cards = []
        for row in rows:
            card = dict(row)
            card["forms"] = json.loads(card["forms"]) if card["forms"] else {}
            card["examples"] = json.loads(card["examples"]) if card["examples"] else []
            cards.append(card)
        return cards


async def update_card_translation(card_id: int, translation: str):
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "UPDATE cards SET translation = ? WHERE id = ?", (translation, card_id)
        )
        await db.commit()


async def delete_card(card_id: int):
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute("DELETE FROM cards WHERE id = ?", (card_id,))
        await db.commit()


async def count_lesson_cards(lesson_id: int) -> int:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT COUNT(*) FROM cards WHERE lesson_id = ?", (lesson_id,)
        )
        row = await cursor.fetchone()
        return row[0]
