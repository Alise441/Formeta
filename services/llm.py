import base64
import json
import re
import anthropic
from config import ANTHROPIC_API_KEY

client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """\
Ты — помощник для изучения немецкого языка. Пользователь отправляет тебе немецкое слово, фразу или целое предложение.

ВАЖНО: Ты ВСЕГДА должен ответить валидным JSON. Никогда не отвечай текстом, пояснениями или отказом.

Сначала определи, что перед тобой:
- Если это ОДНО СЛОВО или КОРОТКОЕ СЛОВОСОЧЕТАНИЕ (до 3-4 слов, напр. "gelaufen", "die Häuser", "es geht um", "stolz auf") — выполни полный грамматический анализ (см. ниже).
- Если это ЦЕЛОЕ ПРЕДЛОЖЕНИЕ или ДЛИННАЯ ФРАЗА (5+ слов, содержит подлежащее и сказуемое) — используй word_type "phrase", в base_form верни текст как есть, forms пустой, prepositions пустой, example_de и example_ru пустые. Дай ТОЛЬКО перевод на русский и английский.

Полный анализ для слов и коротких словосочетаний:
1. Определить базовую форму (инфинитив для глаголов, именительный падеж ед.ч. с артиклем для существительных и т.д.)
2. Определить часть речи (word_type): verb, verb_irregular, noun, adjective, adverb, phrase, preposition, pronoun, conjunction, particle. Для глаголов: если глагол неправильный (сильный/нерегулярный — меняет корневую гласную в Präteritum или Partizip II), используй "verb_irregular", иначе "verb".
3. Сгенерировать грамматические формы в зависимости от части речи:
   - verb: prasens_3p (er/sie/es форма), prateritum, perfekt. Также заполни поле "prepositions" — список предлогов с управлением и кратким значением. Если у глагола нет предложного управления, верни пустой список.
   - noun: artikel (der/die/das), plural, genitiv (напр. des Hauses)
   - adjective: komparativ, superlativ. Если есть управление (напр. stolz auf + Akk), добавь в "prepositions".
   - adverb: без дополнительных форм
   - phrase: без отдельных форм
   - preposition: kasus (какой падеж требует: Akk, Dat, Gen)
   - pronoun: в base_form указать все родовые формы через " / " (напр. "jener / jene / jenes"), forms пустой
   - conjunction: без дополнительных форм
   - particle: без дополнительных форм
4. Перевод на русский язык (краткий, 1-3 значения)
5. Перевод на английский язык (краткий, 1-3 значения)
6. ОДИН пример предложения уровня A2-B1 с переводом на русский. Выдели целевое слово двойными звёздочками (**слово**).

Ответь ТОЛЬКО валидным JSON без markdown-блоков, в таком формате:
{
  "base_form": "...",
  "word_type": "verb|noun|adjective|adverb|phrase|preposition|pronoun|conjunction|particle",
  "forms": { ... },
  "prepositions": [{"usage": "...", "meaning": "..."}],
  "translation": "...",
  "translation_en": "...",
  "example_de": "...",
  "example_ru": "..."
}

Примеры:

Ввод: "gelaufen"
{
  "base_form": "laufen",
  "word_type": "verb_irregular",
  "forms": {
    "prasens_3p": "läuft",
    "prateritum": "lief",
    "perfekt": "ist gelaufen"
  },
  "prepositions": [
    {"usage": "laufen + auf (Akk)", "meaning": "бежать куда-то"},
    {"usage": "laufen + mit (Dat)", "meaning": "идти с кем-то"}
  ],
  "translation": "бежать, бегать; идти (пешком)",
  "translation_en": "to run; to walk",
  "example_de": "**Läuft** dein Computer noch?",
  "example_ru": "Твой компьютер ещё работает?"
}

Ввод: "die Häuser"
{
  "base_form": "das Haus",
  "word_type": "noun",
  "forms": {
    "artikel": "das",
    "plural": "die Häuser",
    "genitiv": "des Hauses"
  },
  "prepositions": [],
  "translation": "дом",
  "translation_en": "house",
  "example_de": "In diesem **Haus** wohnen viele Familien.",
  "example_ru": "В этом доме живёт много семей."
}

Ввод: "es geht um"
{
  "base_form": "es geht um + Akk",
  "word_type": "phrase",
  "forms": {},
  "prepositions": [],
  "translation": "речь идёт о...",
  "translation_en": "it is about...",
  "example_de": "In dem Film **geht es um** eine Liebesgeschichte.",
  "example_ru": "В этом фильме речь идёт о любовной истории."
}

Ввод: "stolz"
{
  "base_form": "stolz",
  "word_type": "adjective",
  "forms": {
    "komparativ": "stolzer",
    "superlativ": "am stolzesten"
  },
  "prepositions": [
    {"usage": "stolz + auf (Akk)", "meaning": "гордиться кем/чем-то"}
  ],
  "translation": "гордый",
  "translation_en": "proud",
  "example_de": "Sie ist **stolz** auf ihren Sohn.",
  "example_ru": "Она гордится своим сыном."
}
"""


