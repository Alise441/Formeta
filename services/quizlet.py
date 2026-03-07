import os

from config import ANKI_OUTPUT_DIR
from bot.formatters import _is_verb


def _format_front(card: dict) -> str:
    forms = card.get("forms", {})
    base = card["base_form"]

    if _is_verb(card["word_type"]):
        parts = [base]
        if forms.get("prasens_3p"):
            parts.append(forms["prasens_3p"])
        if forms.get("prateritum"):
            parts.append(forms["prateritum"])
        if forms.get("perfekt"):
            parts.append(forms["perfekt"])
        return " — ".join(parts)
    elif card["word_type"] == "noun":
        parts = [base]
        if forms.get("plural"):
            parts.append(forms["plural"])
        if forms.get("genitiv"):
            parts.append(forms["genitiv"])
        return ", ".join(parts)
    elif card["word_type"] == "adjective":
        parts = [base]
        if forms.get("komparativ"):
            parts.append(forms["komparativ"])
        if forms.get("superlativ"):
            parts.append(forms["superlativ"])
        return " — ".join(parts)
    elif card["word_type"] == "preposition":
        if forms.get("kasus"):
            return f"{base} + {forms['kasus']}"
        return base
    else:
        return base


def _format_back(card: dict) -> str:
    lines = [card["translation"]]
    if card.get("translation_en"):
        lines.append(card["translation_en"])

    example = card.get("example", {})
    if example and example.get("de"):
        de = example["de"].replace("**", "")
        ex = de
        if example.get("ru"):
            ex += f" — {example['ru']}"
        lines.append(ex)

    prepositions = card.get("prepositions", [])
    for prep in prepositions:
        usage = prep.get("usage", "")
        meaning = prep.get("meaning", "")
        if usage and meaning:
            lines.append(f"{usage} — {meaning}")
        elif usage:
            lines.append(usage)

    return "\n".join(lines)


def generate_quizlet_export(lesson_id: int, cards: list[dict], lesson_date: str) -> str:
    os.makedirs(ANKI_OUTPUT_DIR, exist_ok=True)

    card_blocks = []
    for card in cards:
        front = _format_front(card)
        back = _format_back(card)
        card_blocks.append(f"{front}\t{back}")

    filepath = os.path.join(ANKI_OUTPUT_DIR, f"formeta_quizlet_{lesson_date}.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n\n".join(card_blocks))
    return filepath
