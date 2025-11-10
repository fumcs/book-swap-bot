# Docker Setup Guide

This guide explains how to build and run the Book Swap Bot using Docker and Docker Compose.

## Prerequisites

- Docker (v20.10 or higher)
- Docker Compose (v1.29 or higher)
- A valid Telegram Bot Token (from BotFather)

## Quick Start

### 1. Prepare Environment

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` and set your `TELEGRAM_TOKEN`:

```bash
TELEGRAM_TOKEN=your_actual_token_here
POLLING=true
UVICORN_PORT=8000
LOG_LEVEL=INFO
```

### 2. Build and Run

**Option A: Using Docker Compose (Recommended)**

```bash
# Build the image
docker-compose build

# Run the bot
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop the bot
docker-compose down
```

**Option B: Using Docker directly**

```bash
# Build the image
docker build -t book-swap-bot:latest .

# Run the container
docker run -d \
  --name book-swap-bot \
  -e TELEGRAM_TOKEN=your_token_here \
  -e POLLING=true \
  -v $(pwd)/books.db:/app/books.db \
  -v $(pwd)/locale:/app/locale:ro \
  book-swap-bot:latest

# View logs
docker logs -f book-swap-bot

# Stop the container
docker stop book-swap-bot
docker rm book-swap-bot
```

## Configuration

### Environment Variables

Key environment variables for configuration:

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_TOKEN` | (required) | Your Telegram bot token |
| `POLLING` | `true` | Use polling mode (true) or webhook mode (false) |
| `BOT_POLLING_INTERVAL` | `30` | Polling interval in seconds |
| `UVICORN_HOST` | `0.0.0.0` | Web server host |
| `UVICORN_PORT` | `8000` | Web server port |
| `DATABASE_URL` | `sqlite+aiosqlite:///./books.db` | Database connection string |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `I18N_DEFAULT_LOCALE` | `en` | Default locale for translations |

### Database Configuration

**SQLite (Default)**
```
DATABASE_URL=sqlite+aiosqlite:///./books.db
```

**PostgreSQL**
```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/booksdb
```

## Advanced Usage

### Running in Webhook Mode

Set `POLLING=false` in your `.env` file and ensure:
1. The container is accessible from the internet
2. Port 8000 (or your configured port) is exposed
3. Your firewall/NAT allows incoming connections

```bash
docker-compose up -d
# Configure Telegram webhook to: https://your-domain.com:8000/webhook
```

### Database Persistence

The docker-compose.yml mounts `./books.db` from the host machine, ensuring data persists between container restarts.

To use a volume instead:

```bash
docker-compose exec bot sqlite3 /app/books.db '.backup "/app/backup.db"'
docker cp book-swap-bot:/app/backup.db ./backup.db
```

### Development Mode

For development with auto-reload:

```bash
docker-compose exec bot bash
# Inside container
export UVICORN_RELOAD=true
python main.py
```

Or create a development override:

```yaml
# docker-compose.override.yml
version: '3.9'
services:
  bot:
    environment:
      UVICORN_RELOAD: 'true'
    volumes:
      - .:/app  # Mount entire project for live reload
```

Then run: `docker-compose -f docker-compose.yml -f docker-compose.override.yml up`

## Maintenance

### View Container Logs

```bash
# View logs (last 100 lines)
docker-compose logs --tail=100 bot

# Follow logs in real-time
docker-compose logs -f bot
```

### Execute Commands in Container

```bash
# Run a bash shell
docker-compose exec bot bash

# Run database migrations
docker-compose exec bot python -m alembic upgrade head

# Check Python version
docker-compose exec bot python --version
```

### Backup Database

```bash
# SQLite backup
docker-compose exec bot sqlite3 /app/books.db '.backup "/app/backup_$(date +%Y%m%d).db"'
docker cp book-swap-bot:/app/backup_*.db ./

# Or using docker volumes
docker run --rm -v book-swap-bot_bot_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/bot-data-backup.tar.gz -C /data .
```

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild image
docker-compose build --no-cache

# Restart container
docker-compose down
docker-compose up -d
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs bot

# Check if port is already in use
lsof -i :8000

# Verify environment variables
docker-compose exec bot env | grep -E 'TELEGRAM|DATABASE|LOG'
```

### Database locked error

```bash
# Remove old container and restart
docker-compose down
docker-compose up -d
```

### Memory/CPU issues

Adjust resource limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 1G
```

### Permissions error

Ensure the host machine has proper permissions:

```bash
chmod 755 books.db
chmod -R 755 locale
```

## Production Considerations

1. **Use PostgreSQL** instead of SQLite for production
2. **Use separate webhook server** for webhook mode (nginx/caddy in front)
3. **Set up monitoring** with health checks
4. **Use secrets management** (Docker Secrets or external tools) for sensitive data
5. **Configure logging** to external service (ELK, CloudWatch, etc.)
6. **Use resource limits** to prevent resource exhaustion
7. **Run multiple bot replicas** with load balancing if needed

## See Also

- [Main README](README.md)
- [Translation Setup](I18N_README.md)
- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
