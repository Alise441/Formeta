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
    examples = card.get("examples", [])

    lines = [f"*{_escape_md(card['base_form'])}* \\({_escape_md(word_type)}\\)"]
    lines.append("━━━━━━━━━━━━━━━━━")

    # Forms
    if card["word_type"] == "verb":
        form_parts = []
        if forms.get("prateritum"):
            form_parts.append(forms["prateritum"])
        if forms.get("perfekt"):
            form_parts.append(forms["perfekt"])
        if form_parts:
            lines.append(f"Формы: {_escape_md(' — '.join(form_parts))}")
        if forms.get("rektion"):
            lines.append(f"Управление: {_escape_md(forms['rektion'])}")
    elif card["word_type"] == "noun":
        noun_parts = []
        if forms.get("artikel"):
            noun_parts.append(f"Артикль: {forms['artikel']}")
        if forms.get("plural"):
            noun_parts.append(f"Pl\\. {_escape_md(forms['plural'])}")
        if forms.get("genitiv"):
            noun_parts.append(f"Gen\\. {_escape_md(forms['genitiv'])}")
        lines.extend(noun_parts)
    elif card["word_type"] == "adjective":
        if forms.get("komparativ"):
            lines.append(f"Сравн\\.: {_escape_md(forms['komparativ'])}")
        if forms.get("superlativ"):
            lines.append(f"Превосх\\.: {_escape_md(forms['superlativ'])}")
        if forms.get("rektion"):
            lines.append(f"Управление: {_escape_md(forms['rektion'])}")
    elif card["word_type"] == "preposition":
        if forms.get("kasus"):
            lines.append(f"Падеж: {_escape_md(forms['kasus'])}")

    lines.append(f"Перевод: {_escape_md(card['translation'])}")

    if examples:
        lines.append("")
        lines.append("Примеры:")
        for ex in examples:
            lines.append(f" \\- {_escape_md(ex)}")

    return "\n".join(lines)


def format_card_anki_front(card: dict) -> str:
    """Format card front side for Anki (HTML)."""
    word_type = WORD_TYPE_LABELS.get(card["word_type"], card["word_type"])
    forms = card.get("forms", {})

    lines = [f"<h2>{card['base_form']}</h2>"]
    lines.append(f"<i>({word_type})</i>")

    if card["word_type"] == "verb":
        form_parts = []
        if forms.get("prateritum"):
            form_parts.append(forms["prateritum"])
        if forms.get("perfekt"):
            form_parts.append(forms["perfekt"])
        if form_parts:
            lines.append(f"<p>{' — '.join(form_parts)}</p>")
        if forms.get("rektion"):
            lines.append(f"<p>{forms['rektion']}</p>")
    elif card["word_type"] == "noun":
        parts = []
        if forms.get("plural"):
            parts.append(f"Pl. {forms['plural']}")
        if forms.get("genitiv"):
            parts.append(f"Gen. {forms['genitiv']}")
        if parts:
            lines.append(f"<p>{' | '.join(parts)}</p>")
    elif card["word_type"] == "adjective":
        parts = []
        if forms.get("komparativ"):
            parts.append(forms["komparativ"])
        if forms.get("superlativ"):
            parts.append(forms["superlativ"])
        if parts:
            lines.append(f"<p>{' — '.join(parts)}</p>")
        if forms.get("rektion"):
            lines.append(f"<p>{forms['rektion']}</p>")
    elif card["word_type"] == "preposition":
        if forms.get("kasus"):
            lines.append(f"<p>+ {forms['kasus']}</p>")

    return "\n".join(lines)


def format_card_anki_back(card: dict) -> str:
    """Format card back side for Anki (HTML). Bold markers **word** → <b>word</b>."""
    examples = card.get("examples", [])

    lines = [f"<h3>{card['translation']}</h3>"]

    if examples:
        lines.append("<ul>")
        for ex in examples:
            # Convert **word** to <b>word</b>
            ex_html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", ex)
            lines.append(f"<li>{ex_html}</li>")
        lines.append("</ul>")

    return "\n".join(lines)
