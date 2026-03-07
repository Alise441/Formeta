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
        padding: 20px;
    }
    h2 { margin: 0 0 8px 0; }
    h3 { margin: 0 0 12px 0; }
    i { font-size: 14px; opacity: 0.7; }
    p { margin: 4px 0; }
    .translation-en { font-style: italic; opacity: 0.7; }
    .prep { opacity: 0.7; }
    .example { margin-top: 12px; }
    .example-ru { opacity: 0.7; font-size: 16px; }
    b { color: #5cb85c; }
    """,
)


def generate_deck(lesson_id: int, cards: list[dict], lesson_date: str) -> str:
    """Generate an Anki deck. lesson_date should be in dd.mm format."""
    os.makedirs(ANKI_OUTPUT_DIR, exist_ok=True)

    deck_name = f"Formeta — Урок #{lesson_id} {lesson_date}"

    deck = genanki.Deck(
        DECK_ID_BASE + lesson_id,
        deck_name,
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

    filepath = os.path.join(ANKI_OUTPUT_DIR, f"{deck_name}.apkg")
    genanki.Package(deck).write_to_file(filepath)
    return filepath
