import os
import genanki

from config import ANKI_OUTPUT_DIR
from bot.formatters import (
    format_card_anki_front, format_card_anki_back,
    format_anki_translation_hint, format_anki_base_with_forms,
    format_anki_noun_bare, format_anki_noun_full,
    WORD_TYPE_LABELS,
)

# Stable IDs for the model and deck (generated once, kept constant)
MODEL_ID_V2 = 1607392320
DECK_ID_BASE = 2059400110

CARD_CSS = """
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
.hint { font-size: 14px; opacity: 0.6; margin-top: 8px; }
.gender-q { font-size: 16px; opacity: 0.5; margin-top: 12px; }
"""

CARD_MODEL = genanki.Model(
    MODEL_ID_V2,
    "Formeta German v2",
    fields=[
        {"name": "Front"},
        {"name": "Back"},
        {"name": "TranslationHint"},
        {"name": "WordType"},
        {"name": "BaseFormWithForms"},
        {"name": "NounBare"},
        {"name": "NounFull"},
    ],
    templates=[
        {
            "name": "DE → RU",
            "qfmt": "{{Front}}",
            "afmt": '{{FrontSide}}<hr id="answer">{{Back}}',
        },
        {
            "name": "RU/EN → DE",
            "qfmt": '{{#TranslationHint}}<h3>{{TranslationHint}}</h3><p class="hint">{{WordType}}</p>{{/TranslationHint}}',
            "afmt": '{{FrontSide}}<hr id="answer">{{BaseFormWithForms}}',
        },
        {
            "name": "Artikel",
            "qfmt": '{{#NounBare}}<h2>{{NounBare}}</h2><p class="gender-q">der / die / das?</p>{{/NounBare}}',
            "afmt": '{{FrontSide}}<hr id="answer">{{NounFull}}',
        },
    ],
    css=CARD_CSS,
)


def generate_deck(lesson_id: int, cards: list[dict], lesson_date: str, lesson_type: str = "lesson") -> str:
    """Generate an Anki deck. lesson_date should be in dd.mm format."""
    os.makedirs(ANKI_OUTPUT_DIR, exist_ok=True)

    label = "Урок" if lesson_type == "lesson" else "Сессия"
    deck_name = f"Formeta — #{lesson_id} {label} {lesson_date}"

    deck = genanki.Deck(
        DECK_ID_BASE + lesson_id,
        deck_name,
    )

    for card in cards:
        front = format_card_anki_front(card)
        back = format_card_anki_back(card)
        translation_hint = format_anki_translation_hint(card)
        word_type = WORD_TYPE_LABELS.get(card["word_type"], card["word_type"]).capitalize()
        base_with_forms = format_anki_base_with_forms(card)
        noun_bare = format_anki_noun_bare(card)
        noun_full = format_anki_noun_full(card)

        note = genanki.Note(
            model=CARD_MODEL,
            fields=[front, back, translation_hint, word_type, base_with_forms, noun_bare, noun_full],
            guid=genanki.guid_for(f"formeta-{card['id']}"),
        )
        deck.add_note(note)

    filepath = os.path.join(ANKI_OUTPUT_DIR, f"{deck_name}.apkg")
    genanki.Package(deck).write_to_file(filepath)
    return filepath
