import aiosqlite
from config import DB_PATH, ALLOWED_USER_IDS

SCHEMA = """
CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'active',
    lesson_type TEXT NOT NULL DEFAULT 'lesson'
);

CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER NOT NULL REFERENCES lessons(id),
    raw_input TEXT NOT NULL,
    base_form TEXT NOT NULL,
    word_type TEXT NOT NULL,
    forms TEXT,
    translation TEXT NOT NULL,
    examples TEXT,
    created_by TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()
    await _migrate_add_user_id()
    await _migrate_add_lesson_type()


async def _migrate_add_user_id():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("PRAGMA table_info(lessons)")
        columns = [row[1] for row in await cursor.fetchall()]
        if "user_id" not in columns:
            await db.execute(
                "ALTER TABLE lessons ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0"
            )
            owner_id = ALLOWED_USER_IDS[0] if ALLOWED_USER_IDS else 0
            await db.execute(
                "UPDATE lessons SET user_id = ? WHERE user_id = 0",
                (owner_id,),
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_lessons_user_status ON lessons(user_id, status)"
            )
            await db.commit()


async def _migrate_add_lesson_type():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("PRAGMA table_info(lessons)")
        columns = [row[1] for row in await cursor.fetchall()]
        if "lesson_type" not in columns:
            await db.execute(
                "ALTER TABLE lessons ADD COLUMN lesson_type TEXT NOT NULL DEFAULT 'lesson'"
            )
            await db.commit()
