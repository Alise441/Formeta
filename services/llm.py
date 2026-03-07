import json
import anthropic
from config import ANTHROPIC_API_KEY

client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """\
Ты — помощник для изучения немецкого языка. Пользователь отправляет тебе немецкое слово или фразу в любой форме (спряжённый глагол, множественное число, склонённое прилагательное и т.д.).

Твоя задача:
1. Определить базовую форму (инфинитив для глаголов, именительный падеж ед.ч. с артиклем для существительных и т.д.)
2. Определить часть речи (word_type): verb, verb_irregular, noun, adjective, adverb, phrase, preposition. Для глаголов: если глагол неправильный (сильный/нерегулярный — меняет корневую гласную в Präteritum или Partizip II), используй "verb_irregular", иначе "verb".
3. Сгенерировать грамматические формы в зависимости от части речи:
   - verb: prasens_3p (er/sie/es форма), prateritum, perfekt. Также заполни поле "prepositions" — список предлогов с управлением и кратким значением. Если у глагола нет предложного управления, верни пустой список.
   - noun: artikel (der/die/das), plural, genitiv (напр. des Hauses)
   - adjective: komparativ, superlativ. Если есть управление (напр. stolz auf + Akk), добавь в "prepositions".
   - adverb: без дополнительных форм
   - phrase: без отдельных форм
   - preposition: kasus (какой падеж требует: Akk, Dat, Gen)
4. Перевод на русский язык (краткий, 1-3 значения)
5. Перевод на английский язык (краткий, 1-3 значения)
6. ОДИН пример предложения уровня A2-B1 с переводом на русский. Выдели целевое слово двойными звёздочками (**слово**).

Ответь ТОЛЬКО валидным JSON без markdown-блоков, в таком формате:
{
  "base_form": "...",
  "word_type": "verb|noun|adjective|adverb|phrase|preposition",
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


async def analyze_word(text: str) -> dict:
    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": text}],
        system=SYSTEM_PROMPT,
    )
    content = message.content[0].text.strip()
    # Remove markdown code block if present
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
    return json.loads(content)
