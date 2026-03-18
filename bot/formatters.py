import re

WORD_TYPE_LABELS = {
    "verb": "глагол",
    "verb_irregular": "неправильный глагол",
    "noun": "существительное",
    "adjective": "прилагательное",
    "adverb": "наречие",
    "phrase": "фраза",
    "preposition": "предлог",
    "pronoun": "местоимение",
    "conjunction": "союз",
    "particle": "частица",
}

def _is_verb(word_type: str) -> bool:
    return word_type in ("verb", "verb_irregular")


def _escape_md(text: str) -> str:
    """Escape special MarkdownV2 characters, preserving **bold** markers."""
    # First, temporarily replace **bold** markers
    bold_parts = []
    def replace_bold(m):
        bold_parts.append(m.group(1))
        return f"\x00BOLD{len(bold_parts) - 1}\x00"

    text = re.sub(r"\*\*(.+?)\*\*", replace_bold, text)

    # Escape all special characters
    special = r"_[]()~`>#+-=|{}.!"
    for ch in special:
        text = text.replace(ch, f"\\{ch}")

    # Restore bold markers
    for i, part in enumerate(bold_parts):
        escaped_part = part
        for ch in special:
            escaped_part = escaped_part.replace(ch, f"\\{ch}")
        text = text.replace(f"\x00BOLD{i}\x00", f"*{escaped_part}*")

    return text


def format_card_telegram(card: dict, show_translation_en: bool = False) -> str:
    """Format a card for Telegram MarkdownV2 display."""
    word_type = WORD_TYPE_LABELS.get(card["word_type"], card["word_type"])
    forms = card.get("forms", {})
    example = card.get("example", {})
    prepositions = card.get("prepositions", [])

    # Header: word — translation
    lines = [
        f"*{_escape_md(card['base_form'])}* — {_escape_md(card['translation'])}"
    ]

    if show_translation_en and card.get("translation_en"):
        lines.append(_escape_md(card["translation_en"]))

    # Example sentence with translation
    if example and example.get("de"):
        lines.append(f"{_escape_md(example['de'])}")
        if example.get("ru"):
            lines.append(f"— {_escape_md(example['ru'])}")

    lines.append("━━━━━━━━━━━━━━━━━")

    # Part of speech
    lines.append(_escape_md(word_type.capitalize()))

    # Forms (no labels)
    if _is_verb(card["word_type"]):
        form_parts = []
        if forms.get("prasens_3p"):
            form_parts.append(forms["prasens_3p"])
        if forms.get("prateritum"):
            form_parts.append(forms["prateritum"])
        if forms.get("perfekt"):
            form_parts.append(forms["perfekt"])
        if form_parts:
            lines.append(_escape_md(" — ".join(form_parts)))
    elif card["word_type"] == "noun":
        noun_parts = []
        if forms.get("plural"):
            noun_parts.append(forms["plural"])
        if forms.get("genitiv"):
            noun_parts.append(forms["genitiv"])
        if noun_parts:
            lines.append(_escape_md(", ".join(noun_parts)))
    elif card["word_type"] == "adjective":
        adj_parts = []
        if forms.get("komparativ"):
            adj_parts.append(forms["komparativ"])
        if forms.get("superlativ"):
            adj_parts.append(forms["superlativ"])
        if adj_parts:
            lines.append(_escape_md(" — ".join(adj_parts)))
    elif card["word_type"] == "preposition":
        if forms.get("kasus"):
            lines.append(_escape_md(f"+ {forms['kasus']}"))

    # Prepositions / governance
    for prep in prepositions:
        usage = prep.get("usage", "")
        meaning = prep.get("meaning", "")
        if usage and meaning:
            lines.append(_escape_md(f"{usage} — {meaning}"))
        elif usage:
            lines.append(_escape_md(usage))

    return "\n".join(lines)


WORD_TYPE_FROM_LABEL = {v.capitalize(): k for k, v in WORD_TYPE_LABELS.items()}


