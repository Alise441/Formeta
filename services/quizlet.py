import os

from config import ANKI_OUTPUT_DIR
from bot.formatters import _is_verb, _has_form


def _format_front(card: dict) -> str:
    forms = card.get("forms", {})
    base = card["base_form"]

    if _is_verb(card["word_type"]):
        parts = [base]
        if _has_form(forms.get("prasens_3p")):
            parts.append(forms["prasens_3p"])
        if _has_form(forms.get("prateritum")):
            parts.append(forms["prateritum"])
        if _has_form(forms.get("perfekt")):
            parts.append(forms["perfekt"])
        return " — ".join(parts)
    elif card["word_type"] == "noun":
        parts = [base]
        if _has_form(forms.get("plural")):
            parts.append(forms["plural"])
        if _has_form(forms.get("genitiv")):
            parts.append(forms["genitiv"])
        return ", ".join(parts)
    elif card["word_type"] == "adjective":
        parts = [base]
        if _has_form(forms.get("komparativ")):
            parts.append(forms["komparativ"])
        if _has_form(forms.get("superlativ")):
            parts.append(forms["superlativ"])
        return " — ".join(parts)
    elif card["word_type"] == "preposition":
        if _has_form(forms.get("kasus")):
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


def _strip_article(text: str) -> str:
    """Remove German article from the beginning of a word."""
    for art in ("der ", "die ", "das "):
        if text.startswith(art):
            return text[len(art):]
    return text


def _format_front_en_only(card: dict) -> str:
    """Front side for EN-only mode: word + forms, no articles for nouns."""
    forms = card.get("forms", {})
    base = card["base_form"]

    if _is_verb(card["word_type"]):
        parts = [base]
        if _has_form(forms.get("prasens_3p")):
            parts.append(forms["prasens_3p"])
        if _has_form(forms.get("prateritum")):
            parts.append(forms["prateritum"])
        if _has_form(forms.get("perfekt")):
            parts.append(forms["perfekt"])
        return " — ".join(parts)
    elif card["word_type"] == "noun":
        parts = [base]
        if _has_form(forms.get("plural")):
            parts.append(forms["plural"])
        return " — ".join(parts)
    else:
        return base


def _strip_en_article(text: str) -> str:
    """Remove English articles from the beginning."""
    for art in ("the ", "a ", "an "):
        if text.lower().startswith(art):
            return text[len(art):]
    return text


def _format_back_en_only(card: dict) -> str:
    """Back side for EN-only mode: English translation without articles."""
    translation = card.get("translation_en", card["translation"])
    return _strip_en_article(translation)


def generate_quizlet_export(lesson_id: int, cards: list[dict], lesson_date: str,
                            en_only: bool = False) -> str:
    os.makedirs(ANKI_OUTPUT_DIR, exist_ok=True)

    card_blocks = []
    for card in cards:
        if en_only:
            # Skip phrases and sentences
            if card["word_type"] == "phrase":
                continue
            front = _format_front_en_only(card)
            back = _format_back_en_only(card)
        else:
            front = _format_front(card)
            back = _format_back(card)
        card_blocks.append(f"{front}\t{back}")

    filepath = os.path.join(ANKI_OUTPUT_DIR, f"formeta_quizlet_{lesson_date}.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n\n".join(card_blocks))
    return filepath
