# Formeta

Telegram bot for learning German vocabulary. Add words during a lesson — the bot automatically detects the base form, grammar, translations, and usage example. Cards can be exported to Anki or Quizlet.

## Tech Stack

- **Python 3.11+** — async/await
- **Claude API** (Anthropic SDK) — word analysis, sentence translation, image recognition
- **Telegram Bot API** (python-telegram-bot) — bot interface
- **SQLite** (aiosqlite) — async database with manual migrations
- **genanki** — Anki .apkg deck generation
- **Docker** + Docker Compose — deployment

## Features

- German word analysis via Claude API (base form, part of speech, grammatical forms, RU/EN translations, example)
- Word recognition from photos — send a photo with underlined words, the bot creates a card for each
- Full sentence handling — RU/EN translation without grammar breakdown
- Lessons (with teacher participation) and sessions (personal, without teacher)
- Card editing and deletion
- Anki export (.apkg) — 3 card types: DE→RU (recognition), RU/EN→DE (production), Gender (der/die/das for nouns)
- Quizlet export (.txt)
- Multi-user mode with data isolation
- Per-user card settings
- Teacher role: automatic lesson join, mutual notifications, word export with lesson and part-of-speech filtering

## Deployment

### Requirements

- Docker and Docker Compose
- Telegram Bot Token (get from [@BotFather](https://t.me/BotFather))
- Anthropic API Key (get at [console.anthropic.com](https://console.anthropic.com))

### Setup

1. Clone the repository:

```bash
git clone git@github.com:Alise441/Formeta.git
cd Formeta
```

2. Create a `.env` file:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
ANTHROPIC_API_KEY=your_api_key

# Telegram IDs of allowed users (comma-separated)
ALLOWED_USER_IDS=123456789,987654321

# Teachers (optional): teacher_id:student_id, comma-separated
TEACHERS=111111111:123456789
```

You can find your Telegram ID via [@userinfobot](https://t.me/userinfobot).

3. Start:

```bash
docker compose up -d --build
```

The bot is ready — send it `/start` in Telegram.

### Updating

```bash
git pull
docker compose up -d --build
```

### Data

The database and exported files are stored in the `data/` folder (Docker volume). Data persists across code updates.

## Usage

### Lesson vs Session

- **Lesson** — teacher automatically joins, sees words, and can add their own. Both receive notifications.
- **Session** — personal mode for independent study. Teacher doesn't receive notifications and doesn't participate.

### Adding Words

During an active lesson or session, simply send a German word or phrase in any form:

- `gelaufen` → bot detects the base form `laufen`, shows conjugations, translation, and example
- `die Häuser` → bot detects `das Haus`, shows plural and genitive
- `es geht um` → bot recognizes the phrase and shows translation with example
- A full sentence → bot shows only RU/EN translation

### Photos with Underlined Words

Send a photo of text (textbook, board, worksheet) with underlined or highlighted words — the bot recognizes all marked words and creates a card for each.

### Buttons

| Button | Action |
|--------|--------|
| Start Lesson | Start a lesson (teacher joins) |
| Start Session | Start a personal session |
| Lesson Words | Show all words of the current lesson/session |
| End Lesson/Session | End and proceed to export |
| Export to Anki | Download .apkg file |
| Export to Quizlet | Download .txt file |
| Resume Lesson/Session | Continue the last ended one |
| History | Show recent lessons and sessions |

Each card has inline **Edit** and **Delete** buttons.

### Teacher

When no lesson is active, the teacher sees an **Export Words** button:

1. Select lessons (checkboxes)
2. Select parts of speech (verbs, nouns, adjectives, phrases, other)
3. Get a `.txt` file with the word list

### Anki Export

1. End the lesson or session
2. Tap **Export to Anki**
3. The bot sends a `.apkg` file
4. Open the file in Anki (desktop) or import via AnkiDroid/AnkiMobile
5. The deck appears as `Formeta — #N Lesson dd.mm`

Each word generates up to 3 cards:
- **DE → RU** — recognition (German word → translation)
- **RU/EN → DE** — production (translation → German word), not created for phrases
- **Gender** — `der / die / das?` for nouns

### Quizlet Export

1. End the lesson or session
2. Tap **Export to Quizlet**
3. The bot sends a `.txt` file
4. Open [Quizlet](https://quizlet.com) → **Create** → **Import**
5. Paste the file contents into the import field
6. Term/definition separator: **Tab**
7. Card separator: **Custom** → **\n\n**

## Project Structure

```
Formeta/
├── main.py              # Entry point, message routing
├── config.py            # Configuration from .env
├── user_settings.py     # Per-user settings
├── bot/
│   ├── handlers.py      # Command and message handlers
│   ├── keyboards.py     # Reply and Inline keyboards
│   └── formatters.py    # Card formatting (Telegram, Anki, editor)
├── db/
│   ├── models.py        # DB schema and migrations
│   └── repository.py    # CRUD operations
├── services/
│   ├── llm.py           # Claude API integration
│   ├── anki.py          # .apkg deck generation
│   └── quizlet.py       # .txt generation for Quizlet
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## License

[MIT](LICENSE)