def format_card_editable(card: dict) -> str:
    """Format card as plain text for editing. Mirrors the Telegram display."""
    word_type = WORD_TYPE_LABELS.get(card["word_type"], card["word_type"])
    forms = card.get("forms", {})
    example = card.get("example", {})
    prepositions = card.get("prepositions", [])

    lines = [f"{card['base_form']} — {card['translation']}"]

    if example and example.get("de"):
        ex_line = example["de"]
        if example.get("ru"):
            ex_line += f" — {example['ru']}"
        lines.append(ex_line)

    lines.append("━━━━━━━━━━━━━━━━━")
    lines.append(word_type.capitalize())

    if _is_verb(card["word_type"]):
        form_parts = []
        if forms.get("prasens_3p"):
            form_parts.append(forms["prasens_3p"])
        if forms.get("prateritum"):
            form_parts.append(forms["prateritum"])
        if forms.get("perfekt"):
            form_parts.append(forms["perfekt"])
        if form_parts:
            lines.append(" — ".join(form_parts))
    elif card["word_type"] == "noun":
        noun_parts = []
        if forms.get("plural"):
            noun_parts.append(forms["plural"])
        if forms.get("genitiv"):
            noun_parts.append(forms["genitiv"])
        if noun_parts:
            lines.append(", ".join(noun_parts))
    elif card["word_type"] == "adjective":
        adj_parts = []
        if forms.get("komparativ"):
            adj_parts.append(forms["komparativ"])
        if forms.get("superlativ"):
            adj_parts.append(forms["superlativ"])
        if adj_parts:
            lines.append(" — ".join(adj_parts))
    elif card["word_type"] == "preposition":
        if forms.get("kasus"):
            lines.append(f"+ {forms['kasus']}")

    for prep in prepositions:
        usage = prep.get("usage", "")
        meaning = prep.get("meaning", "")
        if usage and meaning:
            lines.append(f"{usage} — {meaning}")
        elif usage:
            lines.append(usage)

    return "\n".join(lines)


def parse_card_editable(text: str) -> dict:
    """Parse edited card text back into card fields."""
    lines = [l for l in text.strip().split("\n") if l.strip()]

    # Find separator line
    sep_idx = None
    for i, line in enumerate(lines):
        if "━" in line or "---" in line or "———" in line:
            sep_idx = i
            break

    if sep_idx is None:
        # No separator — treat as simple: line1 = word — translation, rest = keep
        sep_idx = len(lines)

    # Lines before separator: header + example
    header_lines = lines[:sep_idx]
    # Lines after separator: type, forms, prepositions
    detail_lines = lines[sep_idx + 1:] if sep_idx < len(lines) else []

    # Parse header (line 1: base_form — translation)
    base_form = ""
    translation = ""
    if header_lines:
        parts = header_lines[0].split(" — ", 1)
        base_form = parts[0].strip()
        translation = parts[1].strip() if len(parts) > 1 else ""

    # Parse example: can be one line "de — ru" or two lines "de" / "— ru"
    example = {}
    if len(header_lines) > 1:
        ex_line = header_lines[1]
        ex_parts = ex_line.split(" — ", 1)
        example["de"] = ex_parts[0].strip()
        example["ru"] = ex_parts[1].strip() if len(ex_parts) > 1 else ""
        # Check if next line is the RU translation (starts with "— ")
        if not example["ru"] and len(header_lines) > 2:
            next_line = header_lines[2].strip()
            if next_line.startswith("— ") or next_line.startswith("- "):
                example["ru"] = next_line.lstrip("—- ").strip()

    # Parse word type
    word_type = "phrase"
    if detail_lines:
        type_label = detail_lines[0].strip()
        word_type = WORD_TYPE_FROM_LABEL.get(type_label, "phrase")

    # Parse forms and prepositions
    forms = {}
    prepositions = []
    form_lines = detail_lines[1:]  # everything after word type

    if form_lines:
        # First non-preposition line is forms
        first = form_lines[0]
        rest = form_lines[1:]

        if _is_verb(word_type):
            parts = [p.strip() for p in first.split(" — ")]
            if len(parts) >= 3:
                forms["prasens_3p"] = parts[0]
                forms["prateritum"] = parts[1]
                forms["perfekt"] = parts[2]
            elif len(parts) == 2:
                forms["prateritum"] = parts[0]
                forms["perfekt"] = parts[1]
        elif word_type == "noun":
            parts = [p.strip() for p in first.split(", ")]
            if len(parts) >= 1:
                forms["plural"] = parts[0]
            if len(parts) >= 2:
                forms["genitiv"] = parts[1]
            # Extract artikel from base_form
            bf_parts = base_form.split(" ", 1)
            if bf_parts[0].lower() in ("der", "die", "das"):
                forms["artikel"] = bf_parts[0]
        elif word_type == "adjective":
            parts = [p.strip() for p in first.split(" — ")]
            if len(parts) >= 1:
                forms["komparativ"] = parts[0]
            if len(parts) >= 2:
                forms["superlativ"] = parts[1]
        elif word_type == "preposition" and first.startswith("+"):
            forms["kasus"] = first[1:].strip()
            rest = form_lines[1:]
        else:
            rest = form_lines  # first line wasn't forms

        for line in rest:
            parts = line.split(" — ", 1)
            prep = {"usage": parts[0].strip()}
            if len(parts) > 1:
                prep["meaning"] = parts[1].strip()
            prepositions.append(prep)

    return {
        "base_form": base_form,
        "translation": translation,
        "word_type": word_type,
        "forms": forms,
        "example": example,
        "prepositions": prepositions,
    }


