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
    example: dict | None = None,
    prepositions: list | None = None,
    created_by: str | None = None,
) -> int:
    # Pack example + prepositions into the examples column as JSON
    extra = {}
    if example:
        extra["example"] = example
    if prepositions:
        extra["prepositions"] = prepositions
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
                json.dumps(extra, ensure_ascii=False) if extra else None,
                created_by,
            ),
        )
        await db.commit()
        return cursor.lastrowid


def _parse_card(row) -> dict:
    card = dict(row)
    card["forms"] = json.loads(card["forms"]) if card["forms"] else {}
    extra = json.loads(card["examples"]) if card["examples"] else {}
    # Support both old format (list) and new format (dict with example/prepositions)
    if isinstance(extra, list):
        card["example"] = {}
        card["prepositions"] = []
    else:
        card["example"] = extra.get("example", {})
        card["prepositions"] = extra.get("prepositions", [])
    del card["examples"]
    return card


async def get_card(card_id: int) -> dict | None:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return _parse_card(row)


async def get_lesson_cards(lesson_id: int) -> list[dict]:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM cards WHERE lesson_id = ? ORDER BY id", (lesson_id,)
        )
        rows = await cursor.fetchall()
        return [_parse_card(row) for row in rows]


async def update_card_full(
    card_id: int,
    base_form: str,
    word_type: str,
    forms: dict | None,
    translation: str,
    example: dict | None = None,
    prepositions: list | None = None,
):
    extra = {}
    if example:
        extra["example"] = example
    if prepositions:
        extra["prepositions"] = prepositions
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """UPDATE cards SET base_form = ?, word_type = ?, forms = ?,
               translation = ?, examples = ? WHERE id = ?""",
            (
                base_form,
                word_type,
                json.dumps(forms, ensure_ascii=False) if forms else None,
                translation,
                json.dumps(extra, ensure_ascii=False) if extra else None,
                card_id,
            ),
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
