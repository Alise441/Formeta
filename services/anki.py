import os
import genanki
import random

from config import ANKI_OUTPUT_DIR
from bot.formatters import format_card_anki_front, format_card_anki_back

# Stable IDs for the model and deck (generated once, kept constant)
MODEL_ID = 1607392319
DECK_ID_BASE = 2059400110

CARD_MODEL = genanki.Model(
    MODEL_ID,
    "Formeta German",
    fields=[
        {"name": "Front"},
        {"name": "Back"},
    ],
    templates=[
        {
            "name": "DE → RU",
            "qfmt": "{{Front}}",
            "afmt": '{{FrontSide}}<hr id="answer">{{Back}}',
        },
    ],
    css="""
    .card {
        font-family: 'Helvetica Neue', Arial, sans-serif;
        font-size: 18px;
        text-align: center;
        color: #333;
        background-color: #fafafa;
        padding: 20px;
    }
    h2 { margin: 0 0 8px 0; color: #1a1a2e; }
    h3 { margin: 0 0 12px 0; color: #16213e; }
    i { color: #666; font-size: 14px; }
    p { margin: 4px 0; }
    ul { text-align: left; padding-left: 20px; }
    li { margin: 6px 0; }
    b { color: #e94560; }
    """,
)


def generate_deck(lesson_id: int, cards: list[dict]) -> str:
    os.makedirs(ANKI_OUTPUT_DIR, exist_ok=True)

    deck = genanki.Deck(
        DECK_ID_BASE + lesson_id,
        f"Formeta — Урок #{lesson_id}",
    )

    for card in cards:
        front = format_card_anki_front(card)
        back = format_card_anki_back(card)
        note = genanki.Note(
            model=CARD_MODEL,
            fields=[front, back],
            guid=genanki.guid_for(f"formeta-{card['id']}"),
        )
        deck.add_note(note)

    filepath = os.path.join(ANKI_OUTPUT_DIR, f"formeta_lesson_{lesson_id}.apkg")
    genanki.Package(deck).write_to_file(filepath)
    return filepath