def format_card_anki_front(card: dict) -> str:
    """Format card front side for Anki (HTML)."""
    word_type = WORD_TYPE_LABELS.get(card["word_type"], card["word_type"])
    forms = card.get("forms", {})

    # Base form + forms in one line
    if _is_verb(card["word_type"]):
        form_parts = [card["base_form"]]
        if forms.get("prasens_3p"):
            form_parts.append(forms["prasens_3p"])
        if forms.get("prateritum"):
            form_parts.append(forms["prateritum"])
        if forms.get("perfekt"):
            form_parts.append(forms["perfekt"])
        lines = [f"<h2>{' — '.join(form_parts)}</h2>"]
    elif card["word_type"] == "noun":
        parts = [card["base_form"]]
        if forms.get("plural"):
            parts.append(forms["plural"])
        if forms.get("genitiv"):
            parts.append(forms["genitiv"])
        lines = [f"<h2>{', '.join(parts)}</h2>"]
    elif card["word_type"] == "adjective":
        parts = [card["base_form"]]
        if forms.get("komparativ"):
            parts.append(forms["komparativ"])
        if forms.get("superlativ"):
            parts.append(forms["superlativ"])
        lines = [f"<h2>{' — '.join(parts)}</h2>"]
    elif card["word_type"] == "preposition":
        if forms.get("kasus"):
            lines = [f"<h2>{card['base_form']} + {forms['kasus']}</h2>"]
        else:
            lines = [f"<h2>{card['base_form']}</h2>"]
    else:
        lines = [f"<h2>{card['base_form']}</h2>"]

    lines.append(f"<i>{word_type.capitalize()}</i>")

    return "\n".join(lines)


def format_card_anki_back(card: dict) -> str:
    """Format card back side for Anki (HTML)."""
    example = card.get("example", {})
    prepositions = card.get("prepositions", [])

    lines = [f"<h3>{card['translation']}</h3>"]

    if card.get("translation_en"):
        lines.append(f"<p class='translation-en'>{card['translation_en']}</p>")

    if example and example.get("de"):
        ex_html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", example["de"])
        lines.append(f"<p class='example'>{ex_html}</p>")
        if example.get("ru"):
            lines.append(f"<p class='example-ru'>— {example['ru']}</p>")

    for prep in prepositions:
        usage = prep.get("usage", "")
        meaning = prep.get("meaning", "")
        if usage and meaning:
            lines.append(f"<p class='prep'>{usage} — {meaning}</p>")
        elif usage:
            lines.append(f"<p class='prep'>{usage}</p>")

    return "\n".join(lines)
