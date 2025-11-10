# Book Swap Marketplace Bot

Async-first Telegram marketplace for student textbook swaps. Users list used books via conversational flows, browse available listings inside Telegram, and query a lightweight Starlette JSON API.

## Features
- 📱 Telegram bot built with aiogram 3 (async).
- 🧭 Guided listing flow with FSM, condition keyboards, and confirmation step.
- 🔍 Browse flow with pagination and instant "contact seller" actions that notify both parties.
- ✅ Seller-only controls to mark items as sold.
- 🌐 Starlette API (`/healthz`, `/books`) with filtering and pagination.
- 🗃️ SQLModel + SQLAlchemy 2.x async stack, tuned for PostgreSQL (asyncpg) with SQLite fallback for local dev.
- 🛠️ Alembic migrations pre-configured for SQLModel metadata and async engines.
- ⚙️ Configuration via Pydantic v2 Settings (env vars + optional `.env`).

## Project Structure
```
.
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 20231003_0001_initial_tables.py
├── bot/
│   ├── __init__.py
│   ├── bot.py
│   ├── handlers.py
│   ├── keyboards.py
│   └── utils.py
├── config.py
├── db/
│   ├── __init__.py
│   ├── models.py
│   └── session.py
├── main.py
├── requirements.txt
├── scripts/
│   └── seed_example.py
├── web/
│   ├── __init__.py
│   └── app.py
└── README.md
```

## Prerequisites
- Python 3.11+
- PostgreSQL (recommended) or SQLite for local testing
- Telegram bot token from [@BotFather](https://t.me/BotFather)

## Installation
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration
Settings are typed via `pydantic-settings` (Pydantic v2). Values are loaded from environment variables and, if present, a `.env` file.

1. Copy `.env.example` and edit as needed:
   ```bash
   cp .env.example .env
   ```
2. Update values (at minimum `TELEGRAM_TOKEN` and `DATABASE_URL`).
   - PostgreSQL example: `postgresql+asyncpg://user:pass@localhost:5432/booksdb`
   - SQLite example: `sqlite:///./books.db` (automatically promoted to `sqlite+aiosqlite://` for async usage)

Available settings (see `config.py` for defaults):
- `TELEGRAM_TOKEN` (required)
- `DATABASE_URL` (required)
- `LOG_LEVEL` (default `INFO`)
- `PAGE_SIZE` (pagination default, default `10`)
- `UVICORN_HOST`, `UVICORN_PORT`, `UVICORN_RELOAD`
- `BOT_POLLING_INTERVAL`, `WEB_CONCURRENCY`

Validation happens at startup; missing/invalid values raise a helpful error.

## Database Migrations
Run Alembic using the async-aware configuration.

```bash
alembic upgrade head
```

Common commands:
- Generate new migration: `alembic revision --autogenerate -m "add something"`
- Roll back: `alembic downgrade -1`

The provided `env.py` imports `SQLModel.metadata` so autogenerate picks up model changes.

## Internationalization (i18n)
The bot supports multiple languages via GNU gettext. Currently configured for:
- **English (en)** - Default language
- **Persian (fa)** - فارسی

See [I18N_README.md](I18N_README.md) for detailed translation workflow and adding new languages.

**Quick translation update:**
```bash
# Extract strings from code
xgettext --from-code=UTF-8 --language=Python --keyword=T \
  --output=locale/messages.pot --add-comments app/bot/*.py

# Compile translations
msgfmt locale/fa/LC_MESSAGES/messages.po -o locale/fa/LC_MESSAGES/messages.mo
```

## Running the Stack
Launch both the Telegram bot and Starlette API with the unified entrypoint:

```bash
python main.py
```

This starts:
- aiogram long polling (async) for Telegram updates.
- Uvicorn-powered Starlette server on `http://<UVICORN_HOST>:<UVICORN_PORT>`.

Graceful shutdown: `Ctrl+C` (SIGINT) stops both services, closes DB connections, and disposes the async engine.

### Alternative: run web app only
```bash
uvicorn web.app:app --host 0.0.0.0 --port 8000
```

## Usage
### API
```bash
curl http://localhost:8000/healthz
curl "http://localhost:8000/books?page=1&per_page=10"
curl "http://localhost:8000/books?author=Rowling&condition=like_new"
```
Response payload:
```json
{
  "items": [
    {
      "id": 1,
      "title": "Linear Algebra",
      "author": "Gilbert Strang",
      "price": "25.00",
      "condition": "like_new",
      "is_sold": false,
      "created_at": "2025-09-01T12:34:56.123456",
      "seller": {
        "id": 5,
        "telegram_id": 12345678,
        "display": "@seller"
      },
      "metadata": null
    }
  ],
  "page": 1,
  "per_page": 10,
  "total": 1
}
```

### Telegram Bot
1. `/start` – registers you (upserts user profile) and shows menu.
2. **Post a book**
   - Provide title → author (`skip` allowed) → select condition → price → optional description.
   - Confirm listing to publish.
3. **Browse books**
   - Paginated list, buttons to contact sellers.
   - Contact sends you the seller’s public display name and notifies the seller with your handle.
4. **My listings**
   - Lists active books you posted.
   - Inline buttons let you mark individual listings as sold.

### Example Data Seeder
Populate sample listings for local demos:
```bash
python scripts/seed_example.py
```
(Requires the app environment variables to be set.)

## Scripts
`scripts/seed_example.py` connects via SQLModel, seeds a demo user and a few books, and marks one as sold. Adjust before running in production.

## Development Notes
- Logging defaults to `INFO`; set `LOG_LEVEL=DEBUG` for SQL echo (automatically toggles SQLAlchemy engine echo).
- Async DB URL normalisation automatically upgrades `postgresql://` → `postgresql+asyncpg://` and `sqlite://` → `sqlite+aiosqlite://`.
- `db/session.py` exposes `session_scope()` for bot handlers and Starlette endpoints to share consistent transactional patterns.
- Alembic downgrade drops the PostgreSQL enum type only when using Postgres, retaining compatibility with SQLite.

## Troubleshooting
- **Bot not responding**: verify `TELEGRAM_TOKEN`, ensure the process is running, and your machine can reach Telegram.
- **No books in `/browse` or `/books`**: users haven’t listed anything yet; seed via the script above.
- **PostgreSQL SSL or driver issues**: confirm the URL uses the `postgresql+asyncpg://` scheme; firewall/SSL issues surface in logs.
- **Starlette 404s**: ensure Uvicorn is running on the expected host/port.

## License
Add your preferred license (MIT/Apache/etc.).
