# Book Swap Bot

A Telegram bot that lets users list books they own and browse books from other users to facilitate local book exchanges.

## Features
- /start welcome & help message
- /addbook quick one-line format: `/addbook Title|Author|Condition(|Optional description)`
- /addbook guided multi-step flow (title → author → condition → description)
- /browse list of recent available books from other users (with owner info)
- /mybooks view your own listings
- Automatic user creation & profile updating on interaction
- Persistent storage with SQLModel (SQLAlchemy) + async engine (SQLite by default, PostgreSQL supported)
- Clean async architecture with Aiogram 3

## Tech Stack
- Python 3.11+
- [Aiogram 3](https://github.com/aiogram/aiogram) (async Telegram Bot API framework)
- SQLModel + SQLAlchemy Async (data models & ORM)

## Project Structure
```
app/
  main.py          # Entry point (bot startup)
  handlers.py      # Command & message handlers (FSM flows)
  database.py      # Async engine & session factory, init_db
  models.py        # SQLModel ORM models (User, Book, BookRequest)
README.md
```

## Data Models (summary)
- User: telegram_id, display_name, username, timestamps
- Book: title, author, condition, description, availability, owner relation
- BookRequest: (scaffolded) for future request / swap workflow

## Prerequisites
- Python 3.11+
- A Telegram Bot Token (create via @BotFather)
- (Optional) PostgreSQL database URL if not using default SQLite

## Installation
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Environment Variables
Create a `.env` file in project root:
```
BOT_TOKEN=123456:ABC-YourTelegramBotToken
# SQLite (default if unspecified)
# DATABASE_URL=sqlite+aiosqlite:///./data.db

# Optional
SQL_ECHO=false
```
Variables used:
- BOT_TOKEN (required)
- DATABASE_URL (optional, else SQLite file `data.db`)
- SQL_ECHO (true/false) enable SQL echo for debugging

## Running Locally
```bash
python app/main.py
```
On first run tables are created automatically.

## Usage Examples
Quick add (no prompts):
```
/addbook The Hobbit|J.R.R. Tolkien|like new|Collectors illustrated edition
```
Guided flow:
```
/addbook
# Bot asks for each field sequentially
```
Browse books:
```
/browse
```
Your listings:
```
/mybooks
```

## Extending
Potential additions:
- Book images (Telegram photo uploads + file storage)
- Inline keyboards for requesting books & marking completed swaps
- Implement BookRequest flow (request, accept, decline)
- Pagination & filtering (author, title search, condition)
- Admin / moderation commands
- Rate limiting & anti-spam
- Docker & CI workflow

## Minimal Docker Example (optional)
```
docker build -t book-swap-bot .
docker run --env-file .env --name book-swap-bot book-swap-bot
```

## Logging
Configured at INFO level. Adjust by editing `logging.basicConfig` in `main.py` if needed.

## Deployment Tips
- Use systemd / Docker for process supervision
- Keep BOT_TOKEN secret (env var, not hardcoded)
- Use PostgreSQL for concurrency & reliability
- Enable structured logging (JSON) for observability if scaling

## Security Considerations
- Do not log sensitive tokens
- Validate / sanitize user input if adding richer features
- Consider per-user rate limits for heavy future operations

## Contributing
1. Fork & branch
2. Add / modify features with tests (if test suite added later)
3. Open PR with concise description


## License
MIT

---

Remember that smoking kills, but you'll die anyway even you stop smoking!