import re

WORD_TYPE_LABELS = {
    "verb": "глагол",
    "noun": "существительное",
    "adjective": "прилагательное",
    "adverb": "наречие",
    "phrase": "фраза",
    "preposition": "предлог",
}


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


def format_card_telegram(card: dict) -> str:
    """Format a card for Telegram MarkdownV2 display."""
    word_type = WORD_TYPE_LABELS.get(card["word_type"], card["word_type"])
    forms = card.get("forms", {})
    example = card.get("example", {})
    prepositions = card.get("prepositions", [])

    # Header: word — translation
    lines = [
        f"*{_escape_md(card['base_form'])}* — {_escape_md(card['translation'])}"
    ]

    # Example sentence with translation
    if example and example.get("de"):
        lines.append(f"{_escape_md(example['de'])}")
        if example.get("ru"):
            lines.append(f"— {_escape_md(example['ru'])}")

    lines.append("━━━━━━━━━━━━━━━━━")

    # Part of speech
    lines.append(_escape_md(word_type.capitalize()))

    # Forms (no labels)
    if card["word_type"] == "verb":
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


def format_card_anki_front(card: dict) -> str:
    """Format card front side for Anki (HTML)."""
    word_type = WORD_TYPE_LABELS.get(card["word_type"], card["word_type"])
    forms = card.get("forms", {})
    prepositions = card.get("prepositions", [])

    lines = [f"<h2>{card['base_form']}</h2>"]
    lines.append(f"<i>{word_type.capitalize()}</i>")

    if card["word_type"] == "verb":
        form_parts = []
        if forms.get("prasens_3p"):
            form_parts.append(forms["prasens_3p"])
        if forms.get("prateritum"):
            form_parts.append(forms["prateritum"])
        if forms.get("perfekt"):
            form_parts.append(forms["perfekt"])
        if form_parts:
            lines.append(f"<p>{' — '.join(form_parts)}</p>")
    elif card["word_type"] == "noun":
        parts = []
        if forms.get("plural"):
            parts.append(forms["plural"])
        if forms.get("genitiv"):
            parts.append(forms["genitiv"])
        if parts:
            lines.append(f"<p>{', '.join(parts)}</p>")
    elif card["word_type"] == "adjective":
        parts = []
        if forms.get("komparativ"):
            parts.append(forms["komparativ"])
        if forms.get("superlativ"):
            parts.append(forms["superlativ"])
        if parts:
            lines.append(f"<p>{' — '.join(parts)}</p>")
    elif card["word_type"] == "preposition":
        if forms.get("kasus"):
            lines.append(f"<p>+ {forms['kasus']}</p>")

    for prep in prepositions:
        usage = prep.get("usage", "")
        meaning = prep.get("meaning", "")
        if usage and meaning:
            lines.append(f"<p class='prep'>{usage} — {meaning}</p>")
        elif usage:
            lines.append(f"<p class='prep'>{usage}</p>")

    return "\n".join(lines)


def format_card_anki_back(card: dict) -> str:
    """Format card back side for Anki (HTML)."""
    example = card.get("example", {})

    lines = [f"<h3>{card['translation']}</h3>"]

    if example and example.get("de"):
        ex_html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", example["de"])
        lines.append(f"<p class='example'>{ex_html}</p>")
        if example.get("ru"):
            lines.append(f"<p class='example-ru'>— {example['ru']}</p>")

    return "\n".join(lines)
