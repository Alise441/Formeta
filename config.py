import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
ALLOWED_USER_IDS = [
    int(uid.strip())
    for uid in os.environ.get("ALLOWED_USER_IDS", "").split(",")
    if uid.strip()
]

DB_PATH = os.environ.get("DB_PATH", "formeta.db")
ANKI_OUTPUT_DIR = os.environ.get("ANKI_OUTPUT_DIR", "exports")

# Teacher → Student mapping. Format: "teacher_id:student_id,teacher_id:student_id"
TEACHER_STUDENT_MAP = {}
for pair in os.environ.get("TEACHERS", "").split(","):
    pair = pair.strip()
    if ":" in pair:
        t, s = pair.split(":", 1)
        TEACHER_STUDENT_MAP[int(t.strip())] = int(s.strip())


def get_lesson_owner(user_id: int) -> int:
    return TEACHER_STUDENT_MAP.get(user_id, user_id)


def is_teacher(user_id: int) -> bool:
    return user_id in TEACHER_STUDENT_MAP


def get_teachers(student_id: int) -> list[int]:
    return [t for t, s in TEACHER_STUDENT_MAP.items() if s == student_id]