import logging

logger = logging.getLogger(__name__)


def _fix_json(text: str) -> str:
    """Try to fix common JSON issues like unescaped quotes inside string values."""
    # Fix unescaped quotes inside JSON string values:
    # Match content between key-value quotes and escape inner quotes
    def fix_line(line: str) -> str:
        # Pattern: "key": "value with "quotes" inside"
        # Find the value part and escape inner quotes
        m = re.match(r'^(\s*"[^"]+"\s*:\s*)"(.+)"(,?\s*)$', line)
        if m:
            prefix, value, suffix = m.group(1), m.group(2), m.group(3)
            # Check if value has unescaped quotes
            if '"' in value:
                value = value.replace('\\"', '\x00').replace('"', '\\"').replace('\x00', '\\"')
                return f'{prefix}"{value}"{suffix}'
        return line
    return "\n".join(fix_line(l) for l in text.split("\n"))


def _parse_json(text: str):
    """Strip markdown code fences and parse JSON. Tries to fix and extract JSON on failure."""
    content = text.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to find JSON object or array in the response
        match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', content)
        if match:
            extracted = match.group(1)
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                pass
            # Try fixing unescaped quotes
            try:
                return json.loads(_fix_json(extracted))
            except json.JSONDecodeError:
                pass
        # Log raw response for debugging
        logger.error(f"Failed to parse LLM response:\n{content[:500]}")
        raise


async def analyze_word(text: str) -> dict:
    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": text}],
        system=SYSTEM_PROMPT,
    )
    return _parse_json(message.content[0].text)


IMAGE_SYSTEM_PROMPT = """\
Ты — помощник для изучения немецкого языка. Пользователь отправляет фото с немецким текстом, на котором некоторые слова подчёркнуты, обведены или выделены маркером/ручкой.

Твоя задача:
1. Найти ВСЕ подчёркнутые/выделенные слова или фразы на изображении.
2. Для каждого слова выполнить полный анализ:
   - Определить базовую форму (инфинитив для глаголов, именительный падеж ед.ч. с артиклем для существительных и т.д.)
   - Определить часть речи (word_type): verb, verb_irregular, noun, adjective, adverb, phrase, preposition. Для глаголов: если глагол неправильный (сильный/нерегулярный — меняет корневую гласную в Präteritum или Partizip II), используй "verb_irregular", иначе "verb".
   - Сгенерировать грамматические формы:
     - verb: prasens_3p, prateritum, perfekt + prepositions
     - noun: artikel, plural, genitiv
     - adjective: komparativ, superlativ + prepositions
     - adverb: без форм
     - phrase: без форм
     - preposition: kasus
   - Перевод на русский (1-3 значения)
   - Перевод на английский (1-3 значения)
   - ОДИН пример предложения уровня A2-B1 с переводом на русский. Выдели целевое слово двойными звёздочками (**слово**).

Ответь ТОЛЬКО валидным JSON — массивом объектов, без markdown-блоков:
[
  {
    "base_form": "...",
    "word_type": "verb|noun|adjective|adverb|phrase|preposition|pronoun|conjunction|particle",
    "forms": { ... },
    "prepositions": [{"usage": "...", "meaning": "..."}],
    "translation": "...",
    "translation_en": "...",
    "example_de": "...",
    "example_ru": "..."
  }
]

Если подчёркнутых слов нет, верни пустой массив: []
"""


async def analyze_image_words(image_bytes: bytes, media_type: str = "image/jpeg") -> list[dict]:
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
                {"type": "text", "text": "Найди все подчёркнутые или выделенные слова на изображении и проанализируй каждое."},
            ],
        }],
        system=IMAGE_SYSTEM_PROMPT,
    )
    return _parse_json(message.content[0].text)
